import pytest
from ethereum import tester
from test_fixtures import (
    auction_contract,
    get_token_contract,
    token_contract,
    auction_args,
    initial_supply,
    auction_supply,
    prealloc,
    multiplier
)
import math
from functools import (
    reduce
)


def test_auction(chain, web3, auction_contract, get_token_contract):
    eth = web3.eth
    auction = auction_contract

    # Bidder accounts
    owners = web3.eth.accounts[:2]
    bidders = web3.eth.accounts[2:]

    # Auction price after deployment; multiplier is 0 at this point
    assert auction.call().price() == 1

    # Initialize token
    token = get_token_contract([
        auction.address,
        initial_supply,
        owners,
        prealloc
    ])

    # Initial Auction state
    assert auction.call().stage() == 0  # AuctionDeployed
    assert eth.getBalance(auction.address) == 0

    # Auction setup without being the owner should fail
    with pytest.raises(tester.TransactionFailed):
        auction.transact({'from': bidders[1]}).setup(token.address)

    auction.transact().setup(token.address)
    assert auction.call().stage() == 1  # AuctionSetUp

    # Make sure we can change auction settings now
    auction.transact().changeSettings(*auction_args[0])

    # changeSettings without being the owner should fail
    with pytest.raises(tester.TransactionFailed):
        auction.transact({'from': bidders[1]}).changeSettings(*auction_args[1])

    # startAuction without being the owner should fail
    with pytest.raises(tester.TransactionFailed):
        auction.transact({'from': bidders[1]}).startAuction()

    # Auction price before auction start
    initial_price = multiplier * auction_args[0][0] // auction_args[0][1] + 1
    assert auction.call().price() == initial_price

    auction.transact().startAuction()
    assert auction.call().stage() == 2  # AuctionStarted
    assert auction.call().price() < initial_price

    # Cannot changeSettings after auction starts
    with pytest.raises(tester.TransactionFailed):
        auction.transact().changeSettings(*auction_args[1])

    # transferReserveToToken should fail (private)
    with pytest.raises(ValueError):
        auction.transact({'from': bidders[1]}).transferReserveToToken()

    # finalizeAuction should fail (private)
    with pytest.raises(ValueError):
        auction.transact({'from': bidders[1]}).finalizeAuction()

    # Set maximum amount for a bid - we don't want 1 account draining the auction
    missing_reserve = auction.call().missingReserveToEndAuction()
    maxBid = missing_reserve / 4

    # TODO Test multiple orders from 1 buyer

    # Bidders start ordering tokens
    bidders_len = len(bidders) - 1
    bidded = 0  # Total bidded amount
    index = 0  # bidders index

    # Make some bids with 1 wei to be sure we test rounding errors
    auction.transact({'from': bidders[0], "value": 1}).bid()
    auction.transact({'from': bidders[1], "value": 1}).bid()
    index = 2
    bidded = 2

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
    print('NO OF BIDDERS', index)

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
    assert auction.call().price() == 0  # UI has to call final_price

    # Claim all tokens
    # Final price per TKN (Tei * multiplier)
    final_price = auction.call().final_price()

    # Total Tei claimable
    total_tokens_claimable = eth.getBalance(auction.address) * multiplier // final_price
    print('FINAL PRICE', final_price)
    print('TOTAL TOKENS CLAIMABLE', int(total_tokens_claimable))
    assert int(total_tokens_claimable) == auction.call().tokens_auctioned()

    rounding_error_tokens = 0

    for i in range(0, index):
        bidder = bidders[i]

        # Calculate number of Tei issued for this bid
        claimable = auction.call().bids(bidder) * multiplier // final_price

        # Number of Tei assigned to the bidder
        bidder_balance = token.call().balanceOf(bidder)

        # Claim tokens -> tokens will be assigned to bidder
        auction.transact({'from': bidder}).claimTokens()

        # If auction funds not transfered to token (last claimTokens)
        # we test for a correct claimed tokens calculation
        balance_auction = eth.getBalance(auction.address)
        if balance_auction > 0:

            # Auction supply = unclaimed tokens, including rounding errors
            unclaimed_token_supply = token.call().balanceOf(auction.address)

            # Calculated unclaimed tokens
            unclaimed_reserve = eth.getBalance(auction.address) - auction.call().funds_claimed()
            unclaimed_tokens = multiplier * unclaimed_reserve // auction.call().final_price()

            # Adding previous rounding errors
            unclaimed_tokens += rounding_error_tokens

            # Token's auction balance should be the same as
            # the unclaimed tokens calculation based on the final_price
            # We assume a rounding error of 1
            if unclaimed_token_supply != unclaimed_tokens:
                rounding_error_tokens += 1
                unclaimed_tokens += 1
            assert unclaimed_token_supply == unclaimed_tokens

        # Check if bidder has the correct number of tokens
        bidder_balance += claimable
        assert token.call().balanceOf(bidder) == bidder_balance

        # Bidder cannot claim tokens again
        with pytest.raises(tester.TransactionFailed):
            auction.transact({'from': bidder}).claimTokens()

    # Check if all the auction tokens have been claimed
    total_tokens = auction.call().tokens_auctioned() + reduce((lambda x, y: x + y), prealloc)
    assert token.call().totalSupply() == total_tokens

    # Auction balance might be > 0 due to rounding errors
    assert token.call().balanceOf(auction.address) == rounding_error_tokens
    print('FINAL UNCLAIMED TOKENS', rounding_error_tokens)

    # Test if Auction funds have been transfered to Token
    funds_claimed = auction.call().funds_claimed()
    assert eth.getBalance(auction.address) == 0
    assert eth.getBalance(token.address) == funds_claimed

    # Check if auction stage has been changed
    assert auction.call().stage() == 5  # TradingStarted
