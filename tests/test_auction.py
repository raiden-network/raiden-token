import pytest
from ethereum import tester
from functools import (
    reduce
)
from web3.utils.compat import (
    Timeout,
)
from utils import (
    elapsed_at_price,
    check_succesful_tx
)
from fixtures import (
    owner_index,
    owner,
    wallet,
    team,
    get_bidders,
    contract_params,
    create_contract,
    get_token_contract,
    token_contract,
    auction_contract,
    create_accounts,
    prepare_preallocs,
    txnCost,
    event_handler,
    auction_fast_decline_args
)

from auction_fixtures import (
    auction_setup_contract,
    auction_started_fast_decline,
    auction_ended,
    auction_bid_tested,
    auction_end_tests,
    auction_post_distributed_tests,
    auction_claim_tokens_tested,
    auction_price,
    price
)

# TODO: missingFundsToEndAuction,
# TODO: review edge cases for claimTokens, bid


def test_auction_init(
    chain,
    web3,
    owner,
    wallet,
    create_contract,
    contract_params):
    Auction = chain.provider.get_contract_factory('DutchAuction')

    with pytest.raises(TypeError):
        auction_contract = create_contract(Auction, [wallet])
    with pytest.raises(TypeError):
        auction_contract = create_contract(Auction, [wallet, 10000, -3, 2])
    with pytest.raises(TypeError):
        auction_contract = create_contract(Auction, [wallet, 10000, 3, -2])
    with pytest.raises(TypeError):
        auction_contract = create_contract(Auction, [wallet, -1, 3, 2])
    with pytest.raises(tester.TransactionFailed):
        auction_contract = create_contract(Auction, [wallet, 10000, 0, 2])
    with pytest.raises(tester.TransactionFailed):
        auction_contract = create_contract(Auction, [wallet, 0, 3, 2])

    create_contract(Auction, [wallet] + contract_params['args'], {'from': owner})


def test_auction_setup(
    web3,
    owner,
    get_bidders,
    auction_contract,
    token_contract,
    contract_params):
    auction = auction_contract
    A = get_bidders(2)[0]

    assert auction.call().stage() == 0  # AuctionDeployed

    # Test setup with a different owner token - should fail
    token = token_contract(auction.address, {'from': A})
    with pytest.raises(tester.TransactionFailed):
        auction.transact({'from': owner}).setup(token.address)

    web3.testing.mine(5)
    token = token_contract(auction.address)
    auction.transact({'from': owner}).setup(token.address)
    assert auction.call().tokens_auctioned() == token.call().balanceOf(auction.address)
    assert auction.call().multiplier() == 10**token.call().decimals()
    assert auction.call().stage() == 1

    # Token cannot be changed after setup
    with pytest.raises(tester.TransactionFailed):
        auction.call().setup(token.address)


def test_auction_change_settings(
    web3,
    owner,
    get_bidders,
    auction_contract,
    token_contract):
    auction = auction_contract
    token = token_contract(auction.address)
    A = get_bidders(2)[0]
    price_start = 2 * 10^18

    with pytest.raises(tester.TransactionFailed):
        auction.transact({'from': A}).changeSettings(price_start, 524880000, 3)
    with pytest.raises(tester.TransactionFailed):
        auction.transact({'from': owner}).changeSettings(0, 524880000, 2)
    with pytest.raises(tester.TransactionFailed):
        auction.transact({'from': owner}).changeSettings(price_start, 0, 3)
    with pytest.raises(TypeError):
        auction.transact({'from': owner}).changeSettings(price_start, 524880000, -3)
    with pytest.raises(TypeError):
        auction.transact({'from': owner}).changeSettings(price_start, -4, 3)
    with pytest.raises(TypeError):
        auction.transact({'from': owner}).changeSettings(-1, 524880000, 3)

    auction.transact({'from': owner}).changeSettings(price_start, 524880000, 3)
    assert auction.call().price_start() == price_start
    assert auction.call().price_constant() == 524880000
    assert auction.call().price_exponent() == 3

    auction.transact({'from': owner}).setup(token.address)
    auction.transact({'from': owner}).changeSettings(5000, 1, 1)
    assert auction.call().price_start() == 5000
    assert auction.call().price_constant() == 1
    assert auction.call().price_exponent() == 1

    auction.transact({'from': owner}).startAuction()
    with pytest.raises(tester.TransactionFailed):
        auction.transact({'from': owner}).changeSettings(5000, 1, 1)


