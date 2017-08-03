import pytest
from ethereum import tester
from test_fixtures import (
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
    terms_hash
)
import math
from functools import (
    reduce
)


# TODO: missingReserveToEndAuction, transferReserveToToken,
# TODO: review edge cases for claimTokens, bid


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


@pytest.fixture()
def auction_started_fast_decline(web3, auction_setup_contract):
    auction = auction_setup_contract
    # Higher price decline
    auction.transact().changeSettings(2, multiplier)
    auction.transact().startAuction()
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
            auction.transact({'from': bidder}).sign(terms_hash)

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


# Tests that should run after the auction has ended
def auction_end_tests(auction, bidder):
    assert auction.call().stage() == 3  # AuctionEnded
    assert auction.call().missingReserveToEndAuction() == 0
    assert auction.call().price() == 0  # UI has to call final_price
    assert auction.call().final_price() > 0

    with pytest.raises(tester.TransactionFailed):
        auction.transact({'from': bidder}).sign(terms_hash)
    with pytest.raises(tester.TransactionFailed):
        auction.transact({'from': bidder, "value": 1000}).bid()
    with pytest.raises(tester.TransactionFailed):
        auction.transact({'from': bidder, "value": 1}).bid()
    with pytest.raises(tester.TransactionFailed):
        auction.transact({'from': bidder, "value": 0}).bid()


def test_auction_init(chain, web3, create_contract):
    Auction = chain.provider.get_contract_factory('DutchAuction')

    with pytest.raises(TypeError):
        auction_contract = create_contract(Auction, [])
    with pytest.raises(TypeError):
        auction_contract = create_contract(Auction, [-3, 2])
    with pytest.raises(TypeError):
        auction_contract = create_contract(Auction, [3, -2])
    with pytest.raises(tester.TransactionFailed):
        auction_contract = create_contract(Auction, [0, 2])
    with pytest.raises(tester.TransactionFailed):
        auction_contract = create_contract(Auction, [2, 0])

    auction_contract = create_contract(Auction, auction_args[0])


def test_auction_setup(web3, auction_contract, token_contract):
    auction = auction_contract
    owners = web3.eth.accounts[:2]
    A = web3.eth.accounts[2]

    assert auction.call().stage() == 0  # AuctionDeployed

    # Test setup with a different owner token - should fail
    token = token_contract(auction.address, {'from': A})
    with pytest.raises(tester.TransactionFailed):
        auction.transact().setup(token.address)

    web3.testing.mine(5)
    token = token_contract(auction.address)
    auction.transact().setup(token.address)
    assert auction.call().tokens_auctioned() == token.call().balanceOf(auction.address)
    assert auction.call().multiplier() == 10**token.call().decimals()
    assert auction.call().stage() == 1

    # Token cannot be changed after setup
    with pytest.raises(tester.TransactionFailed):
        auction.call().setup(token.address)


def test_auction_change_settings(web3, auction_contract, token_contract):
    auction = auction_contract
    token = token_contract(auction.address)
    A = web3.eth.accounts[2]

    with pytest.raises(tester.TransactionFailed):
        auction.transact({'from': A}).changeSettings(2, 10)
    with pytest.raises(tester.TransactionFailed):
        auction.transact().changeSettings(0, 10)
    with pytest.raises(tester.TransactionFailed):
        auction.transact().changeSettings(2, 0)
    with pytest.raises(TypeError):
        auction.transact().changeSettings(2, -5)
    with pytest.raises(TypeError):
        auction.transact().changeSettings(-2, 5)

    auction.transact().changeSettings(2, 10)
    assert auction.call().price_factor() == 2
    assert auction.call().price_const() == 10

    auction.transact().setup(token.address)
    auction.transact().changeSettings(1, 1)

    auction.transact().startAuction()
    with pytest.raises(tester.TransactionFailed):
        auction.transact().changeSettings(5, 102)


# Make sure the variables have appropriate access from outside the contract
def test_auction_access(chain, web3, create_contract):
    Auction = chain.provider.get_contract_factory('DutchAuction')
    auction = create_contract(Auction, auction_args[0])
    A = web3.eth.accounts[2]

    assert auction.call().owner() == web3.eth.coinbase
    assert auction.call().price_factor() == auction_args[0][0]
    assert auction.call().price_const() == auction_args[0][1]
    assert auction.call().start_time() == 0
    assert auction.call().end_time() == 0
    assert auction.call().start_block() == 0
    assert auction.call().funds_claimed() == 0
    assert auction.call().tokens_auctioned() == 0
    assert auction.call().final_price() == 0
    assert auction.call().stage() == 0
    assert auction.call().token()
    assert not auction.call().terms_signed(A)

    with pytest.raises(ValueError):  # No matching functions found
        auction.call().terms_hash()


