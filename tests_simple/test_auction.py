import pytest
from ethereum import tester
from test_fixtures import (
    auction_contract,
    get_token_contract,
    token_contract,
    accounts,
    accounts_orders,
    auction_args,
    auction_supply,
    initial_supply,
    prealloc
)
import math
from functools import (
    reduce
)


def test_auction(chain, accounts, web3, auction_contract, get_token_contract):
    # Buyers accounts
    (Owner, A, B, C, D) = accounts(5)
    bidders = [A, B, C, D]
    eth = web3.eth
    orders = accounts_orders
    auction = auction_contract

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
        auction.transact().changeSettings(*auction_args[1])

    auction.transact().setup(token.address)
    assert auction.call().stage() == 1  # AuctionSetUp

    # Make sure we can change auction settings now
    auction.transact().changeSettings(*auction_args[0])

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
    assert total_tokens_claimable == auction.call().tokens_auctioned()

    owner_balance = token.call().balanceOf(Owner)
    for i in range(0, len(bidders)):
        bidder = bidders[i]

        if auction.call().bids(bidder):
            claimable = auction.call().bids(bidder) // final_price
            owner_fraction = auction.call().ownerFraction(claimable)
            bidder_balance = token.call().balanceOf(bidder)
            # print('^^^^claimable', claimable, owner_fraction, claimable / 10)

            auction.transact({'from': bidder}).claimTokens()

            owner_balance += owner_fraction
            bidder_balance += claimable - owner_fraction
            # FIXME
            # assert token.call().balanceOf(Owner) == owner_balance
            # assert token.call().balanceOf(bidder) == bidder_balance

        # Bidder cannot claim tokens again
        with pytest.raises(tester.TransactionFailed):
            auction.transact({'from': bidder}).claimTokens()

    # Check if all the auction tokens have been claimed
    total_tokens = auction.call().tokens_auctioned() + reduce((lambda x, y: x + y), prealloc)
    assert token.call().totalSupply() == total_tokens
    # FIXME
    # assert token.call().balanceOf(Owner) == owner_balance

    # Test if Auction funds have been transfered to Token
    funds_claimed = auction.call().funds_claimed()
    assert eth.getBalance(auction.address) == 0
    assert eth.getBalance(token.address) == funds_claimed

    assert auction.call().stage() == 5  # TradingStarted


def test_ownerFraction(accounts, auction_contract, token_contract):
    auction = auction_contract
    (Owner, A, B, C, D) = accounts(5)
    bidders = [A, B, C, D]
    token = token_contract(bidders, prealloc, auction)

    assert auction.call().ownerFraction(100000) == 10000
    assert auction.call().ownerFraction(123456) == 12345

    auction.transact().changeSettings(*auction_args[1])
    owner_fr = 100000 * auction_args[1][2] / math.pow(10, auction_args[1][3])
    assert auction.call().ownerFraction(100000) == owner_fr