def test_auction_access(
    chain,
    owner,
    web3,
    auction_contract,
    contract_params):
    auction = auction_contract
    auction_args = contract_params['args']

    assert auction.call().owner() == owner
    assert auction.call().price_start() == auction_args[0]
    assert auction.call().price_constant() == auction_args[1]
    assert auction.call().price_exponent() == auction_args[2]
    assert auction.call().start_time() == 0
    assert auction.call().end_time() == 0
    assert auction.call().start_block() == 0
    assert auction.call().funds_claimed() == 0
    assert auction.call().tokens_auctioned() == 0
    assert auction.call().received_ether() == 0
    assert auction.call().final_price() == 0
    assert auction.call().stage() == 0
    assert auction.call().token()


def test_auction_start(
    chain,
    web3,
    owner,
    get_bidders,
    auction_contract,
    token_contract,
    auction_bid_tested,
    auction_end_tests):
    auction = auction_contract
    token = token_contract(auction.address)
    (A, B) = get_bidders(2)

    # Should not be able to start auction before setup
    with pytest.raises(tester.TransactionFailed):
        auction.transact({'from': owner}).startAuction()

    auction.transact({'from': owner}).setup(token.address)
    assert auction.call().stage() == 1
    multiplier = auction.call().multiplier()

    auction.transact({'from': owner}).changeSettings(*auction_fast_decline_args)

    # Should not be able to start auction if not owner
    with pytest.raises(tester.TransactionFailed):
        auction.transact({'from': A}).startAuction()

    txn_hash = auction.transact({'from': owner}).startAuction()
    receipt = chain.wait.for_receipt(txn_hash)
    timestamp = web3.eth.getBlock(receipt['blockNumber'])['timestamp']
    assert auction.call().stage() == 2
    assert auction.call().start_time() == timestamp

    # Should not be able to call start auction after it has already started
    with pytest.raises(tester.TransactionFailed):
        auction.transact({'from': owner}).startAuction()

    amount = web3.eth.getBalance(A) - 10000000
    missing_funds = auction.call().missingFundsToEndAuction()

    # Fails if amount is > missing_funds
    if(missing_funds < amount):
        with pytest.raises(tester.TransactionFailed):
            auction_bid_tested(auction, A, amount)

    missing_funds = auction.call().missingFundsToEndAuction()
    auction_bid_tested(auction, A, missing_funds)

    # Finalize auction
    assert auction.call().missingFundsToEndAuction() == 0
    auction.transact({'from': owner}).finalizeAuction()
    auction_end_tests(auction, B)

    with pytest.raises(tester.TransactionFailed):
        auction.transact({'from': owner}).startAuction()


# Test price function at the different auction stages
def test_price(
    web3,
    owner,
    wallet,
    auction_contract,
    token_contract,
    auction_bid_tested,
    auction_end_tests,
    price):
    auction = auction_contract
    token = token_contract(auction.address)
    (A, B) = web3.eth.accounts[2:4]

    # Auction price after deployment; multiplier is 0 at this point
    assert auction.call().price() == auction.call().price_start()

    auction.transact({'from': owner}).setup(token.address)
    multiplier = auction.call().multiplier()

    # Auction price before auction start
    price_start = auction.call().price_start()
    price_constant = auction.call().price_constant()
    assert auction.call().price() == price_start

    auction.transact({'from': owner}).startAuction()
    start_time = auction.call().start_time()

    elapsed = 33
    web3.testing.timeTravel(start_time + elapsed)
    new_price = price(elapsed)
    assert new_price == auction.call().price()

    missing_funds = auction.call().missingFundsToEndAuction()
    auction_bid_tested(auction, A, missing_funds)

    auction.transact({'from': owner}).finalizeAuction()
    auction_end_tests(auction, B)

    # Calculate final price
    received_ether = auction.call().received_ether()
    tokens_auctioned = auction.call().tokens_auctioned()
    final_price = received_ether // (tokens_auctioned // multiplier)

    assert auction.call().price() == 0
    assert auction.call().final_price() == final_price


