"""
Deploy ReserveToken and DutchAuction on a testnet
"""
import click
from populus import Project
from populus.utils.wait import wait_for_transaction_receipt
from web3 import Web3
from testnet_fixtures import createWallet

multiplier = 10**18
# price_factor, _price_const
auction_args = [
    [2, 7500],
    [3, 7500]
]


def check_succesful_tx(web3: Web3, txid: str, timeout=180) -> dict:

    receipt = wait_for_transaction_receipt(web3, txid, timeout=timeout)
    txinfo = web3.eth.getTransaction(txid)

    # EVM has only one error mode and it's consume all gas
    assert txinfo["gas"] != receipt["gasUsed"]
    return receipt


@click.command()
@click.option(
    '--chain',
    default='kovan',
    help='Chain to deploy on: kovan | ropsten | rinkeby | tester | privtest'
)
@click.option(
    '--owner',
    help='Contracts owner, default: web3.eth.accounts[0]'
)
@click.option(
    '--supply',
    default=10000000,
    help='Token contract supply (number of total issued tokens).'
)
@click.option(
    '--price-factor',
    default=2,
    help='Price factor used in auction price calculation.'
)
@click.option(
    '--price-constant',
    default=7500,
    help='Price constant used in auction price calculation.'
)
@click.option(
    '--prealloc-addresses',
    help='Addresses separated by a comma, for preallocating tokens.'
)
@click.option(
    '--prealloc-amounts',
    help='Token amounts separated by a comma, for preallocating tokens.'
)
def main(**kwargs):
    project = Project()

    chain_name = kwargs['chain']
    owner = kwargs['owner']
    supply = kwargs['supply'] * multiplier
    price_factor = kwargs['price_factor']
    price_constant = kwargs['price_constant']

    print("Make sure {} chain is running, you can connect to it and it is synced, or you'll get timeout".format(chain_name))

    with project.get_chain(chain_name) as chain:
        web3 = chain.web3
        owner = owner or web3.eth.accounts[0]

        # Set preallocations
        if kwargs['prealloc_addresses']:
            prealloc_addresses = kwargs['prealloc_addresses'].split(',')
        else:
            if len(web3.eth.accounts) >= 2:
                prealloc_addresses = web3.eth.accounts[:2]
            else:
                # Create needed accounts if they don't exist
                prealloc_addresses = []
                priv_keys = []
                for i in range(0, 2):
                    priv_key, address = createWallet()
                    priv_keys.append(priv_key)
                    prealloc_addresses.append('0x' + address)
                print('Preallocations will be sent to the following addresses:')
                print(prealloc_addresses)
                print('Preallocation addresses private keys: ', priv_keys)

        if kwargs['prealloc_amounts']:
            prealloc_amounts = kwargs['prealloc_amounts'].split(',')
        else:
            prealloc_amounts = [
                200000 * multiplier,
                800000 * multiplier
            ]

        print("Web3 provider is", web3.currentProvider)
        assert owner, "Make sure owner account is created"
        print('Owner', owner)
        print('Preallocation addresses & amounts', prealloc_addresses, prealloc_amounts)

        # Load Populus contract proxy classes
        Auction = chain.provider.get_contract_factory('DutchAuction')
        Token = chain.provider.get_contract_factory('ReserveToken')

        # Deploy Auction
        txhash = Auction.deploy(transaction={"from": owner}, args=[price_factor, price_constant])
        print("Deploying auction, tx hash is", txhash)
        receipt = check_succesful_tx(web3, txhash)
        auction_address = receipt["contractAddress"]
        print("Auction contract address is", auction_address)

        # Deploy token
        txhash = Token.deploy(transaction={"from": owner}, args=[
            auction_address,
            supply,
            prealloc_addresses,
            prealloc_amounts
        ])
        print("Deploying token, tx hash is", txhash)
        receipt = check_succesful_tx(web3, txhash)
        token_address = receipt["contractAddress"]
        print("Token contract address is", token_address)

        # Make contracts aware of each other
        print("Initializing contracts")
        auction = Auction(address=auction_address)
        token = Token(address=token_address)

        txhash = auction.transact({"from": owner}).setup(token_address)
        check_succesful_tx(web3, txhash)

        # Do some contract reads to see everything looks ok
        print("Token total supply is", token.call().totalSupply())
        print("Auction price is", auction.call().price())


if __name__ == "__main__":
    main()
