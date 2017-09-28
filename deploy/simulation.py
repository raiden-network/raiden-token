import logging

log = logging.getLogger(__name__)

from deploy.utils import (
    check_succesful_tx,
    print_logs,
    amount_format
)

tx_timeout = 180

# TODO
# multiple bids same bidders
# If bidders have remaining balances, we should send them back to the owner


# TODO fix for new price function, otherwise OUTDATED
# Calculate auction factors given 2 price points (price, elapsed_time)
def getAuctionFactors(price1, elapsed1, price2, elapsed2, multiplier):
    price_constant = (elapsed2 * (price2 - 1) - elapsed1 * (price1 - 1)) / (price1 - price2)
    price_factor = (price2 - 1) * (elapsed2 + price_constant) / multiplier

    price1_calculated = round(multiplier * price_factor / (elapsed1 + price_constant) + 1)
    price2_calculated = round(multiplier * price_factor / (elapsed2 + price_constant) + 1)

    assert price1 == price1_calculated
    assert price2 == price2_calculated

    return (int(price_factor), int(price_constant))


# TODO check negative elapsed
# Seconds that should elapse since auction start, in order to get the given price
def elapsedAtPrice(price, price_factor, price_constant, multiplier):
    elapsed = (multiplier * price_factor) / (price - 1) - price_constant
    return int(elapsed)


def print_all_logs(token_contract, auction_contract):
    print_logs(token_contract, 'Transfer', 'CustomToken')
    print_logs(auction_contract, 'Deployed', 'DutchAuction')
    print_logs(auction_contract, 'Setup', 'DutchAuction')
    print_logs(auction_contract, 'SettingsChanged', 'DutchAuction')
    print_logs(auction_contract, 'AuctionStarted', 'DutchAuction')
    print_logs(auction_contract, 'BidSubmission', 'DutchAuction')
    print_logs(auction_contract, 'AuctionEnded', 'DutchAuction')
    print_logs(auction_contract, 'ClaimedTokens', 'DutchAuction')
    print_logs(auction_contract, 'TokensDistributed', 'DutchAuction')


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


def auction_simulation(web3, wallet, token, auction, owner, bidders,
                       bid_interval=None, bid_start_price=None, sim_claim_tokens=False):
    print_all_logs(token, auction)

    log.info('{owner} {balance}'.format(owner=owner,
                                        balance=amount_format(web3, web3.eth.getBalance(owner))))

    # Start the auction
    log.info('Start auction owner balance %s' % amount_format(web3, web3.eth.getBalance(owner)))
    txhash = auction.transact({'from': owner}).startAuction()
    receipt = check_succesful_tx(web3, txhash, tx_timeout)

    assert auction.call().stage() == 2  # AuctionStarted

    # Make the bids

    # Timeout until price is = bid_start_price
    price_start = auction.call().price_start()
    assert price_start > 0
    price_constant = auction.call().price_constant()
    assert isinstance(price_constant, int)
    price_exponent = auction.call().price_exponent()
    assert isinstance(price_exponent, int)
    decimals = token.call().decimals()
    multiplier = 10**decimals
    assert multiplier > 0

    '''
    # Delay in seconds if we want to start the first bid at a certain price
    if bid_start_price:
        initial_bid_delay = elapsedAtPrice(bid_start_price, price_factor, price_constant, multiplier)
        assert initial_bid_delay >= 0, 'Price for first bid was set too high'
        log.info('Elapsed time until the first bid is made', initial_bid_delay
    '''  # noqa

    log.info('Timeout between bids {0}'.format(bid_interval or ' is random.'))

    from deploy.bidder import Bidder
    import gevent
    bidder_objs = [Bidder(web3, auction, addr) for addr in bidders]
    bidder_gevents = [gevent.spawn(b.run) for b in bidder_objs]

    gevent.joinall(bidder_gevents)
    del bidder_gevents

    assert auction.call({'from': owner}).missingFundsToEndAuction() == 0
    log.info('missing funds from=%s' % auction.call({'from': owner}).missingFundsToEndAuction())

    # Owner calls finalizeAuction
    txhash = auction.transact({'from': owner}).finalizeAuction()
    receipt = check_succesful_tx(web3, txhash)
    assert receipt is not None
    assert auction.call().stage() == 3  # AuctionEnded

    # distribute tokens

    def claim_tokens(auction, bidder):
        txhash = auction.transact({'from': bidder}).claimTokens()
        check_succesful_tx(web3, txhash)

    def get_balance(token, bidder):
        token_balance = token.call().balanceOf(bidder)
        log.info('{bidder} {tokens}'.format(bidder=bidder, tokens=token_balance))
        return token_balance

    if sim_claim_tokens is True:
        event_lst = [gevent.spawn(claim_tokens, auction, x)
                     for x in bidders]
        gevent.joinall(event_lst)
        event_lst = [gevent.spawn(get_balance, token, x)
                     for x in bidders]
        gevent.joinall(event_lst)
        total_balance = sum([ev.value for ev in event_lst])
        assert auction.call().stage() == 4  # TokensDistributed
        return total_balance