# Test sending ETH to the auction contract
def test_auction_bid(
    chain,
    web3,
    owner,
    auction_contract,
    token_contract,
    contract_params,
    txnCost,
    auction_end_tests,
    auction_claim_tokens_tested):
    eth = web3.eth
    auction = auction_contract

    bidders_index = 2 + len(contract_params['preallocations'])
    (A, B) = web3.eth.accounts[bidders_index:(bidders_index + 2)]

    # Initialize token
    token = token_contract(auction.address)

    # Try sending funds before auction starts
    with pytest.raises(tester.TransactionFailed):
        eth.sendTransaction({
            'from': A,
            'to': auction.address,
            'value': 100
        })

    with pytest.raises(tester.TransactionFailed):
        auction.transact({'from': A, "value": 100}).bid()

    auction.transact({'from': owner}).setup(token.address)
    multiplier = auction.call().multiplier()

    # Higher price decline
    auction.transact({'from': owner}).changeSettings(*auction_fast_decline_args)
    auction.transact({'from': owner}).startAuction()

    # End auction by bidding the needed amount
    missing_funds = auction.call().missingFundsToEndAuction()

    # Test fallback function
    # 76116 gas cost
    txn_hash = eth.sendTransaction({
        'from': A,
        'to': auction.address,
        'value': 100
    })
    receipt = check_succesful_tx(web3, txn_hash)
    print('--- FALLBACK', receipt)

    assert auction.call().received_ether() == 100
    assert auction.call().bids(A) == 100

    missing_funds = auction.call().missingFundsToEndAuction()

    # 46528 gas cost
    txn_hash = auction.transact({'from': A, "value": missing_funds}).bid()
    receipt = check_succesful_tx(web3, txn_hash)
    print('--- BID', receipt)
    assert auction.call().received_ether() == missing_funds + 100
    assert auction.call().bids(A) == missing_funds + 100

    auction.transact({'from': owner}).finalizeAuction()
    auction_end_tests(auction, B)

    # Any payable transactions should fail now
    with pytest.raises(tester.TransactionFailed):
        auction.transact({'from': A, "value": 1}).bid()
    with pytest.raises(tester.TransactionFailed):
        eth.sendTransaction({
            'from': A,
            'to': auction.address,
            'value': 1
        })

    auction_claim_tokens_tested(token, auction, A)

    assert auction.call().stage() == 4  # TokensDistributed

    # Any payable transactions should fail now
    with pytest.raises(tester.TransactionFailed):
        auction.transact({'from': A, "value": 100}).bid()
    with pytest.raises(tester.TransactionFailed):
        eth.sendTransaction({
            'from': A,
            'to': auction.address,
            'value': 100
        })


# Final bid amount == missing_funds
def test_auction_final_bid_0(
    web3,
    owner,
    contract_params,
    auction_started_fast_decline,
    auction_bid_tested,
    auction_end_tests
):
    auction = auction_started_fast_decline
    bidders_index = 2 + len(contract_params['preallocations'])
    (bidder, late_bidder) = web3.eth.accounts[bidders_index:(bidders_index + 2)]

    missing_funds = auction.call().missingFundsToEndAuction()
    auction_bid_tested(auction, bidder, missing_funds)
    auction.transact({'from': owner}).finalizeAuction()
    auction_end_tests(auction, late_bidder)


# Final bid amount == missing_funds + 1    + 1 bid of 1 wei
def test_auction_final_bid_more(
    web3,
    contract_params,
    auction_started_fast_decline,
    auction_bid_tested,
    auction_end_tests
):
    auction = auction_started_fast_decline
    bidders_index = 2 + len(contract_params['preallocations'])
    (bidder, late_bidder) = web3.eth.accounts[bidders_index:(bidders_index + 2)]

    missing_funds = auction.call().missingFundsToEndAuction()
    amount = missing_funds + 1
    with pytest.raises(tester.TransactionFailed):
        web3.eth.sendTransaction({
            'from': bidder,
            'to': auction.address,
            'value': amount
        })
    with pytest.raises(tester.TransactionFailed):
        auction_bid_tested(auction, bidder, amount)


# Final bid amount == missing_funds - 1    + 1 bid of 1 wei
def test_auction_final_bid_1(
    web3,
    owner,
    contract_params,
    auction_started_fast_decline,
    auction_bid_tested,
    auction_end_tests
):
    auction = auction_started_fast_decline
    bidders_index = 2 + len(contract_params['preallocations'])
    (bidder, late_bidder) = web3.eth.accounts[bidders_index:(bidders_index + 2)]

    missing_funds = auction.call().missingFundsToEndAuction()
    amount = missing_funds - 1
    auction_bid_tested(auction, bidder, amount)

    # Some parameters decrease the price very fast
    missing_funds = auction.call().missingFundsToEndAuction()
    if missing_funds > 0:
        auction_bid_tested(auction, bidder, 1)

    auction.transact({'from': owner}).finalizeAuction()
    auction_end_tests(auction, late_bidder)


