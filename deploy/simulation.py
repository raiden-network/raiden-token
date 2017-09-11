import random
from web3.utils.compat import (
    Timeout,
)
from utils import (
    check_succesful_tx,
    print_logs,
)

passphrase = '0'
tx_timeout = 180

# TODO
# multiple bids same bidders
# If bidders have remaining balances, we should send them back to the owner


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


def amount_format(web3, wei):
    return "{0} WEI = {1} ETH".format(wei, web3.fromWei(wei, 'ether'))


def print_auction(auction_contract):
    print_logs(auction_contract, 'Deployed', 'DutchAuction')
    print_logs(auction_contract, 'Setup', 'DutchAuction')
    print_logs(auction_contract, 'SettingsChanged', 'DutchAuction')
    print_logs(auction_contract, 'AuctionStarted', 'DutchAuction')
    print_logs(auction_contract, 'BidSubmission', 'DutchAuction')
    print_logs(auction_contract, 'AuctionEnded', 'DutchAuction')
    print_logs(auction_contract, 'ClaimedTokens', 'DutchAuction')
    print_logs(auction_contract, 'TokensDistributed', 'DutchAuction')
    print_logs(auction_contract, 'TradingStarted', 'DutchAuction')


def auction_simulation(web3, token, auction, owner, bidders, bids=500, bid_interval=None, bid_start_price=None):
    bids = {}
    approx_payable_txn_cost = 30000
    approx_bid_txn_cost = 40000
    bidders_len = len(bidders)
    print_auction(auction)

    print('Owner balance:', owner, amount_format(web3, web3.eth.getBalance(owner)))

    # Start the auction
    print('Start auction owner balance', amount_format(web3, web3.eth.getBalance(owner)))
    txhash = auction.transact({'from': owner}).startAuction()
    receipt = check_succesful_tx(web3, txhash, tx_timeout)

    assert auction.call().stage() == 2  # AuctionStarted

    # Make the bids

    # Timeout until price is = bid_start_price
    price_factor = auction.call().price_factor()
    price_constant = auction.call().price_const()
    decimals = token.call().decimals()
    multiplier = 10**decimals
    initial_bid_delay = 0

    # Delay in seconds if we want to start the first bid at a certain price
    if bid_start_price:
        initial_bid_delay = elapsedAtPrice(bid_start_price, price_factor, price_constant, multiplier)
        assert initial_bid_delay >= 0, 'Price for first bid was set too high'
        print('Elapsed time until the first bid is made', initial_bid_delay)

    print('Timeout between bids', bid_interval or ' is random.')

    with Timeout() as timeout:
        timeout.sleep(int(initial_bid_delay))  # seconds

    # Have some 1 wei bids
    unlocked = web3.personal.unlockAccount(bidders[0], passphrase)
    unlocked = web3.personal.unlockAccount(bidders[1], passphrase)
    unlocked = web3.personal.unlockAccount(bidders[2], passphrase)

    print('Simulation bids start at', amount_format(web3, auction.call().price()))

    txhash = auction.transact({'from': bidders[0], "value": 1}).bid()
    receipt = check_succesful_tx(web3, txhash)

    txhash = auction.transact({'from': bidders[1], "value": 1}).bid()
    receipt = check_succesful_tx(web3, txhash)

    txhash = auction.transact({'from': bidders[2], "value": 2}).bid()
    receipt = check_succesful_tx(web3, txhash)

    bidder_number = 3

    # Continue bidding until auction ends
    while auction.call().missingFundsToEndAuction() > 0:

        # Timeout between bids
        if bid_interval or bid_interval == 0:
            interval = bid_interval
        else:
            interval = random.randint(0, 30)
        print('Timeout to next bid: {0} seconds'.format(interval))
        with Timeout() as timeout:
            timeout.sleep(interval)  # seconds

        bidder = bidders[bidder_number]
        bids[bidder] = 0
        missing_funds = auction.call().missingFundsToEndAuction()
        bidder_balance = web3.eth.getBalance(bidder)
        max_bid = int(missing_funds / (bidders_len - bidder_number))
        amount = int(min(bidder_balance - approx_bid_txn_cost, max_bid))
        print('BID bidder, missing_funds, balance, amount', bidder, missing_funds, bidder_balance, amount_format(web3, amount))

        # Check if last bidder - we want to close the auction
        if bidder_number == bidders_len - 1 and missing_funds > amount:
            # Calculate wanted price from the maximum amount of ETH that we can bid
            wanted_price = multiplier * (amount + web3.eth.getBalance(auction.address)) / auction.call().tokens_auctioned()
            # Calculate elapsed time needed to reach the wanted price (from auction start)
            elapsed = elapsedAtPrice(wanted_price, price_factor, price_constant, multiplier)

            # Calculate how much time we need to wait for the wanted price
            price_now = auction.call().price()
            elapsed_now = elapsedAtPrice(price_now, price_factor, price_constant, multiplier)
            interval = elapsed - elapsed_now
            print('elapsed, elapsed_now', elapsed, elapsed_now)
            print('wanted_price, price_now', wanted_price, price_now)
            print('Last bid delayed {0} seconds in order to wait for a smaller auction price.'.format(interval))
            with Timeout() as timeout:
                timeout.sleep(interval)  # seconds

        unlocked = web3.personal.unlockAccount(bidder, passphrase)
        txhash = auction.transact({'from': bidder, "value": amount}).bid()
        receipt = check_succesful_tx(web3, txhash)

        with Timeout() as timeout:
            timeout.sleep(10)

        bids[bidder] += amount
        # TODO - fix this assert + last bid after process is determined
        if bidder_number < bidders_len - 1:
            assert auction.call().bids(bidder) == bids[bidder]
        bidder_number += 1

    print('missing funds', auction.call().missingFundsToEndAuction())
    print('stage', auction.call().stage())
    assert auction.call().stage() == 3  # AuctionEnded
