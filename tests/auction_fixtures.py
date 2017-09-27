import pytest
from ethereum import tester

from functools import (
    reduce
)

from fixtures import (
    owner_index,
    owner,
    wallet_address,
    get_bidders,
    create_contract,
    auction_contract,
    auction_contract_fast_decline,
    get_token_contract,
    token_contract,
    txnCost,
)


'''
    Auction price decay function
'''


def auction_price(price_start, price_constant, price_exponent, elapsed):
    price_decay = elapsed**(price_exponent) // price_constant
    return price_start * (1 + elapsed) // (1 + elapsed + price_decay)


@pytest.fixture()
def price(contract_params):
    def get(elapsed):
        return auction_price(*contract_params['args'], elapsed)
    return get


'''
    Various auction contracts in different stages.
'''


@pytest.fixture()
def auction_setup_contract(
    web3,
    owner,
    auction_contract,
    token_contract):
    auction = auction_contract

    # Initialize token
    token = token_contract(auction.address, {'from': owner})
    auction.transact({'from': owner}).setup(token.address)
    return auction


@pytest.fixture()
def auction_ended(
    web3,
    owner,
    get_bidders,
    token_contract,
    auction_contract_fast_decline,
    auction_bid_tested,
    auction_end_tests):
    eth = web3.eth
    auction = auction_contract_fast_decline
    bidders = get_bidders(10)

    # Initialize token
    token = token_contract(auction.address, {'from': owner})
    auction.transact({'from': owner}).setup(token.address)

    auction.transact({'from': owner}).startAuction()

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
            missing_funds = auction.call().missingFundsToEndAuction()
            amount = missing_funds
            auction_bid_tested(auction, bidder, amount)

        bidded += min(amount, missing_funds)
        index += 1

    print('NO OF BIDDERS', index)
    print('received_wei / bidded', auction.call().received_wei(), bidded)
    assert auction.call().received_wei() == bidded
    auction.transact({'from': owner}).finalizeAuction()
    auction_end_tests(auction, bidders[index])

    return (token, auction)


'''
    Auction tests that should always run after important actions.
    To be called from the integration tests.
'''


# Bid + tests that should run when bidding
@pytest.fixture(params=[True, False])
def auction_bid_tested(web3, request, wallet_address, txnCost, contract_params):
    def get(auction, bidder, amount):
        use_fallback = request.param
        bidder_pre_balance = web3.eth.getBalance(bidder)
        bidder_pre_a_balance = auction.call().bids(bidder)
        wallet_pre_balance = web3.eth.getBalance(wallet_address)

        if use_fallback:
            txn_cost = txnCost(web3.eth.sendTransaction({
                'from': bidder,
                'to': auction.address,
                'value': amount
            }))
        else:
            txn_cost = txnCost(auction.transact({'from': bidder, 'value': amount}).bid())
        assert auction.call().bids(bidder) == bidder_pre_a_balance + amount
        assert web3.eth.getBalance(wallet_address) == wallet_pre_balance + amount
        assert web3.eth.getBalance(auction.address) == 0
        assert web3.eth.getBalance(bidder) == bidder_pre_balance - amount - txn_cost
    return get


# Claim tokens + tests that should run when claiming tokens
@pytest.fixture()
def auction_claim_tokens_tested(web3, owner, contract_params):
    def get(token, auction, bidders, distributor=None):
        if type(bidders) == str:
            bidders = [bidders]

        values = []
        pre_balances = []
        expected_tokens = []

        token_multiplier = auction.call().token_multiplier()
        final_price = auction.call().final_price()
        auction_pre_balance = token.call().balanceOf(auction.address)
        pre_funds_claimed = auction.call().funds_claimed()

        assert auction.call().stage() == 3  # AuctionEnded
        assert final_price > 0

        for i, bidder in enumerate(bidders):
            print('auction_claim_tokens_tested bidder', bidder)
            values.append(auction.call().bids(bidder))
            tokens_expected = token_multiplier * values[i] // final_price
            expected_tokens.append(tokens_expected)
            pre_balances.append(token.call().balanceOf(bidder))

            if tokens_expected == 0:
                print('-- just claimed 0 tokens for a bid value of ', values[i])

            assert values[i] > 0

        if len(bidders) == 1:
            print('auction_claim_tokens_tested claimTokens', bidders[0])
            auction.transact({'from': bidders[0]}).claimTokens()
            # auction.transact({'from': owner}).claimTokens(bidders[0])
        else:
            print('auction_claim_tokens_tested distribute', bidders)
            distributor.transact({'from': owner}).distribute(bidders)

        for i, bidder in enumerate(bidders):
            assert token.call().balanceOf(bidder) == pre_balances[i] + expected_tokens[i]
            assert auction.call().bids(bidder) == 0

            # Bidder cannot claim tokens again
            with pytest.raises(tester.TransactionFailed):
                auction.transact({'from': bidder}).claimTokens()

        funds_claimed = auction.call().funds_claimed()
        funds_claimed_calculated = pre_funds_claimed + reduce((lambda x, y: x + y), values)
        assert funds_claimed == funds_claimed_calculated

        auction_balance = token.call().balanceOf(auction.address)
        claimed_tokens = reduce((lambda x, y: x + y), expected_tokens)
        auction_balance_calculated = auction_pre_balance - claimed_tokens
        assert auction_balance == auction_balance_calculated

    return get


# Tests that should run after the auction has ended
@pytest.fixture()
def auction_end_tests(web3, wallet_address):
    def get(auction, bidder):
        assert auction.call().stage() == 3  # AuctionEnded
        assert auction.call().missingFundsToEndAuction() == 0
        assert auction.call().price() == 0  # UI has to call final_price
        assert auction.call().final_price() > 0
        assert web3.eth.getBalance(wallet_address) >= auction.call().received_wei()

        with pytest.raises(tester.TransactionFailed):
            auction.transact({'from': bidder, "value": 1000}).bid()
        with pytest.raises(tester.TransactionFailed):
            auction.transact({'from': bidder, "value": 1}).bid()
        with pytest.raises(tester.TransactionFailed):
            auction.transact({'from': bidder, "value": 0}).bid()
    return get


# Tests that should run after the auction has ended
@pytest.fixture()
def auction_post_distributed_tests(web3, wallet_address):
    def get(auction):
        owner = auction.call().owner_address()
        assert auction.call().stage() == 4  # TokensDistributed

        assert auction.call().funds_claimed() == auction.call().received_wei()
        assert web3.eth.getBalance(wallet_address) >= auction.call().received_wei()
        assert web3.eth.getBalance(auction.address) == 0
    return get