# Final bid amount == missing_funds - 2
def test_auction_final_bid_2(
    web3,
    owner,
    contract_params,
    auction_started_fast_decline,
    auction_bid_tested,
    auction_end_tests
):
    auction = auction_started_fast_decline
    bidders_index = 2 + len(contract_params['preallocations'])
    (A, B, late_bidder) = web3.eth.accounts[bidders_index:(bidders_index + 3)]


    missing_funds = auction.call().missingFundsToEndAuction()
    amount = missing_funds - 2
    auction_bid_tested(auction, A, amount)

    with pytest.raises(tester.TransactionFailed):
        auction_bid_tested(auction, B, 3)

    # Some parameters decrease the price very fast
    missing_funds = auction.call().missingFundsToEndAuction()
    if missing_funds > 0:
        auction_bid_tested(auction, B, missing_funds)

    auction.transact({'from': owner}).finalizeAuction()
    auction_end_tests(auction, late_bidder)


# Final bid amount == missing_funds - 5  + 5 bids of 1 wei
def test_auction_final_bid_5(
    web3,
    owner,
    contract_params,
    auction_started_fast_decline,
    auction_bid_tested,
    auction_end_tests,
    create_accounts
):
    auction = auction_started_fast_decline
    bidders_index = 2 + len(contract_params['preallocations'])
    needed_bidders = 7
    extant_accounts = len(web3.eth.accounts) - bidders_index
    create_accounts(needed_bidders - extant_accounts)

    (A, late_bidder, *bidders) = web3.eth.accounts[bidders_index:(bidders_index + 8)]

    missing_funds = auction.call().missingFundsToEndAuction()
    amount = missing_funds - 5
    auction_bid_tested(auction, A, amount)

    pre_received_ether = auction.call().received_ether()
    bidded = 0
    for bidder in bidders:
        # Some parameters decrease the price very fast
        missing_funds = auction.call().missingFundsToEndAuction()
        if missing_funds > 0:
            auction_bid_tested(auction, bidder, 1)
            bidded += 1
        else:
            break

    assert auction.call().received_ether() == pre_received_ether + bidded

    auction.transact({'from': owner}).finalizeAuction()
    auction_end_tests(auction, late_bidder)


