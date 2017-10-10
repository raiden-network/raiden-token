"""
Distribute tokens to bidders after auction ends.
"""
from populus import Project
from deploy.distributor import Distributor as DistributorScript
import click
from deploy.utils import (
    check_succesful_tx
)
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
    help='Distributor contract address.'
)
@click.option(
    '--auction',
    required=True,
    help='Auction contract address.'
)
@click.option(
    '--auction-tx',
    required=True,
    help='Auction contract address.'
)
@click.option(
    '--claims',
    default=5,
    help='Auction contract address.'
)
def main(**kwargs):
    project = Project()

    chain_name = kwargs['chain']
    distributor_address = kwargs['distributor']
    distributor_tx = kwargs['distributor_tx']
    auction_address = kwargs['auction']
    auction_tx = kwargs['auction_tx']
    claims = kwargs['claims']

    with project.get_chain(chain_name) as chain:
        web3 = chain.web3
        print("Web3 provider is", web3.currentProvider)
        
        owner = chain.web3.eth.accounts[0]
        Auction = chain.provider.get_contract_factory('DutchAuction')
        Distributor = chain.provider.get_contract_factory('Distributor')

        # Load Populus contract proxy classes
        auction = Auction(address=auction_address)

        if not distributor_address:
            distributor_tx = Distributor.deploy(transaction={"from": owner},
                                                    args=[auction_address])
            log.info("Deploying distributor, tx hash is " + distributor_tx)
            print("Deploying distributor, tx hash is ", distributor_tx)
            receipt, success = check_succesful_tx(web3, distributor_tx)
            assert success is True
            distributor_address = receipt["contractAddress"]
            log.info("Distributor contract address  " + distributor_address)
            print("Distributor contract address  ", distributor_address)

        distributor = Distributor(address=distributor_address)
        assert distributor is not None

        distrib = DistributorScript(web3, auction, auction_tx, auction.abi,
                              distributor, distributor_tx, claims)
        distrib.distribute()


if __name__ == "__main__":
    main()
