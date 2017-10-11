"""
Distribute tokens to bidders after auction ends.
"""
from populus import Project
from deploy.distributor import Distributor as DistributorScript
import click
from deploy.utils import (
    check_succesful_tx
)
import sys
import logging
log = logging.getLogger(__name__)

@click.command()
@click.option(
    '--chain',
    default='kovan',
    help='Chain to deploy on: kovan | ropsten | rinkeby | tester | privtest'
)
@click.option(
    '--distributor',
    help='Distributor contract address.'
)
@click.option(
    '--distributor-tx',
    help='Distributor deployment transaction hash.'
)
@click.option(
    '--auction',
    required=True,
    help='Auction contract address.'
)
@click.option(
    '--auction-tx',
    required=True,
    help='Auction deployment transaction hash.'
)
@click.option(
    '--batch-number',
    default=None,
    help='How many token claims to be processed. Default is calculated from gas cost estimation.'
)
def main(**kwargs):
    project = Project()

    chain_name = kwargs['chain']
    distributor_address = kwargs['distributor']
    distributor_tx = kwargs['distributor_tx']
    auction_address = kwargs['auction']
    auction_tx = kwargs['auction_tx']
    batch_number = kwargs['batch_number']

    if batch_number:
        batch_number = int(batch_number)

    with project.get_chain(chain_name) as chain:
        web3 = chain.web3
        log.info("Web3 provider is %s" % (web3.currentProvider))

        owner = chain.web3.eth.accounts[0]
        Auction = chain.provider.get_contract_factory('DutchAuction')
        Distributor = chain.provider.get_contract_factory('Distributor')

        # Load Populus contract proxy classes
        auction = Auction(address=auction_address)

        end_time = auction.call().end_time()
        waiting = auction.call().token_claim_waiting_period()
        token_claim_ok_time = end_time + waiting
        now = web3.eth.getBlock('latest')['timestamp']
        if token_claim_ok_time > now:
            log.warning('Token claim waiting period is not over')
            log.warning('Remaining: %s seconds' % (token_claim_ok_time - now))
            sys.exit()

        if not distributor_address:
            distributor_tx = Distributor.deploy(transaction={"from": owner},
                                                    args=[auction_address])
            log.info("DISTRIBUTOR tx hash: " + distributor_tx)
            receipt, success = check_succesful_tx(web3, distributor_tx)
            assert success is True
            assert receipt is not None

            distributor_address = receipt["contractAddress"]
            log.info("DISTRIBUTOR contract address  " + distributor_address)

        distributor = Distributor(address=distributor_address)
        assert distributor is not None

        distrib = DistributorScript(web3, auction, auction_tx, auction.abi,
                              distributor, distributor_tx, batch_number)
        distrib.distribute()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    main()
