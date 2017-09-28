from gevent import monkey
monkey.patch_all()
"""
Deploy CustomToken and DutchAuction on a testnet
"""
import requests.adapters as adapter
adapter.DEFAULT_POOLSIZE = 1000


import click
import gevent
from populus import Project
from deploy.utils import (
    passphrase,
    createWallet,
    check_succesful_tx,
    assignFundsToBidders,
    returnFundsToOwner
)
from deploy.simulation import (
    getAuctionFactors,
    auction_simulation
)
import logging


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
    '--decimals',
    default=18,
    help='Token contract decimals.'
)
@click.option(
    '--price-start',
    default=6,
    help='Price factor used in auction price calculation.'
)
@click.option(
    '--price-constant',
    default=66,
    help='Price constant used in auction price calculation.'
)
@click.option(
    '--price-exponent',
    default=3,
    help='Price exponent'
)
@click.option(
    '--price-points',
    help='2 price points "price1_in_wei,elapsed_seconds1,price2_in_wei,elapsed_seconds2" used to calculate the price factor and constant for the auction price function. Example: "100000000000000000,0,10000000000000000,600"'
)
@click.option(
    '--prealloc-addresses',
    help='Addresses separated by a comma, for preallocating tokens.'
)
@click.option(
    '--prealloc-amounts',
    help='Token amounts separated by a comma, for preallocating tokens.'
)
@click.option(
    '--simulation',
    is_flag=True,
    help='Run auction simulation.'
)
@click.option(
    '--bidders',
    default=10,
    help='Number of bidders. Only if the --simulation flag is set'
)
@click.option(
    '--bid-price',
    help='Price per TKN in WEI at which the first bid should start. Only if the --simulation flag is set'
)
@click.option(
    '--bid-interval',
    help='Time interval in seconds between bids. Only if the --simulation flag is set'
)
@click.option(
    '--fund/--no-fund',
    default=True,
    help='Fund bidders accounts with random ETH from the owner account. Done before starting the simulation.'
)
@click.option(
    '--auction',
    help='Auction contract address.'
)
@click.option(
    '--token',
    help='Token contract address.'
)
@click.option(
    '--distributor',
    help='Distributor contract address.'
)
def main(**kwargs):
    project = Project()

    chain_name = kwargs['chain']
    owner = kwargs['owner']
    supply = kwargs['supply']
    decimals = kwargs['decimals']
    price_start = kwargs['price_start']
    price_constant = kwargs['price_constant']
    price_exponent = kwargs['price_exponent']
    simulation = kwargs['simulation']
    bidders = int(kwargs['bidders'])
    bid_start_price = int(kwargs['bid_price'] or 0)
    bid_interval = int(kwargs['bid_interval'] or 0)
    price_points = kwargs['price_points']
    fund_bidders = kwargs['fund']
    # auction_addr = kwargs['auction']
    # token_addr = kwargs['token']
    # distributor_addr = kwargs['distributor']

    multiplier = 10**decimals
    supply *= multiplier

    if price_points:
        price_points = price_points.split(',')
        (price_factor, price_constant) = getAuctionFactors(
            int(price_points[0]),
            int(price_points[1]),
            int(price_points[2]),
            int(price_points[3]),
            multiplier)

    print("Make sure {} chain is running, you can connect to it and it is synced, or you'll get timeout".format(chain_name))

    with project.get_chain(chain_name) as chain:
        web3 = chain.web3
        owner = owner or web3.eth.accounts[0]

        # Set preallocations
        if kwargs['prealloc_addresses']:
            prealloc_addresses = kwargs['prealloc_addresses'].split(',')
        else:
            if len(web3.eth.accounts) >= 2:
                prealloc_addresses = web3.eth.accounts[1:3]
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
        print('Preallocation addresses & amounts in WEI', prealloc_addresses, prealloc_amounts)
        print('Auction start price:', price_start)
        print('Auction price constant:', price_constant)
        print('Auction price exponent:', price_exponent)

        # Load Populus contract proxy classes
        Auction = chain.provider.get_contract_factory('DutchAuction')
        Token = chain.provider.get_contract_factory('CustomToken')
        Distributor = chain.provider.get_contract_factory('Distributor')

        wallet = web3.personal.newAccount(passphrase)

        # Deploy Auction
        auction_txhash = Auction.deploy(transaction={"from": owner},
                                        args=[wallet, price_start, price_constant, price_exponent])
        print("Deploying auction, tx hash is", auction_txhash)
        receipt = check_succesful_tx(web3, auction_txhash)
        auction_address = receipt["contractAddress"]
        print("Auction contract address is", auction_address)

        # Deploy token
        if decimals == 18:
            token_txhash = Token.deploy(transaction={"from": owner}, args=[
                auction_address,
                supply,
                prealloc_addresses,
                prealloc_amounts
            ])
        else:
            Token = chain.provider.get_contract_factory('CustomToken2')
            token_txhash = Token.deploy(transaction={"from": owner}, args=[
                decimals,
                auction_address,
                supply,
                prealloc_addresses,
                prealloc_amounts
            ])

        print("Deploying token, tx hash is", token_txhash)
        receipt = check_succesful_tx(web3, token_txhash)
        token_address = receipt["contractAddress"]
        print("Token contract address is", token_address)

        # Deploy Distributor contract
        distributor_txhash = Distributor.deploy(transaction={"from": owner},
                                                args=[auction_address])
        print("Deploying distributor, tx hash is", distributor_txhash)
        receipt = check_succesful_tx(web3, distributor_txhash)
        distributor_address = receipt["contractAddress"]
        print("Distributor contract address is", distributor_address)

        # Make contracts aware of each other
        print("Initializing contracts")
        auction = Auction(address=auction_address)
        token = Token(address=token_address)
        distributor = Distributor(address=distributor_address)
        assert distributor is not None

        txhash = auction.transact({"from": owner}).setup(token_address)
        check_succesful_tx(web3, txhash)

        # Do some contract reads to see everything looks ok
        print("Token total supply is {0} Tei = {1} TKN".format(
            token.call().totalSupply(),
            int(token.call().totalSupply() / multiplier)))
        print("Auction price at 0 seconds (elapsed) is {0} WEI = {1} ETH".format(
            auction.call().price(),
            web3.fromWei(auction.call().price(), 'ether')))

        # Start simulation if --simulation flag is set
        if simulation:
            print('Starting simulation setup for', bidders, 'bidders')
            bidder_addresses = web3.eth.accounts[1:(bidders + 1)]

            # come to daddy
            event_list = [gevent.spawn(returnFundsToOwner, web3, owner, bidder)
                          for bidder in bidder_addresses]
            gevent.joinall(event_list)

            print('Creating more bidder accounts:', bidders - len(bidder_addresses), 'accounts')
            for i in range(len(bidder_addresses), bidders):
                address = web3.personal.newAccount(passphrase)
                bidder_addresses.append(address)

            print('Simulating', len(bidder_addresses), 'bidders:', bidder_addresses)
            if bid_start_price:
                print('Bids will start at {0} WEI = {1} ETH  / TKN'.format(
                    bid_start_price,
                    web3.fromWei(bid_start_price, 'ether')))

            if fund_bidders:
                assignFundsToBidders(web3, owner, bidder_addresses)

            tokens = auction_simulation(web3, wallet, token, auction, owner,
                                        bidder_addresses, bid_interval, bid_start_price)
            assert tokens == supply


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    main()
