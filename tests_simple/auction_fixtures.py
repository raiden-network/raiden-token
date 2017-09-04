import pytest
from ethereum import tester
from functools import (
    reduce
)

from fixtures import (
    create_contract,
    auction_contract,
    get_token_contract,
    token_contract,
    auction_args,
    initial_supply,
    auction_supply,
    prealloc,
    multiplier,
    txnCost,
    terms_hash,
)

from utils import (
    hash_sign_msg,
)


@pytest.fixture()
def auction_setup_contract(web3, auction_contract, get_token_contract):
    auction = auction_contract
    owners = web3.eth.accounts[:2]

    # Initialize token
    token = get_token_contract([
        auction.address,
        initial_supply,
        owners,
        prealloc
    ])
    auction.transact().setup(token.address)
    return auction


# Bid + tests that should run when bidding
@pytest.fixture()
def auction_bid_tested(web3, txnCost):
    def get(auction, bidder, amount):
        # If bidder has not signed Terms and Conditions, he cannot bid
        if not auction.call().terms_signed(bidder):
            with pytest.raises(tester.TransactionFailed):
                auction.transact({'from': bidder, 'value': amount}).bid()

            # Sign Terms
            bidder_hash = hash_sign_msg(terms_hash, bidder)
            auction.transact({'from': bidder}).sign(bidder_hash)

        assert auction.call().terms_signed(bidder)

        bidder_pre_balance = web3.eth.getBalance(bidder)
        bidder_pre_a_balance = auction.call().bids(bidder)
        auction_pre_balance = web3.eth.getBalance(auction.address)
        missing_reserve = auction.call().missingReserveToEndAuction()
        accepted_amount = min(missing_reserve, amount)

        txn_cost = txnCost(auction.transact({'from': bidder, 'value': amount}).bid())

        assert auction.call().bids(bidder) == bidder_pre_a_balance + accepted_amount
        assert web3.eth.getBalance(auction.address) == auction_pre_balance + accepted_amount
        assert web3.eth.getBalance(bidder) == bidder_pre_balance - accepted_amount - txn_cost
    return get


@pytest.fixture()
def auction_started_fast_decline(web3, auction_setup_contract):
    auction = auction_setup_contract
    # Higher price decline
    auction.transact().changeSettings(2, multiplier)
    auction.transact().startAuction()
    return auction


@pytest.fixture()
def auction_ended(web3, auction_setup_contract, auction_bid_tested, auction_end_tests):
    eth = web3.eth
    auction = auction_setup_contract
    bidders = eth.accounts[2:]
    # Higher price decline
    auction.transact().changeSettings(2, multiplier)
    auction.transact().startAuction()

    # Set maximum amount for a bid - we don't want 1 account draining the auction
    missing_reserve = auction.call().missingReserveToEndAuction()
    maxBid = missing_reserve / 4

    # Bidders start ordering tokens
    bidders_len = len(bidders) - 1
    bidded = 0  # Total bidded amount
    index = 0  # bidders index

    # Make some bids with 1 wei to be sure we test rounding errors
    auction_bid_tested(auction, bidders[0], 1)
    auction_bid_tested(auction, bidders[1], 1)
    index = 2
    bidded = 2
    approx_bid_txn_cost = 4000000

    while auction.call().missingReserveToEndAuction() > 0:
        if bidders_len < index:
            print('!! Not enough accounts to simulate bidders')

        bidder = bidders[index]
        auction.transact({'from': bidder}).sign(hash_sign_msg(terms_hash, bidder))

        bidder_balance = eth.getBalance(bidder)
        assert auction.call().bids(bidder) == 0

        missing_reserve = auction.call().missingReserveToEndAuction()
        amount = int(min(bidder_balance - approx_bid_txn_cost, maxBid))

        auction_bid_tested(auction, bidder, amount)

        # txn_cost = txnCost(auction.transact({'from': bidder, "value": amount}).bid())
        bidded += min(amount, missing_reserve)
        '''
        if amount <= missing_reserve:
            assert auction.call().bids(bidder) == amount
            post_balance = bidder_balance - amount - txn_cost
        else:
            assert auction.call().bids(bidder) == missing_reserve
            post_balance = bidder_balance - missing_reserve - txn_cost
            print('-------! LAST BIDDER surplus to be returned:', amount - missing_reserve)

        assert eth.getBalance(bidder) == post_balance
        '''
        index += 1

    print('NO OF BIDDERS', index)

    assert eth.getBalance(auction.address) == bidded
    auction_end_tests(auction, bidders[index])

    return auction


# Tests that should run after the auction has ended
@pytest.fixture()
def auction_end_tests():
    def get(auction, bidder):
        assert auction.call().stage() == 3  # AuctionEnded
        assert auction.call().missingReserveToEndAuction() == 0
        assert auction.call().price() == 0  # UI has to call final_price
        assert auction.call().final_price() > 0

        with pytest.raises(tester.TransactionFailed):
            auction.transact({'from': bidder}).sign(hash_sign_msg(terms_hash, bidder))
        with pytest.raises(tester.TransactionFailed):
            auction.transact({'from': bidder, "value": 1000}).bid()
        with pytest.raises(tester.TransactionFailed):
            auction.transact({'from': bidder, "value": 1}).bid()
        with pytest.raises(tester.TransactionFailed):
            auction.transact({'from': bidder, "value": 0}).bid()
    return get