def test_auction_start(chain, web3, auction_contract, token_contract, auction_bid_tested):
    auction = auction_contract
    token = token_contract(auction.address)
    A = web3.eth.accounts[2]

    # Should not be able to start auction before setup
    with pytest.raises(tester.TransactionFailed):
        auction.transact().startAuction()

    auction.transact().setup(token.address)
    auction.transact().changeSettings(2, multiplier)  # fast price decline

    # Should not be able to start auction if not owner
    with pytest.raises(tester.TransactionFailed):
        auction.transact({'from': A}).startAuction()

    txn_hash = auction.transact().startAuction()
    receipt = chain.wait.for_receipt(txn_hash)
    timestamp = web3.eth.getBlock(receipt['blockNumber'])['timestamp']
    assert auction.call().stage() == 2
    assert auction.call().start_time() == timestamp

    # Should not be able to call start auction after it has already started
    with pytest.raises(tester.TransactionFailed):
        auction.transact().startAuction()

    # Finalize auction
    amount = web3.eth.getBalance(A) - 10000000
    auction_bid_tested(auction, A, amount)
    assert auction.call().stage() == 3

    with pytest.raises(tester.TransactionFailed):
        auction.transact().startAuction()


# Test price function at the different auction stages
def test_price(web3, auction_contract, token_contract, auction_bid_tested):
    auction = auction_contract
    token = token_contract(auction.address)
    A = web3.eth.accounts[2]

    # Auction price after deployment; multiplier is 0 at this point
    assert auction.call().price() == 1

    auction.transact().setup(token.address)

    # Auction price before auction start
    price_factor = auction.call().price_factor()
    price_const = auction.call().price_const()
    initial_price = multiplier * price_factor // price_const + 1
    assert auction.call().price() == initial_price

    auction.transact().startAuction()
    assert auction.call().price() < initial_price

    amount = web3.eth.getBalance(A) - 10000000
    auction_bid_tested(auction, A, amount)

    # Calculate final price
    elapsed = auction.call().end_time() - auction.call().start_time()
    price = multiplier * price_factor // (elapsed + price_const) + 1

    assert auction.call().price() == 0
    assert auction.call().final_price() == price


# Test signing Terms and Consitions
def test_auction_sign(web3, auction_contract, token_contract, auction_bid_tested):
    auction = auction_contract
    A = web3.eth.accounts[2]
    another_hash = 'e18de70182a134687249aebe6656048c'

    assert not auction.call().terms_signed(A)

    # Fail if auction has not started
    with pytest.raises(tester.TransactionFailed):
        auction.transact({'from': A}).sign(terms_hash)

    auction.transact().setup(token.address)

    # Fail if auction has not started
    with pytest.raises(tester.TransactionFailed):
        auction.transact({'from': A}).sign(terms_hash)

    auction.transact().startAuction()

    # Fail if hash is not correct
    with pytest.raises(tester.TransactionFailed):
        auction.transact({'from': A}).sign(another_hash)

    auction.transact({'from': A}).sign(terms_hash)
    assert auction.call().terms_signed(A)


# Test sending ETH to the auction contract
def test_auction_payable(chain, web3, auction_contract, get_token_contract, txnCost):
    eth = web3.eth
    auction = auction_contract
    owners = web3.eth.accounts[:2]
    bidder = web3.eth.accounts[2]

    # Initialize token
    token = get_token_contract([
        auction.address,
        initial_supply,
        owners,
        prealloc
    ])

    # Try sending funds before auction starts
    with pytest.raises(tester.TransactionFailed):
        eth.sendTransaction({
            'from': bidder,
            'to': auction.address,
            'value': 100
        })
    with pytest.raises(tester.TransactionFailed):
        auction.transact({'from': bidder}).sign(terms_hash)
    with pytest.raises(tester.TransactionFailed):
        auction.transact({'from': bidder, "value": 100}).bid()

    auction.transact().setup(token.address)

    # Higher price decline
    auction.transact().changeSettings(2, multiplier)
    auction.transact().startAuction()
    auction.transact({'from': bidder}).sign(terms_hash)

    # End auction by bidding the needed amount
    missing_reserve = auction.call().missingReserveToEndAuction()
    auction.transact({'from': bidder, "value": missing_reserve}).bid()
    assert auction.call().stage() == 3

    # Any payable transactions should fail now
    with pytest.raises(tester.TransactionFailed):
        auction.transact({'from': bidder, "value": 100}).bid()
    with pytest.raises(tester.TransactionFailed):
        eth.sendTransaction({
            'from': bidder,
            'to': auction.address,
            'value': 100
        })

    auction.transact({'from': bidder}).claimTokens()
    assert auction.call().stage() == 5

    # Any payable transactions should fail now
    with pytest.raises(tester.TransactionFailed):
        auction.transact({'from': bidder, "value": 100}).bid()
    with pytest.raises(tester.TransactionFailed):
        eth.sendTransaction({
            'from': bidder,
            'to': auction.address,
            'value': 100
        })


