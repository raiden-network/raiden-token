import logging
import gevent

log = logging.getLogger(__name__)

from deploy.utils import (
    check_succesful_tx,
    amount_format,
    passphrase,
    returnFundsToOwner,
    assignFundsToBidders
)

tx_timeout = 180

AUCTION_DEPLOYED = 0
AUCTION_SETUP = 1
AUCTION_STARTED = 2
AUCTION_ENDED = 3
AUCTION_TOKENS_DISTRIBUTED = 4


def fund_bidders(web3, owner, kwargs):
    bidders = int(kwargs['bidders'])
    bid_start_price = int(kwargs['bid_price'] or 0)
    fund_bidders = kwargs['fund']
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
        log.info('owner={owner} balance={balance}'
                 .format(owner=owner, balance=amount_format(web3, web3.eth.getBalance(owner))))
        assignFundsToBidders(web3, owner, bidder_addresses,
                             kwargs['distribution_limit'])
    return bidder_addresses


def successful_bid(web3, auction, bidder, amount):
    bid_successful = False

    while not bid_successful and amount > 0:
        try:
            txhash = auction.transact({'from': bidder, "value": amount}).bid()
            receipt = check_succesful_tx(web3, txhash)
            assert receipt is not None
            log.info('BID successful from=%s value=%d' % (bidder, amount))
            bid_successful = amount
        except:
            amount = auction.call().missingFundsToEndAuction()
            if(amount > 10):
                amount = amount // 7
            log.info('Bid > missing funds, trying with {0} WEI ({bidder})'
                     .format(amount, bidder=bidder))
    return amount


def deploy_bidders(bidder_addrs, web3, auction, kwargs):
    if auction.call().stage() != AUCTION_STARTED:
        log.warning('requested bidders deployment, but auction is not started yet')
        return
    from deploy.bidder import Bidder
    bidder_objs = []
    for addr in bidder_addrs:
        bidder = Bidder(web3, auction, addr)
        bidder.max_bid_ceiling = kwargs['max_bid_ceiling']
        bidder.bid_interval = kwargs['bid_interval']
        bidder.max_bid_price = kwargs['max_bid_amount']
        bidder.min_bid_price = kwargs['min_bid_amount']
        bidder_objs.append(bidder)
    for i in range(0, kwargs['wei_bidders']):
        if i == 0:
            bidder_objs[i].max_bids = 1
        bidder_objs[i].max_bid_price = 1
        bidder_objs[i].min_bid_price = 1
    bidder_gevents = [gevent.spawn(b.run) for b in bidder_objs]
    gevent.joinall(bidder_gevents)


def claim_tokens(auction, bidder, web3):
    unlocked = web3.personal.unlockAccount(bidder, passphrase)
    assert unlocked is True
    txhash = auction.transact({'from': bidder}).claimTokens()
    receipt, success = check_succesful_tx(web3, txhash)
    if success is False:
        log.info('claimTokens(%s) failed for tx %s. This is either an error, '
                 'or funds have been claimed already' % (bidder, txhash))


def start_auction(auction, owner, web3):
    if auction.call().stage() >= AUCTION_STARTED:
        log.info('requested startAuction(), but auction has started already. skipping.')
        return

    log.info('Start auction owner balance %s' %
             amount_format(web3, web3.eth.getBalance(owner)))
    txhash = auction.transact({'from': owner}).startAuction()
    receipt = check_succesful_tx(web3, txhash, tx_timeout)
    assert receipt is not None


def finalize_auction(auction, owner, web3):
    # check if there are no funds remaining
    if auction.call().stage() >= AUCTION_ENDED:
        log.warning("requested finalizeAuction(), but auction has ended already. Skipping this.")
        return

    ret = auction.call({'from': owner}).missingFundsToEndAuction()
    assert ret == 0
    log.info('missing funds %s' % auction.call({'from': owner}).missingFundsToEndAuction())

    # Owner calls finalizeAuction
    txhash = auction.transact({'from': owner}).finalizeAuction()
    receipt, success = check_succesful_tx(web3, txhash)
    assert receipt is not None
    assert success is True
    assert auction.call().stage() == 3  # AuctionEnded


def get_balance(token, bidder):
    token_balance = token.call().balanceOf(bidder)
    log.info('{bidder} {tokens}'.format(bidder=bidder, tokens=token_balance))
    return token_balance


def auction_simulation(web3, token, auction, owner, kwargs):
    # Start the auction
    bidder_addresses = fund_bidders(web3, owner, kwargs)
    if kwargs['start_auction'] is True:
        start_auction(auction, owner, web3)

    # deploy bidders
    # this will return when auction ends
    if kwargs['deploy_bidders']:
        assert auction.call().price_start() > 0
        assert isinstance(auction.call().price_constant(), int)
        assert isinstance(auction.call().price_exponent(), int)
        assert token.call().decimals() > 0
        deploy_bidders(bidder_addresses, web3, auction, kwargs)
    else:
        log.info("--deploy-bidders is not set. Skipping bidding part of the simulation.")

    if kwargs['finalize_auction']:
        finalize_auction(auction, owner, web3)

    if kwargs['claim_tokens'] is True:
        if auction.call().stage() == AUCTION_TOKENS_DISTRIBUTED:
            log.info('not claiming tokens: auction stage is TokensDistributed already')
            return
        assert auction.call().stage() == AUCTION_ENDED
        bidder_addresses = fund_bidders(web3, owner, kwargs)  # refill bidders again
        event_lst = [gevent.spawn(claim_tokens, auction, x, web3)
                     for x in bidder_addresses]
        gevent.joinall(event_lst)
        event_lst = [gevent.spawn(get_balance, token, x)
                     for x in bidder_addresses]
        gevent.joinall(event_lst)
        total_balance = sum([ev.value for ev in event_lst])
        assert auction.call().stage() == AUCTION_TOKENS_DISTRIBUTED
        return total_balance
