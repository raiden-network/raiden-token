import random
from web3.utils.compat import (
    Timeout,
)
from utils import check_succesful_tx

passphrase = '0'
tx_timeout = 180

# TODO
# multiple bids same bidders
# If bidders have remaining balances, we should send them back to the owner


# Calculate auction factors given 2 price points (price, elapsed_time)
def getAuctionFactors(price1, elapsed1, price2, elapsed2, multiplier):
    price_const = int((elapsed2 * (price2 - 1) - elapsed1 * (price1 - 1)) / (price1 - price2))
    price_factor = int((price2 - 1) * (elapsed2 + price_const) / multiplier)
    return (price_factor, price_const)


# TODO check negative elapsed
# Seconds that should elapse since auction start, in order to get the given price
def elapsedAtPrice(price, price_factor, price_constant, multiplier):
    elapsed = (multiplier * price_factor) / (price - 1) - price_constant
    return int(elapsed)


def amount_format(web3, wei):
    return "{0} WEI = {1} ETH".format(wei, web3.fromWei(wei, 'ether'))


# Return funds to owner, so we keep most of the ETH in the simulation
def returnFundsToOwner(web3, owner, bidders):
    for bidder in bidders:
        # Return most ETH to owner
        value = web3.eth.getBalance(bidder)
        gas_estimate = web3.eth.estimateGas({'from': bidder, 'to': owner, 'value': value}) + 10000
        value -= gas_estimate

        if value < 0:
            continue

        # We have to unlock the account first
        unlocked = web3.personal.unlockAccount(bidder, passphrase)
        txhash = web3.eth.sendTransaction({'from': bidder, 'to': owner, 'value': value})
        receipt = check_succesful_tx(web3, txhash, tx_timeout)


def auction_simulation(web3, token, auction, owner, bidders, bids=500, bid_interval=None, bid_start_price=1000000000000000000):
    bids = {}
    approx_payble_txn_cost = 30000
    approx_bid_txn_cost = 40000
    bidders_len = len(bidders)

    # Return previous simulation funds back to owner
    print('First return to the owner any past auction funds locked in the bidders accounts.')
    returnFundsToOwner(web3, owner, bidders)
    print('Owner balance:', owner, amount_format(web3, web3.eth.getBalance(owner)))

    # Transfer some testnet ether to the bidders
    print('Assign random ETH amounts to bidders')

    # Make sure we have some 1 ETH bids
    txhash = web3.eth.sendTransaction({'from': owner, 'to': bidders[0], 'value': 1 + approx_bid_txn_cost})
    receipt = check_succesful_tx(web3, txhash, tx_timeout)

    txhash = web3.eth.sendTransaction({'from': owner, 'to': bidders[1], 'value': 1 + approx_bid_txn_cost})
    receipt = check_succesful_tx(web3, txhash, tx_timeout)

    txhash = web3.eth.sendTransaction({'from': owner, 'to': bidders[2], 'value': 2 + approx_bid_txn_cost})
    receipt = check_succesful_tx(web3, txhash, tx_timeout)

    # Make sure bidders have random ETH
    for i in range(3, bidders_len - 1):
        bidder = bidders[i]
        owner_balance = web3.eth.getBalance(owner)
        max_bid = int(owner_balance / (bidders_len - i))
        value = random.randint(max_bid / 2, max_bid)
        print('i', i, bidder, amount_format(web3, value))

        txhash = web3.eth.sendTransaction({'from': owner, 'to': bidder, 'value': value})
        receipt = check_succesful_tx(web3, txhash, tx_timeout)

    owner_balance = web3.eth.getBalance(owner)
    if owner_balance > 0:
        bidder = bidders[bidders_len - 1]
        value = owner_balance - approx_payble_txn_cost
        print('i', bidders_len - 1, bidder, amount_format(web3, value))

        txhash = web3.eth.sendTransaction({'from': owner, 'to': bidders[bidders_len - 1], 'value': value})
        receipt = check_succesful_tx(web3, txhash, tx_timeout)

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
    # Delay in seconds
    initial_bid_delay = elapsedAtPrice(bid_start_price, price_factor, price_constant, multiplier)
    assert initial_bid_delay >= 0, 'Price for first bid was set too high'
    print('Elapsed time until the first bid is made', initial_bid_delay)
    print('Timeout between bids', bid_interval)

    with Timeout() as timeout:
        timeout.sleep(int(initial_bid_delay))  # seconds
    print('Simulation bids start at', amount_format(web3, auction.call().price()))

    # Have some 1 wei bids
    unlocked = web3.personal.unlockAccount(bidders[0], passphrase)
    unlocked = web3.personal.unlockAccount(bidders[1], passphrase)
    unlocked = web3.personal.unlockAccount(bidders[2], passphrase)
    txhash = auction.transact({'from': bidders[0], "value": 1}).bid()
    receipt = check_succesful_tx(web3, txhash)
    txhash = auction.transact({'from': bidders[1], "value": 1}).bid()
    receipt = check_succesful_tx(web3, txhash)
    txhash = auction.transact({'from': bidders[2], "value": 2}).bid()
    receipt = check_succesful_tx(web3, txhash)

    bidder_number = 3

    # Continue bidding until auction ends
    while auction.call().missingReserveToEndAuction() > 0:
        bidder = bidders[bidder_number]
        bids[bidder] = 0
        missing_reserve = auction.call().missingReserveToEndAuction()
        bidder_balance = web3.eth.getBalance(bidder)
        max_bid = int(missing_reserve / (bidders_len - bidder_number))
        amount = int(min(bidder_balance - approx_bid_txn_cost, max_bid))
        print('BID', bidder, bidder_balance, amount_format(web3, amount))

        # Check if last bidder - we want to close the auction
        if bidder_number == bidders_len - 1 and missing_reserve > bidder_balance:
            # Calculate wanted price from the maximum amount of ETH that we can bid
            wanted_price = multiplier * (amount + web3.eth.getBalance(auction.address)) / auction.call().tokens_auctioned()
            # Calculate elapsed time needed to reach the wanted price (from auction start)
            elapsed = elapsedAtPrice(wanted_price, price_factor, price_constant, multiplier)

            # Calculate how much time we need to wait for the wanted price
            price_now = auction.call().price()
            elapsed_now = elapsedAtPrice(price_now, price_factor, price_constant, multiplier)
            bid_interval = elapsed - elapsed_now
            print('elapsed, elapsed_now', elapsed, elapsed_now)
            print('wanted_price, price_now', wanted_price, price_now)
            print('Last bid delayed {0} seconds in order to wait for a smaller auction price.'.format(bid_interval))

        # Timeout between bids
        if bid_interval:
            with Timeout() as timeout:
                timeout.sleep(bid_interval)  # seconds

        unlocked = web3.personal.unlockAccount(bidder, passphrase)
        txhash = auction.transact({'from': bidder, "value": amount}).bid()
        receipt = check_succesful_tx(web3, txhash)

        bids[bidder] += amount
        assert auction.call().bids(bidder) == bids[bidder]
        bidder_number += 1


    assert auction.call().stage() == 3  # AuctionEnded
