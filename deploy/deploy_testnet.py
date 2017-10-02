from gevent import monkey
monkey.patch_all()
"""
Deploy RaidenToken and DutchAuction on a testnet
"""
import requests.adapters as adapter
adapter.DEFAULT_POOLSIZE = 1000


import click
import gevent
import sys
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
log = logging.getLogger(__name__)


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
@click.pass_context
def main(ctx, **kwargs):
    project = Project()

    chain_name = kwargs['chain']

    log.info("Make sure {} chain is running, you can connect to it and it is synced, "
             "or you'll get timeout".format(chain_name))

    with project.get_chain(chain_name) as chain:
        set_connection_pool_size(chain.web3, 100, 100)
        ctx.obj = {}
        ctx.obj['chain'] = chain
        ctx.obj['owner'] = kwargs['owner'] or chain.web3.eth.accounts[0]


@main.group('deploy', invoke_without_command=True)
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
def deploy(ctx, **kwargs):
    owner = ctx.obj['owner']
    wallet_address = kwargs['wallet']
    supply = kwargs['supply']
    price_start = kwargs['price_start']
    price_constant = kwargs['price_constant']
    price_exponent = kwargs['price_exponent']

    multiplier = 10 ** 18
    supply *= multiplier

    chain = ctx.obj['chain']
    web3 = chain.web3
    wallet_address = wallet_address or web3.personal.newAccount(passphrase)

    log.info("Web3 provider is %s" % (web3.currentProvider))
    assert owner, "Make sure owner account is created"
    assert wallet_address, "Make sure wallet account is created"
    log.info('owner=%s wallet=%s' % (owner, wallet_address))
    log.info('auction start_price=%d constant=%d exponent=%d' %
             (price_start, price_constant, price_exponent))

    # Load Populus contract proxy classes
    Auction = chain.provider.get_contract_factory('DutchAuction')
    Token = chain.provider.get_contract_factory('RaidenToken')
    Distributor = chain.provider.get_contract_factory('Distributor')

    # Deploy Auction
    auction_txhash = Auction.deploy(transaction={"from": owner},
                                    args=[wallet_address, price_start,
                                          price_constant, price_exponent])
    log.info("Deploying auction, tx hash " + auction_txhash)
    receipt = check_succesful_tx(web3, auction_txhash)
    auction_address = receipt["contractAddress"]
    log.info("Auction contract address " + auction_address)

    # Deploy token
    token_txhash = Token.deploy(transaction={"from": owner}, args=[
        auction_address,
        wallet_address,
        supply
    ])

    log.info("Deploying token, tx hash " + token_txhash)
    receipt = check_succesful_tx(web3, token_txhash)
    token_address = receipt["contractAddress"]
    log.info("Token contract address " + token_address)

    # Deploy Distributor contract
    distributor_txhash = Distributor.deploy(transaction={"from": owner},
                                            args=[auction_address])
    log.info("Deploying distributor, tx hash is " + distributor_txhash)
    receipt = check_succesful_tx(web3, distributor_txhash)
    distributor_address = receipt["contractAddress"]
    log.info("Distributor contract address  " + distributor_address)

    # Make contracts aware of each other
    log.info("Initializing contracts")
    auction = Auction(address=auction_address)
    token = Token(address=token_address)
    distributor = Distributor(address=distributor_address)
    assert distributor is not None

    txhash = auction.transact({"from": owner}).setup(token_address)
    check_succesful_tx(web3, txhash)

    # Do some contract reads to see everything looks ok
    log.info("Token total supply is {0} Tei = {1} TKN".format(
        token.call().totalSupply(),
        int(token.call().totalSupply() / multiplier)))
    log.info("Auction price at 0 seconds (elapsed) is {0} WEI = {1} ETH".format(
        auction.call().price(),
        web3.fromWei(auction.call().price(), 'ether')))
    ctx.obj['token_contract_address'] = token_address
    ctx.obj['auction_contract_address'] = auction_address


@main.group('simulation', invoke_without_command=True)
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
    type=int,
    help='Price per TKN in WEI at which the first bid should start.'
)
@click.option(
    '--max-bid-amount',
    type=int,
    default=10000000,
    help='Maximum amount of ETH to use per bid (in WEI)'
)
@click.option(
    '--max-bid-ceiling',
    type=float,
    default='0.8',
    help='A float value betwen 0 - 1.0'
)
@click.option(
    '--bid-interval',
    default=5,
    type=int,
    help='Time interval in seconds between bids. Only if the --simulation flag is set'
)
@click.option(
    '--token-contract',
    help='Address of token contract (if set, overrides deployed addr)'
)
@click.option(
    '--auction-contract',
    help='Address of  auction contract (if set, overrides deployed addr)'
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
    help="How much of the owner's ethereum distribute to the bidders (in wei)"
)
@click.pass_context
def simulation(ctx, **kwargs):
    bidders = int(kwargs['bidders'])
    bid_start_price = int(kwargs['bid_price'] or 0)
    fund_bidders = kwargs['fund']

    token_contract_address = ctx.obj.get('token_contract_address', None)
    if token_contract_address is None:
        token_contract_address = kwargs.get('token_contract')
    if token_contract_address is None:
        log.fatal('No token contract address set! Either supply one '
                  'using --token-contract option, or use deploy command')
        sys.exit(1)

    auction_contract_address = ctx.obj.get('auction_contract_address', None)
    if auction_contract_address is None:
        auction_contract_address = kwargs.get('auction_contract')
    if auction_contract_address is None:
        log.fatal('No auction contract address set! Either supply one '
                  'using --auction-contract option, or use deploy command')
        sys.exit(1)

    chain = ctx.obj['chain']
    owner = ctx.obj['owner']
    web3 = chain.web3

    Auction = chain.provider.get_contract_factory('DutchAuction')
    Token = chain.provider.get_contract_factory('RaidenToken')

    auction_contract = Auction(address=auction_contract_address)
    token_contract = Token(address=token_contract_address)

    bidder_addresses = web3.eth.accounts[1:(bidders + 1)]

    # come to daddy
    event_list = [gevent.spawn(returnFundsToOwner, web3, owner, bidder)
                  for bidder in bidder_addresses]
    gevent.joinall(event_list)

    log.info('Creating {0} bidder accounts: '.format(bidders - len(bidder_addresses)))
    for i in range(len(bidder_addresses), bidders):
        address = web3.personal.newAccount(passphrase)
        bidder_addresses.append(address)

    log.info('Simulating {0} bidders: {1}'.format(len(bidder_addresses), bidder_addresses))
    if bid_start_price:
        log.info('Bids will start at {0} WEI = {1} ETH  / TKN'.format(
            bid_start_price,
            web3.fromWei(bid_start_price, 'ether')))

    if fund_bidders:
        assignFundsToBidders(web3, owner, bidder_addresses,
                             kwargs['distribution_limit'])

    auction_simulation(web3, token_contract, auction_contract, owner,
                       bidder_addresses, kwargs)


deploy.add_command(simulation)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    main()