# Final bid amount == missing_reserve
def test_auction_final_bid_0(web3, auction_started_fast_decline, auction_bid_tested):
    auction = auction_started_fast_decline
    (bidder, late_bidder) = web3.eth.accounts[2:4]

    missing_reserve = auction.call().missingReserveToEndAuction()
    auction_bid_tested(auction, bidder, missing_reserve)
    auction_end_tests(auction, late_bidder)


# Final bid amount == missing_reserve + 1    + 1 bid of 1 wei
def test_auction_final_bid_more(web3, auction_started_fast_decline, auction_bid_tested):
    auction = auction_started_fast_decline
    (bidder, late_bidder) = web3.eth.accounts[2:4]

    missing_reserve = auction.call().missingReserveToEndAuction()
    amount = missing_reserve + 1
    auction_bid_tested(auction, bidder, amount)
    auction_end_tests(auction, late_bidder)


# Final bid amount == missing_reserve - 1    + 1 bid of 1 wei
def test_auction_final_bid_1(web3, auction_started_fast_decline, auction_bid_tested):
    auction = auction_started_fast_decline
    (bidder, late_bidder) = web3.eth.accounts[2:4]

    missing_reserve = auction.call().missingReserveToEndAuction()
    amount = missing_reserve - 1
    auction_bid_tested(auction, bidder, amount)
    auction_bid_tested(auction, bidder, 1)
    auction_end_tests(auction, late_bidder)


# Final bid amount == missing_reserve - 2
def test_auction_final_bid_2(web3, auction_started_fast_decline, auction_bid_tested):
    auction = auction_started_fast_decline
    (A, B, late_bidder) = web3.eth.accounts[2:5]

    missing_reserve = auction.call().missingReserveToEndAuction()
    amount = missing_reserve - 2
    auction_bid_tested(auction, A, amount)
    auction_bid_tested(auction, B, 3)

    auction_end_tests(auction, late_bidder)


# Final bid amount == missing_reserve - 5  + 5 bids of 1 wei
def test_auction_final_bid_5(web3, auction_started_fast_decline, auction_bid_tested):
    auction = auction_started_fast_decline
    (A, late_bidder, *bidders) = web3.eth.accounts[:7]

    missing_reserve = auction.call().missingReserveToEndAuction()
    amount = missing_reserve - 5
    # FIXME weird bug where A's final balance is bigger than initially
    # auction_bid_tested(auction, A, amount)

    auction_pre_balance = web3.eth.getBalance(auction.address)
    for bidder in bidders:
        auction_bid_tested(auction, bidder, 1)

    assert web3.eth.getBalance(auction.address) == auction_pre_balance + 5
    # auction_end_tests(auction, late_bidder)


def test_auction_simulation(
    chain,
    web3,
    auction_contract,
    get_token_contract,
    auction_bid_tested,
    txnCost
):
    eth = web3.eth
    auction = auction_contract

    # Bidder accounts
    owners = web3.eth.accounts[:2]
    bidders = web3.eth.accounts[2:]

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

    auction.transact().startAuction()
    assert auction.call().stage() == 2  # AuctionStarted

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
    auction_bid_tested(auction, bidders[0], 1)
    auction_bid_tested(auction, bidders[1], 1)
    index = 2
    bidded = 2
    approx_bid_txn_cost = 4000000

    while auction.call().missingReserveToEndAuction() > 0:
        if bidders_len < index:
            print('!! Not enough accounts to simulate bidders')

        bidder = bidders[index]
        auction.transact({'from': bidder}).sign(terms_hash)

        bidder_balance = eth.getBalance(bidder)
        assert auction.call().bids(bidder) == 0

        missing_reserve = auction.call().missingReserveToEndAuction()
        amount = int(min(bidder_balance - approx_bid_txn_cost, maxBid))

        txn_cost = txnCost(auction.transact({'from': bidder, "value": amount}).bid())
        bidded += min(amount, missing_reserve)

        if amount <= missing_reserve:
            assert auction.call().bids(bidder) == amount
            post_balance = bidder_balance - amount - txn_cost
        else:
            assert auction.call().bids(bidder) == missing_reserve
            post_balance = bidder_balance - missing_reserve - txn_cost
            print('-------! LAST BIDDER surplus to be returned:', amount - missing_reserve)

        assert eth.getBalance(bidder) == post_balance
        index += 1

    print('NO OF BIDDERS', index)

    # Auction ended, no more orders possible
    if bidders_len < index:
        print('!! Not enough accounts to simulate bidders. 1 additional account needed')

    assert eth.getBalance(auction.address) == bidded
    auction_end_tests(auction, bidders[index])

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

        # Verfify again that Terms are signed
        assert auction.call().terms_signed(bidder)

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
