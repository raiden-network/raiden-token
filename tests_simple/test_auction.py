import pytest
from ethereum import tester
from test_fixtures import (
    auction_contract,
    get_token_contract,
    accounts,
    accounts_orders,
    xassert,
    xassert_threshold_price,
    auction_args
)
import math
from functools import (
    reduce
)


def test_auction(chain, accounts, web3, auction_contract, get_token_contract):
    # Buyers accounts
    (Owner, A, B, C, D) = accounts(5)

    eth = web3.eth
    orders = accounts_orders
    auction = auction_contract

    multiplier = 10**18
    initial_supply = 10000000 * multiplier
    auction_supply = 9000000 * multiplier
    prealloc = [
        200000 * multiplier,
        300000 * multiplier,
        400000 * multiplier,
        100000 * multiplier,
    ]
    bidders = [A, B, C, D]

    token = get_token_contract([
        auction.address,
        bidders,
        prealloc
    ])

    # Initial Auction state
    assert auction.call().stage() == 0  # AuctionDeployed
    assert eth.getBalance(auction.address) == 0

    # changeSettings needs AuctionSetUp
    with pytest.raises(tester.TransactionFailed):
        auction.transact().changeSettings(auction_args[1][0])

    auction.transact().setup(token.address)
    assert auction.call().stage() == 1  # AuctionSetUp

    # Make sure we can change auction settings now
    auction.transact().changeSettings(auction_args[0][0])

    auction.transact().startAuction()
    assert auction.call().stage() == 2  # AuctionStarted

    missing_reserve = auction.call().missingReserveToEndAuction()
    print('Initial missing_reserve', missing_reserve)
    # Buyers start ordering tokens

    # Test multiple orders from 1 buyer
    assert auction.call().bids(A) == 0
    auction.transact({'from': A, "value": orders[0][0] - 50}).bid()
    assert auction.call().bids(A) == orders[0][0] - 50
    auction.transact({'from': A, "value": 50}).bid()
    assert auction.call().bids(A) == orders[0][0]

    auction.transact({'from': B, "value": orders[1][0]}).bid()
    assert auction.call().bids(B) == orders[1][0]

    auction.transact({'from': C, "value": orders[2][0]}).bid()
    assert auction.call().bids(C) == orders[2][0]

    # Add all the orders up until this point
    bidded = 0
    for bidder in orders[0:len(orders) - 1]:
        bidded += bidder[0]
    assert eth.getBalance(auction.address) == bidded

    # Make an order > than missing_reserve to end auction
    while auction.call().missingReserveToEndAuction() > 0:
        (Bidder) = accounts(1)
        Bidder = Bidder[0]
        bidders.append(Bidder)
        missing_reserve = auction.call().missingReserveToEndAuction()
        # amount = min(missing_reserve, eth.getBalance(Bidder) - 4000000)
        amount = eth.getBalance(Bidder) - 4000000
        print('missing_reserve', missing_reserve, amount, eth.getBalance(Bidder))
        auction.transact({'from': Bidder, "value": amount}).bid()
        print('after bid balance', eth.getBalance(Bidder))
        bidded += amount

    assert auction.call().missingReserveToEndAuction() == 0

    # TODO check if account has received back the difference
    # gas_price = eth.gasPrice
    # receive_back -= receipt['gasUsed'] * gas_price
    # assert eth.getBalance(D) == receive_back

    # Auction ended, no more orders possible
    with pytest.raises(tester.TransactionFailed):
        auction.transact({'from': D, "value": 1000}).bid()

    assert auction.call().stage() == 3  # AuctionEnded

    # Claim all tokens
    final_price = auction.call().final_price()
    total_tokens_claimable = eth.getBalance(auction.address) / final_price
    print('FINAL PRICE', final_price)
    print('total_tokens_claimable', total_tokens_claimable)
    assert total_tokens_claimable == auction.call().MAX_TOKENS_SOLD()

    allocs = len(prealloc)
    for i in range(0, len(bidders)):
        bidder = bidders[i]

        # without // I got a case like
        # claimable = 89981237506524656 (in Python tests)
        # claimable = 89981237506524657 (in Solidity & online big number calculators)
        # even with claimable = math.floor(claimable)
        claimable = auction.call().bids(bidder) // final_price

        if i < allocs:
            preallocation = math.floor(prealloc[i])
        else:
            preallocation = 0

        # print(i, 'bidder', bidder, auction.call().bids(bidder), claimable, math.floor(claimable), preallocation)

        if auction.call().bids(bidder):
            auction.transact({'from': bidder}).claimTokens()
        assert token.call().balanceOf(bidder) == claimable + preallocation

        # Bidder cannot claim tokens again
        with pytest.raises(tester.TransactionFailed):
            auction.transact({'from': bidder}).claimTokens()

    # Check if all the auction tokens have been claimed
    total_tokens = auction.call().MAX_TOKENS_SOLD() + reduce((lambda x, y: x + y), prealloc)
    assert token.call().totalSupply() == total_tokens

    # Test if Auction funds have been transfered to Token
    funds_claimed = auction.call().funds_claimed()
    assert eth.getBalance(auction.address) == 0
    assert eth.getBalance(token.address) == funds_claimed

    assert auction.call().stage() == 5  # TradingStarted
