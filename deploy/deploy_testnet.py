from gevent import monkey
monkey.patch_all()
"""
Deploy RaidenToken and DutchAuction on a testnet
"""
import requests.adapters as adapter
adapter.DEFAULT_POOLSIZE = 1000


import click
import gevent
from populus import Project
from deploy.utils import (
    passphrase,
    check_succesful_tx,
    assignFundsToBidders,
    returnFundsToOwner,
    set_connection_pool_size
)
from deploy.simulation import (
    auction_simulation
)
import logging
from web3 import Web3
from populus.contracts.contract import PopulusContract
log = logging.getLogger(__name__)


class Web3Context:
    def __init__(self, web3, auction_contract, token_contract,
                 owner, wallet_address, auction_address):
        assert isinstance(web3, Web3)
        assert isinstance(auction_contract, PopulusContract)
        assert isinstance(token_contract, PopulusContract)
        assert isinstance(owner, str)
        assert isinstance(wallet_address, str)
        assert isinstance(auction_address, str)

        self.web3 = web3
        self.auction_contract = auction_contract
        self.token_contract = token_contract
        self.owner = owner
        self.wallet_address = wallet_address


pass_app = click.make_pass_decorator(Web3Context)


@click.group()
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
    '--wallet',
    help='Auction funds will be sent to this wallet address.'
)
@click.option(
    '--supply',
    default=10000000,
    help='Token contract supply (number of total issued tokens).'
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
@click.pass_context
def main(ctx, **kwargs):
    project = Project()

    chain_name = kwargs['chain']
    owner = kwargs['owner']
    wallet_address = kwargs['wallet']
    supply = kwargs['supply']
    price_start = kwargs['price_start']
    price_constant = kwargs['price_constant']
    price_exponent = kwargs['price_exponent']

    multiplier = 10 ** 18
    supply *= multiplier

    print("Make sure {} chain is running, you can connect to it and it is synced, "
          "or you'll get timeout".format(chain_name))

    with project.get_chain(chain_name) as chain:
        web3 = chain.web3
        set_connection_pool_size(web3, 100, 100)
        owner = owner or web3.eth.accounts[0]
        wallet_address = wallet_address or web3.personal.newAccount(passphrase)

        print("Web3 provider is", web3.currentProvider)
        assert owner, "Make sure owner account is created"
        assert wallet_address, "Make sure wallet account is created"
        print('Owner', owner)
        print('Wallet', wallet_address)
        print('Auction start price:', price_start)
        print('Auction price constant:', price_constant)
        print('Auction price exponent:', price_exponent)

        # Load Populus contract proxy classes
        Auction = chain.provider.get_contract_factory('DutchAuction')
        Token = chain.provider.get_contract_factory('RaidenToken')
        Distributor = chain.provider.get_contract_factory('Distributor')

        # Deploy Auction
        auction_txhash = Auction.deploy(transaction={"from": owner},
                                        args=[wallet_address, price_start,
                                              price_constant, price_exponent])
        print("Deploying auction, tx hash is", auction_txhash)
        receipt = check_succesful_tx(web3, auction_txhash)
        auction_address = receipt["contractAddress"]
        print("Auction contract address is", auction_address)

        # Deploy token
        token_txhash = Token.deploy(transaction={"from": owner}, args=[
            auction_address,
            wallet_address,
            supply
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
        ctx.obj = Web3Context(web3, auction, token, owner, wallet_address, auction_address)


@main.command()
@click.option(
    '--claim-tokens',
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
    help='Price per TKN in WEI at which the first bid should start. Only if the --simulation flag '
         'is set'
)
@click.option(
    '--bid-interval',
    help='Time interval in seconds between bids. Only if the --simulation flag is set'
)
@click.option(
    '--fund/--no-fund',
    default=True,
    help='Fund bidders accounts with random ETH from the owner account. Done before starting '
         'the simulation.'
)
@click.option(
    '--distribution-limit',
    default=None,
    type=int,
    help="How much of the owner's ethereum distribute to the bidders"
)
@pass_app
def simulation(app: Web3Context, **kwargs):
    bidders = int(kwargs['bidders'])
    bid_start_price = int(kwargs['bid_price'] or 0)
    bid_interval = int(kwargs['bid_interval'] or 0)
    fund_bidders = kwargs['fund']
    sim_claim_tokens = kwargs['claim_tokens']
    if simulation:
        log.info('Starting simulation setup for {0} bidders'.format(bidders))
        bidder_addresses = app.web3.eth.accounts[1:(bidders + 1)]

        # come to daddy
        event_list = [gevent.spawn(returnFundsToOwner, app.web3, app.owner, bidder)
                      for bidder in bidder_addresses]
        gevent.joinall(event_list)

        log.info('Creating {0} bidder accounts: '.format(bidders - len(bidder_addresses)))
        for i in range(len(bidder_addresses), bidders):
            address = app.web3.personal.newAccount(passphrase)
            bidder_addresses.append(address)

        log.info('Simulating {0} bidders: {1}'.format(len(bidder_addresses), bidder_addresses))
        if bid_start_price:
            log.info('Bids will start at {0} WEI = {1} ETH  / TKN'.format(
                bid_start_price,
                app.web3.fromWei(bid_start_price, 'ether')))

        if fund_bidders:
            assignFundsToBidders(app.web3, app.owner, bidder_addresses,
                                 kwargs['distribution_limit'])

        auction_simulation(app.web3, app.wallet_address, app.token_contract,
                           app.auction_contract, app.owner,
                           bidder_addresses, bid_interval, bid_start_price,
                           sim_claim_tokens)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    main()
