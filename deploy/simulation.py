import random
from web3.utils.compat import (
    Timeout,
)
from utils import (
    passphrase,
    check_succesful_tx,
    print_logs,
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


def amount_format(web3, wei):
    return "{0} WEI = {1} ETH".format(wei, web3.fromWei(wei, 'ether'))


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
            print('BID successful')
            bid_successful = amount
        except:
            missing = auction.call().missingFundsToEndAuction()
            amount = missing // 7
            print('Bid > missing funds, trying with {0} WEI'.format(amount))
    return amount


def auction_simulation(web3, wallet, token, auction, owner, bidders, bids=500, bid_interval=None, bid_start_price=None):
    bids = {}
    approx_payable_txn_cost = 30000
    approx_bid_txn_cost = 40000
    bidders_len = len(bidders)
    print_all_logs(token, auction)

    print('Owner balance:', owner, amount_format(web3, web3.eth.getBalance(owner)))

    # Start the auction
    print('Start auction owner balance', amount_format(web3, web3.eth.getBalance(owner)))
    txhash = auction.transact({'from': owner}).startAuction()
    receipt = check_succesful_tx(web3, txhash, tx_timeout)

    assert auction.call().stage() == 2  # AuctionStarted

    # Make the bids

    # Timeout until price is = bid_start_price
    price_start = auction.call().price_start()
    price_constant = auction.call().price_constant()
    price_exponent = auction.call().price_exponent()
    decimals = token.call().decimals()
    multiplier = 10**decimals
    initial_bid_delay = 0

    '''
    # Delay in seconds if we want to start the first bid at a certain price
    if bid_start_price:
        initial_bid_delay = elapsedAtPrice(bid_start_price, price_factor, price_constant, multiplier)
        assert initial_bid_delay >= 0, 'Price for first bid was set too high'
        print('Elapsed time until the first bid is made', initial_bid_delay
    '''

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

        # Avoid overbidding, otherwise the bid will fail
        delta_overbid = missing_funds / 10

        bidder_balance = web3.eth.getBalance(bidder)
        max_bid = int((missing_funds - delta_overbid) / (bidders_len - bidder_number))

        # Take the minimum between the bidder's balance and the max bid amount
        amount = int(min(bidder_balance - approx_bid_txn_cost, max_bid))

        unlocked = web3.personal.unlockAccount(bidder, passphrase)

        print('BID bidder, missing_funds, balance, amount', bidder, missing_funds, bidder_balance, amount_format(web3, amount))

        if bidder_number == bidders_len - 1:
            print('Bidding / Waiting until missing funds = 0')
            with Timeout() as timeout:
                while auction.call().missingFundsToEndAuction() > 0:
                    print("Missing funds: ", auction.call().missingFundsToEndAuction())

                    if web3.eth.getBalance(bidder) > amount:
                        amount = successful_bid(web3, auction, bidder, amount)
                    timeout.sleep(5)

        bids[bidder] += amount
        # TODO assert bid amout?
        bidder_number += 1

    assert auction.call({'from': owner}).missingFundsToEndAuction() == 0
    print('missing funds', auction.call({'from': owner}).missingFundsToEndAuction())

    # Owner calls finalizeAuction
    txhash = auction.transact({'from': owner}).finalizeAuction()
    receipt = check_succesful_tx(web3, txhash)

    print('stage', auction.call().stage())
    assert auction.call().stage() == 3  # AuctionEnded
