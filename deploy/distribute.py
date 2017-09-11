"""
Distribute tokens to bidders after auction ends.
"""
from populus import Project
from web3 import Web3
from distributor import Distributor
import json
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

    with open('build/contracts.json') as json_data:
        abis = json.load(json_data)

    with project.get_chain(chain_name) as chain:
        web3 = chain.web3
        auction_abi = abis['DutchAuction']['abi']
        distributor_abi = abis['Distributor']['abi']

        # Load Populus contract proxy classes
        auction = web3.eth.contract(abi=auction_abi, address=auction_address)
        distributor = web3.eth.contract(abi=distributor_abi, address=distributor_address)

        print("Web3 provider is", web3.currentProvider)

        distrib = Distributor(web3, auction, auction_tx, auction_abi, distributor, distributor_tx, distributor_abi, claims)
        distrib.distribute()


if __name__ == "__main__":
    main()