def test_auction_simulation(
    chain,
    web3,
    owner,
    team,
    get_bidders,
    auction_contract,
    token_contract,
    contract_params,
    auction_bid_tested,
    auction_end_tests,
    auction_post_distributed_tests,
    auction_claim_tokens_tested,
    create_accounts,
    txnCost
):
    eth = web3.eth
    auction = auction_contract
    bidders = get_bidders(12)

    # Initialize token
    token = token_contract(auction.address)

    # Initial Auction state
    assert auction.call().stage() == 0  # AuctionDeployed
    assert eth.getBalance(auction.address) == 0
    assert auction.call().received_ether() == 0

    # Auction setup without being the owner should fail
    with pytest.raises(tester.TransactionFailed):
        auction.transact({'from': bidders[1]}).setup(token.address)

    auction.transact({'from': owner}).setup(token.address)
    assert auction.call().stage() == 1  # AuctionSetUp

    multiplier = auction.call().multiplier()
    prealloc = prepare_preallocs(multiplier, contract_params['preallocations'])

    # We want to revert to these, because we set them in the fixtures
    initial_args = [
        auction.call().price_start(),
        auction.call().price_constant(),
        auction.call().price_exponent()
    ]

    # Make sure we can change auction settings now
    auction.transact({'from': owner}).changeSettings(1000, 556, 322)

    # changeSettings without being the owner should fail
    with pytest.raises(tester.TransactionFailed):
        auction.transact({'from': bidders[1]}).changeSettings(1000, 556, 322)

    # Change settings back to the fixtures settings
    auction.transact({'from': owner}).changeSettings(*initial_args)

    # startAuction without being the owner should fail
    with pytest.raises(tester.TransactionFailed):
        auction.transact({'from': bidders[1]}).startAuction()

    auction.transact({'from': owner}).startAuction()
    assert auction.call().stage() == 2  # AuctionStarted

    # Cannot changeSettings after auction starts
    with pytest.raises(tester.TransactionFailed):
        auction.transact({'from': owner}).changeSettings(1000, 556, 322)

    # transferFundsToToken should fail (private)
    with pytest.raises(ValueError):
        auction.transact({'from': bidders[1]}).transferFundsToToken()

    # finalizeAuction should fail (missing funds not 0)
    with pytest.raises(tester.TransactionFailed):
        auction.transact({'from': bidders[1]}).finalizeAuction()
    with pytest.raises(tester.TransactionFailed):
        auction.transact({'from': owner}).finalizeAuction()

    # Set maximum amount for a bid - we don't want 1 account draining the auction
    missing_funds = auction.call().missingFundsToEndAuction()
    maxBid = missing_funds / 4

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

    while auction.call().missingFundsToEndAuction() > 0:
        if bidders_len < index:
            new_account = create_accounts(1)[0]
            bidders.append(new_account)
            bidders_len += 1
            print('Creating 1 additional bidder account', new_account)

        bidder = bidders[index]

        bidder_balance = eth.getBalance(bidder)
        assert auction.call().bids(bidder) == 0

        missing_funds = auction.call().missingFundsToEndAuction()
        amount = int(min(bidder_balance - approx_bid_txn_cost, maxBid))

        if amount <= missing_funds:
            txn_cost = txnCost(auction.transact({'from': bidder, "value": amount}).bid())
        else:
            # Fail if we bid more than missing_funds
            with pytest.raises(tester.TransactionFailed):
                txn_cost = txnCost(auction.transact({'from': bidder, "value": amount}).bid())

            # Bid exactly the amount needed in order to end the auction
            amount = missing_funds
            txn_cost = txnCost(auction.transact({'from': bidder, "value": amount}).bid())

        assert auction.call().bids(bidder) == amount
        post_balance = bidder_balance - amount - txn_cost
        bidded += min(amount, missing_funds)

        assert eth.getBalance(bidder) == post_balance
        index += 1

    print('NO OF BIDDERS', index)

    # Auction ended, no more orders possible
    if bidders_len < index:
        print('!! Not enough accounts to simulate bidders. 1 additional account needed')

    # Finalize Auction
    auction.transact({'from': owner}).finalizeAuction()

    with pytest.raises(tester.TransactionFailed):
        auction.transact({'from': owner}).finalizeAuction()

    assert auction.call().received_ether() == bidded
    auction_end_tests(auction, bidders[index])

    # Claim all tokens
    # Final price per TKN (Tei * multiplier)
    final_price = auction.call().final_price()

    funds_at_price = auction.call().tokens_auctioned() * final_price // multiplier
    received_ether = auction.call().received_ether()
    assert received_ether == funds_at_price

    # Total Tei claimable
    total_tokens_claimable = auction.call().received_ether() * multiplier // final_price
    print('FINAL PRICE', final_price)
    print('TOTAL TOKENS CLAIMABLE', int(total_tokens_claimable))
    assert int(total_tokens_claimable) == auction.call().tokens_auctioned()

    rounding_error_tokens = 0

    for i in range(0, index):
        bidder = bidders[i]

        auction_claim_tokens_tested(token, auction, bidder)

        # If auction funds not transferred to owner (last claimTokens)
        # we test for a correct claimed tokens calculation
        balance_auction = auction.call().received_ether()
        if balance_auction > 0:

            # Auction supply = unclaimed tokens, including rounding errors
            unclaimed_token_supply = token.call().balanceOf(auction.address)

            # Calculated unclaimed tokens
            unclaimed_funds = balance_auction - auction.call().funds_claimed()
            unclaimed_tokens = multiplier * unclaimed_funds // auction.call().final_price()

            # Adding previous rounding errors
            unclaimed_tokens += rounding_error_tokens

            # Token's auction balance should be the same as
            # the unclaimed tokens calculation based on the final_price
            # We assume a rounding error of 1
            if unclaimed_token_supply != unclaimed_tokens:
                rounding_error_tokens += 1
                unclaimed_tokens += 1
            assert unclaimed_token_supply == unclaimed_tokens


    # Check if all the auction tokens have been claimed
    total_tokens = auction.call().tokens_auctioned() + reduce((lambda x, y: x + y), prealloc)
    assert token.call().totalSupply() == total_tokens

    # Auction balance might be > 0 due to rounding errors
    assert token.call().balanceOf(auction.address) == rounding_error_tokens
    print('FINAL UNCLAIMED TOKENS', rounding_error_tokens)

    auction_post_distributed_tests(auction)


def test_waitfor_last_events_timeout():
    with Timeout(20) as timeout:
        timeout.sleep(2)
