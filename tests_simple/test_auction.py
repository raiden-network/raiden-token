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
    prealloc,
    multiplier
)
import math
from functools import (
    reduce
)


def test_auction(chain, accounts, web3, auction_contract, get_token_contract):
    eth = web3.eth
    orders = accounts_orders
    auction = auction_contract

    # Bidder accounts
    bidders = web3.eth.accounts
    Owner = bidders[0]
    bidders = bidders[1:]

    # Initialize token
    token = get_token_contract([
        auction.address,
        bidders[1:5],
        prealloc
    ])

    # Initial Auction state
    assert auction.call().stage() == 0  # AuctionDeployed
    assert eth.getBalance(auction.address) == 0

    # changeSettings needs stage = AuctionSetUp, so it will fail now
    with pytest.raises(tester.TransactionFailed):
        auction.transact().changeSettings(*auction_args[1])

    auction.transact().setup(token.address)
    assert auction.call().stage() == 1  # AuctionSetUp

    # Make sure we can change auction settings now
    auction.transact().changeSettings(*auction_args[0])

    auction.transact().startAuction()
    assert auction.call().stage() == 2  # AuctionStarted

    # Set maximum amount for a bid - we don't want 1 account draining the auction
    missing_reserve = auction.call().missingReserveToEndAuction()
    maxBid = missing_reserve / 4;

    # TODO Test multiple orders from 1 buyer

    # Bidders start ordering tokens
    bidders_len = len(bidders) - 1
    bidded = 0  # Total bidded amount
    index = 0  # bidders index

    while auction.call().missingReserveToEndAuction() > 0:
        if bidders_len < index:
            print('!! Not enough accounts to simulate bidders')

        bidder = bidders[index]
        balance = eth.getBalance(bidder)
        assert auction.call().bids(bidder) == 0

        missing_reserve = auction.call().missingReserveToEndAuction()
        amount = int(min(balance - 4000000, maxBid))

        auction.transact({'from': bidder, "value": amount}).bid()
        bidded += min(amount, missing_reserve)

        if amount <= missing_reserve:
            assert auction.call().bids(bidder) == amount
        else:
            assert auction.call().bids(bidder) == missing_reserve

        index += 1

    assert eth.getBalance(auction.address) == bidded
    assert auction.call().missingReserveToEndAuction() == 0

    # TODO check if account has received back the difference
    # gas_price = eth.gasPrice
    # receive_back -= receipt['gasUsed'] * gas_price
    # assert eth.getBalance(D) == receive_back

    # Auction ended, no more orders possible
    if bidders_len < index:
        print('!! Not enough accounts to simulate bidders. 1 additional account needed')
    with pytest.raises(tester.TransactionFailed):
        auction.transact({'from': bidders[index], "value": 1000}).bid()

    assert auction.call().stage() == 3  # AuctionEnded

    # Claim all tokens
    # Final price per TKN (Tei * multiplier)
    final_price = auction.call().final_price()

    # Total Tei claimable
    total_tokens_claimable = eth.getBalance(auction.address) * multiplier / final_price
    print('FINAL PRICE', final_price)
    print('TOTAL TOKENS CLAIMABLE', total_tokens_claimable)
    assert total_tokens_claimable == auction.call().tokens_auctioned()

    owner_balance = token.call().balanceOf(Owner)

    for i in range(0, index):
        bidder = bidders[i]

        # Calculate number of Tei issued for this bid
        claimable = auction.call().bids(bidder) * multiplier // final_price

        # Number of Tei assigned to owner
        owner_fraction = auction.call().ownerFraction(claimable)

        # Number of Tei assigned to the bidder
        bidder_balance = token.call().balanceOf(bidder)

        # Claim tokens -> tokens will be assigned to owner + bidder
        auction.transact({'from': bidder}).claimTokens()

        # Check if owner & bidder have the correct number of tokens
        owner_balance += owner_fraction
        bidder_balance += claimable - owner_fraction
        assert token.call().balanceOf(Owner) == owner_balance
        assert token.call().balanceOf(bidder) == bidder_balance

        # Bidder cannot claim tokens again
        with pytest.raises(tester.TransactionFailed):
            auction.transact({'from': bidder}).claimTokens()

    # Check if all the auction tokens have been claimed
    total_tokens = auction.call().tokens_auctioned() + reduce((lambda x, y: x + y), prealloc)
    assert token.call().totalSupply() == total_tokens
    assert token.call().balanceOf(Owner) == owner_balance

    # Test if Auction funds have been transfered to Token
    funds_claimed = auction.call().funds_claimed()
    assert eth.getBalance(auction.address) == 0
    assert eth.getBalance(token.address) == funds_claimed

    # Check if auction stage has been changed
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
