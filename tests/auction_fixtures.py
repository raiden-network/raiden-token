import pytest
from ethereum import tester

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
)


@pytest.fixture()
def auction_setup_contract(
    web3,
    auction_contract,
    get_token_contract):
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
        bidder_pre_balance = web3.eth.getBalance(bidder)
        bidder_pre_a_balance = auction.call().bids(bidder)
        auction_pre_balance = web3.eth.getBalance(auction.address)
        missing_funds = auction.call().missingFundsToEndAuction()
        accepted_amount = min(missing_funds, amount)

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
def auction_ended(
    web3,
    auction_setup_contract,
    auction_bid_tested,
    auction_end_tests):
    eth = web3.eth
    auction = auction_setup_contract
    bidders = eth.accounts[2:]
    # Higher price decline
    auction.transact().changeSettings(2, multiplier)
    auction.transact().startAuction()

    # Set maximum amount for a bid - we don't want 1 account draining the auction
    missing_funds = auction.call().missingFundsToEndAuction()
    maxBid = missing_funds / 4

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

    while auction.call().missingFundsToEndAuction() > 0:
        if bidders_len < index:
            print('!! Not enough accounts to simulate bidders')

        bidder = bidders[index]

        bidder_balance = eth.getBalance(bidder)
        assert auction.call().bids(bidder) == 0

        missing_funds = auction.call().missingFundsToEndAuction()
        amount = int(min(bidder_balance - approx_bid_txn_cost, maxBid))

        if amount <= missing_funds:
            auction_bid_tested(auction, bidder, amount)
        else:
            # Fail if we bid more than missing_funds
            with pytest.raises(tester.TransactionFailed):
                auction_bid_tested(auction, bidder, amount)

            # Bid exactly the amount needed in order to end the auction
            amount = missing_funds
            auction_bid_tested(auction, bidder, amount)

        bidded += min(amount, missing_funds)
        index += 1

    print('NO OF BIDDERS', index)

    assert eth.getBalance(auction.address) == bidded
    auction.transact().finalizeAuction()
    auction_end_tests(auction, bidders[index])

    return auction


# Tests that should run after the auction has ended
@pytest.fixture()
def auction_end_tests():
    def get(auction, bidder):
        assert auction.call().stage() == 3  # AuctionEnded
        assert auction.call().missingFundsToEndAuction() == 0
        assert auction.call().price() == 0  # UI has to call final_price
        assert auction.call().final_price() > 0

        with pytest.raises(tester.TransactionFailed):
            auction.transact({'from': bidder, "value": 1000}).bid()
        with pytest.raises(tester.TransactionFailed):
            auction.transact({'from': bidder, "value": 1}).bid()
        with pytest.raises(tester.TransactionFailed):
            auction.transact({'from': bidder, "value": 0}).bid()
    return get


# Tests that should run after the auction has ended
@pytest.fixture()
def auction_claimed_tests(web3):
    def get(auction, owner_pre_balance, auction_pre_balance):
        owner = auction.call().owner()
        assert auction.call().stage() == 5  # TradingStarted

        # Test if Auction funds have been transfered to the owner
        assert web3.eth.getBalance(auction.address) == 0
        assert auction.call().funds_claimed() == auction_pre_balance
        # assert web3.eth.getBalance(owner) == owner_pre_balance + auction_pre_balance
        assert web3.eth.getBalance(owner) >= owner_pre_balance + auction_pre_balance
    return get
