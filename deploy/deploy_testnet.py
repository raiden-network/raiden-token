from gevent import monkey
monkey.patch_all()
"""
Deploy RaidenToken and DutchAuction on a testnet
"""
import requests.adapters as adapter
adapter.DEFAULT_POOLSIZE = 1000


import click
import sys
from populus import Project
from deploy.utils import (
    passphrase,
    check_succesful_tx,
    set_connection_pool_size,
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
        set_connection_pool_size(chain.web3, 1000, 1000)
        ctx.obj = {}
        ctx.obj['chain'] = chain
        ctx.obj['owner'] = kwargs['owner'] or chain.web3.eth.accounts[0]


@main.group('deploy', invoke_without_command=True)
@click.option(
    '--wallet',
    help='Auction funds will be sent to this wallet address.'
)
@click.option(
    '--whitelister',
    required=True,
    help='Address with permission to add/remove bidders to/from a whitelist.'
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
    whitelister = kwargs['whitelister']

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

    # Deploy Auction
    auction_txhash = Auction.deploy(transaction={"from": owner},
                                    args=[wallet_address, whitelister, price_start,
                                          price_constant, price_exponent])
    log.info("Deploying auction, tx hash " + auction_txhash)
    receipt, success = check_succesful_tx(web3, auction_txhash)
    assert success is True
    auction_address = receipt["contractAddress"]
    log.info("Auction contract address " + auction_address)

    # Deploy token
    token_txhash = Token.deploy(transaction={"from": owner}, args=[
        auction_address,
        wallet_address,
        supply
    ])

    log.info("Deploying token, tx hash " + token_txhash)
    receipt, success = check_succesful_tx(web3, token_txhash)
    assert success is True
    token_address = receipt["contractAddress"]
    log.info("Token contract address " + token_address)

    # Make contracts aware of each other
    log.info("Initializing contracts")
    auction = Auction(address=auction_address)
    token = Token(address=token_address)

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
    ctx.obj['total_supply'] = supply

    log.info("contracts deployed: --auction-contract %s --token-contract %s"
             % (auction_address, token_address))


@main.group('simulation', invoke_without_command=True)
@click.option(
    '--claim-tokens/--no-claim-tokens',
    default=False,
    is_flag=True,
    help='Run auction simulation.'
)
@click.option(
    '--bidders',
    default=10,
    help='Number of bidders.'
)
@click.option(
    '--wei-bidders',
    type=int,
    default=1,
    help='How many of running bidders will do 1 WEI bids.'
)
@click.option(
    '--bid-price',
    type=int,
    help='Price per TKN in WEI at which the first bid should start.'
)
@click.option(
    '--max-bid-amount',
    type=int,
    default=100e18,
    help='Maximum amount of WEI to use per bid'
)
@click.option(
    '--min-bid-amount',
    type=int,
    default=10000,
    help='Minimum amount of WEI to use per bid'
)
@click.option(
    '--max-bid-ceiling',
    type=float,
    default='0.8',
    help='A float value betwen 0 - 1.0'
)
@click.option(
    '--start-auction/--no-start-auction',
    default=False,
    is_flag=True,
    help='Whether "startAuction()" is called at the begininng of the sim.'
)
@click.option(
    '--deploy-bidders/--no-deploy-bidders',
    default=False,
    is_flag=True,
    help='If set, bidders are deployed (aka do the actual simulation)'
)
@click.option(
    '--finalize-auction/--no-finalize-auction',
    default=False,
    is_flag=True,
    help='Whether "finalizeAuction()" is called after all bidders finish.'
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
    help="How much of the owner's WEI will be distributed to the bidders, to run the simulation"
)
@click.pass_context
def simulation(ctx, **kwargs):
    token_contract_address = ctx.obj.get('token_contract_address', None)
    if token_contract_address is None:
        token_contract_address = kwargs.get('token_contract')
    if token_contract_address is None:
        log.fatal('No token contract address set! Either supply one '
                  'using --token-contract option, or use deploy command')
        sys.exit(1)
    if kwargs['bidders'] < kwargs['wei_bidders']:
        log.fatal('1 wei bidders number must be less or equal as the total number of bidders')
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

    auction_simulation(web3, token_contract, auction_contract, owner, kwargs)


deploy.add_command(simulation)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    main()
