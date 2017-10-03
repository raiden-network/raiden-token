import logging
import gevent

log = logging.getLogger(__name__)

from deploy.utils import (
    check_succesful_tx,
    amount_format,
    passphrase
)

tx_timeout = 180


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
    from deploy.bidder import Bidder
    bidder_objs = []
    for addr in bidder_addrs:
        bidder = Bidder(web3, auction, addr)
        bidder.max_bid_ceiling = kwargs['max_bid_ceiling']
        bidder.bid_interval = kwargs['bid_interval']
        bidder.max_bid_price = kwargs['max_bid_amount']
        bidder.min_bid_price = kwargs['min_bid_amount']
        bidder_objs.append(bidder)
    bidder_gevents = [gevent.spawn(b.run) for b in bidder_objs]
    gevent.joinall(bidder_gevents)


def claim_tokens(auction, bidder, web3):
    unlocked = web3.personal.unlockAccount(bidder, passphrase)
    assert unlocked is True
    txhash = auction.transact({'from': bidder}).claimTokens()
    check_succesful_tx(web3, txhash)


def get_balance(token, bidder):
    token_balance = token.call().balanceOf(bidder)
    log.info('{bidder} {tokens}'.format(bidder=bidder, tokens=token_balance))
    return token_balance


def auction_simulation(web3, token, auction, owner, bidders,
                       kwargs):

    log.info('owner={owner} balance={balance}'
             .format(owner=owner, balance=amount_format(web3, web3.eth.getBalance(owner))))

    # Start the auction
    if kwargs['start_auction'] is True:
        log.info('Start auction owner balance %s' %
                 amount_format(web3, web3.eth.getBalance(owner)))
        txhash = auction.transact({'from': owner}).startAuction()
        receipt = check_succesful_tx(web3, txhash, tx_timeout)

    assert auction.call().stage() == 2  # AuctionStarted
    assert auction.call().price_start() > 0
    assert isinstance(auction.call().price_constant(), int)
    assert isinstance(auction.call().price_exponent(), int)
    assert token.call().decimals() > 0

    # deploy bidders
    # this will return when auction ends
    deploy_bidders(bidders, web3, auction, kwargs)

    # check if there are no funds remaining
    ret = auction.call({'from': owner}).missingFundsToEndAuction()
    assert ret == 0
    log.info('missing funds %s' % auction.call({'from': owner}).missingFundsToEndAuction())

    # Owner calls finalizeAuction
    txhash = auction.transact({'from': owner}).finalizeAuction()
    receipt = check_succesful_tx(web3, txhash)
    assert receipt is not None
    assert auction.call().stage() == 3  # AuctionEnded

    if kwargs['claim_tokens'] is True:
        event_lst = [gevent.spawn(claim_tokens, auction, x, web3)
                     for x in bidders]
        gevent.joinall(event_lst)
        event_lst = [gevent.spawn(get_balance, token, x)
                     for x in bidders]
        gevent.joinall(event_lst)
        total_balance = sum([ev.value for ev in event_lst])
        assert auction.call().stage() == 4  # TokensDistributed
        return total_balance
