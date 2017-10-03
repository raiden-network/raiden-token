"""
Distribute tokens to bidders after auction ends.
"""
from populus import Project
from deploy.distributor import Distributor
import click


@click.command()
@click.option(
    '--chain',
    default='kovan',
    help='Chain to deploy on: kovan | ropsten | rinkeby | tester | privtest'
)
@click.option(
    '--distributor',
    required=True,
    help='Distributor contract address.'
)
@click.option(
    '--distributor-tx',
    required=True,
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
        Auction_abi = chain.provider.get_contract_factory('DutchAuction')
        Distributor_abi = chain.provider.get_contract_factory('Distributor')

        # Load Populus contract proxy classes
        auction = Auction_abi(address=auction_address)
        distributor = Distributor_abi(address=distributor_address)

        print("Web3 provider is", web3.currentProvider)

        distrib = Distributor(web3, auction, auction_tx, auction.abi,
                              distributor, distributor_tx, claims)
        distrib.distribute()


if __name__ == "__main__":
    main()
