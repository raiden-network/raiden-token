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
    wallet_address,
    get_bidders,
    gnosis_multisig_wallet,
    contract_params,
    create_contract,
    get_token_contract,
    token_contract,
    auction_contract,
    auction_contract_fast_decline,
    create_accounts,
    txnCost,
    event_handler
)

from auction_fixtures import (
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
    wallet_address,
    create_contract,
    contract_params):
    Auction = chain.provider.get_contract_factory('DutchAuction')

    with pytest.raises(TypeError):
        auction_contract = create_contract(Auction, [wallet_address])
    with pytest.raises(TypeError):
        auction_contract = create_contract(Auction, [wallet_address, 10000, -3, 2])
    with pytest.raises(TypeError):
        auction_contract = create_contract(Auction, [wallet_address, 10000, 3, -2])
    with pytest.raises(TypeError):
        auction_contract = create_contract(Auction, [wallet_address, -1, 3, 2])
    with pytest.raises(tester.TransactionFailed):
        auction_contract = create_contract(Auction, [wallet_address, 10000, 0, 2])
    with pytest.raises(tester.TransactionFailed):
        auction_contract = create_contract(Auction, [wallet_address, 0, 3, 2])

    create_contract(Auction, [wallet_address] + contract_params['args'], {'from': owner})


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

    # changeSettings is a private method
    with pytest.raises(ValueError):
        auction.transact({'from': owner}).changeSettings(1000, 556, 322)

    web3.testing.mine(5)
    token = token_contract(auction.address)
    auction.transact({'from': owner}).setup(token.address)
    assert auction.call().num_tokens_auctioned() == token.call().balanceOf(auction.address)
    assert auction.call().token_multiplier() == 10**token.call().decimals()
    assert auction.call().stage() == 1

    # Token cannot be changed after setup
    with pytest.raises(tester.TransactionFailed):
        auction.call().setup(token.address)


def test_auction_access(
    chain,
    owner,
    web3,
    auction_contract,
    contract_params):
    auction = auction_contract
    auction_args = contract_params['args']

    assert auction.call().owner_address() == owner
    assert auction.call().price_start() == auction_args[0]
    assert auction.call().price_constant() == auction_args[1]
    assert auction.call().price_exponent() == auction_args[2]
    assert auction.call().start_time() == 0
    assert auction.call().end_time() == 0
    assert auction.call().start_block() == 0
    assert auction.call().funds_claimed() == 0
    assert auction.call().num_tokens_auctioned() == 0
    assert auction.call().received_wei() == 0
    assert auction.call().final_price() == 0
    assert auction.call().stage() == 0
    assert auction.call().token()


def test_auction_start(
    chain,
    web3,
    owner,
    get_bidders,
    auction_contract_fast_decline,
    token_contract,
    auction_bid_tested,
    auction_end_tests):
    auction = auction_contract_fast_decline
    token = token_contract(auction.address)
    (A, B) = get_bidders(2)

    # Should not be able to start auction before setup
    with pytest.raises(tester.TransactionFailed):
        auction.transact({'from': owner}).startAuction()

    auction.transact({'from': owner}).setup(token.address)
    assert auction.call().stage() == 1
    token_multiplier = auction.call().token_multiplier()

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
    wallet_address,
    auction_contract,
    token_contract,
    auction_bid_tested,
    auction_end_tests,
    price):
    auction = auction_contract
    token = token_contract(auction.address)
    (A, B) = web3.eth.accounts[2:4]

    # Auction price after deployment; token_multiplier is 0 at this point
    assert auction.call().price() == auction.call().price_start()

    auction.transact({'from': owner}).setup(token.address)
    token_multiplier = auction.call().token_multiplier()

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
    received_wei = auction.call().received_wei()
    num_tokens_auctioned = auction.call().num_tokens_auctioned()
    final_price = received_wei // (num_tokens_auctioned // token_multiplier)

    assert auction.call().price() == 0
    assert auction.call().final_price() == final_price


# Test sending ETH to the auction contract
def test_auction_bid(
    chain,
    web3,
    owner,
    wallet_address,
    get_bidders,
    auction_contract_fast_decline,
    token_contract,
    contract_params,
    txnCost,
    auction_end_tests,
    auction_claim_tokens_tested):
    eth = web3.eth
    auction = auction_contract_fast_decline
    (A, B) = get_bidders(2)

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
    token_multiplier = auction.call().token_multiplier()

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

    assert auction.call().received_wei() == 100
    assert auction.call().bids(A) == 100

    missing_funds = auction.call().missingFundsToEndAuction()

    # 46528 gas cost
    txn_hash = auction.transact({'from': A, "value": missing_funds}).bid()
    receipt = check_succesful_tx(web3, txn_hash)

    assert auction.call().received_wei() == missing_funds + 100
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


def test_auction_bid_from_multisig(
    web3,
    owner,
    wallet_address,
    gnosis_multisig_wallet,
    get_bidders,
    auction_contract_fast_decline,
    token_contract,
    event_handler):
    eth = web3.eth
    auction = auction_contract_fast_decline
    (A, B, C) = get_bidders(3)

    # Initialize token
    token = token_contract(auction.address)
    auction.transact({'from': owner}).setup(token.address)
    auction.transact({'from': owner}).startAuction()

    gnosis_wallet1 = gnosis_multisig_wallet([A, B, C], 1)
    gnosis_wallet2 = gnosis_multisig_wallet([A, B, C], 2)

    web3.eth.sendTransaction({
        'from': B,
        'to': gnosis_wallet1.address,
        'value': 100000
    })
    web3.eth.sendTransaction({
        'from': B,
        'to': gnosis_wallet2.address,
        'value': 200000
    })

    pre_balance_wallet = web3.eth.getBalance(wallet_address)

    # Test gnosis wallet with 2 owners and 1 confirmation
    gnosis_wallet1.transact({'from': A}).submitTransaction(auction.address, 1000, bytearray())
    assert web3.eth.getBalance(gnosis_wallet1.address) == 100000 - 1000
    assert auction.call().bids(gnosis_wallet1.address) == 1000
    assert web3.eth.getBalance(wallet_address) == pre_balance_wallet + 1000

    transactionId = None
    def setId(event):
        nonlocal transactionId
        transactionId = event['args']['transactionId']

    # Test gnosis wallet with 3 owners and 2 confirmations
    pre_balance_wallet = web3.eth.getBalance(wallet_address)
    txhash = gnosis_wallet2.transact({'from': A}).submitTransaction(auction.address, 3000, bytearray())
    assert web3.eth.getBalance(gnosis_wallet2.address) == 200000
    assert auction.call().bids(gnosis_wallet2.address) == 0
    assert web3.eth.getBalance(wallet_address) == pre_balance_wallet

    # Wait for transactionId from the Confirmation event
    ev_handler = event_handler(gnosis_wallet2)
    ev_handler.add(txhash, 'Confirmation', setId)
    ev_handler.check()

    # Second owner confirms the transaction
    gnosis_wallet2.transact({'from': B}).confirmTransaction(transactionId)
    assert web3.eth.getBalance(gnosis_wallet2.address) == 200000 - 3000
    assert auction.call().bids(gnosis_wallet2.address) == 3000
    assert web3.eth.getBalance(wallet_address) == pre_balance_wallet + 3000


# Final bid amount == missing_funds
def test_auction_final_bid_0(
    web3,
    owner,
    get_bidders,
    contract_params,
    token_contract,
    auction_contract_fast_decline,
    auction_bid_tested,
    auction_end_tests
):
    auction = auction_contract_fast_decline
    token = token_contract(auction.address)
    auction.transact({'from': owner}).setup(token.address)
    auction.transact({'from': owner}).startAuction()

    (bidder, late_bidder) = get_bidders(2)

    missing_funds = auction.call().missingFundsToEndAuction()
    auction_bid_tested(auction, bidder, missing_funds)
    auction.transact({'from': owner}).finalizeAuction()
    auction_end_tests(auction, late_bidder)


# Final bid amount == missing_funds + 1    + 1 bid of 1 wei
def test_auction_final_bid_more(
    web3,
    owner,
    get_bidders,
    contract_params,
    token_contract,
    auction_contract_fast_decline,
    auction_bid_tested,
    auction_end_tests
):
    auction = auction_contract_fast_decline
    token = token_contract(auction.address)
    auction.transact({'from': owner}).setup(token.address)
    auction.transact({'from': owner}).startAuction()

    (bidder, late_bidder) = get_bidders(2)

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
    get_bidders,
    contract_params,
    token_contract,
    auction_contract_fast_decline,
    auction_bid_tested,
    auction_end_tests
):
    auction = auction_contract_fast_decline
    token = token_contract(auction.address)
    auction.transact({'from': owner}).setup(token.address)
    auction.transact({'from': owner}).startAuction()

    (bidder, late_bidder) = get_bidders(2)

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
    get_bidders,
    contract_params,
    token_contract,
    auction_contract_fast_decline,
    auction_bid_tested,
    auction_end_tests
):
    auction = auction_contract_fast_decline
    token = token_contract(auction.address)
    auction.transact({'from': owner}).setup(token.address)
    auction.transact({'from': owner}).startAuction()

    (A, B, late_bidder) = get_bidders(3)

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
    get_bidders,
    contract_params,
    token_contract,
    auction_contract_fast_decline,
    auction_bid_tested,
    auction_end_tests,
    create_accounts
):
    auction = auction_contract_fast_decline
    token = token_contract(auction.address)
    auction.transact({'from': owner}).setup(token.address)
    auction.transact({'from': owner}).startAuction()

    (A, late_bidder, *bidders) = get_bidders(7)

    missing_funds = auction.call().missingFundsToEndAuction()
    amount = missing_funds - 5
    auction_bid_tested(auction, A, amount)

    pre_received_wei = auction.call().received_wei()
    bidded = 0
    for bidder in bidders:
        # Some parameters decrease the price very fast
        missing_funds = auction.call().missingFundsToEndAuction()
        if missing_funds > 0:
            auction_bid_tested(auction, bidder, 1)
            bidded += 1
        else:
            break

    assert auction.call().received_wei() == pre_received_wei + bidded

    auction.transact({'from': owner}).finalizeAuction()
    auction_end_tests(auction, late_bidder)


def test_auction_simulation(
    chain,
    web3,
    owner,
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
    assert auction.call().received_wei() == 0

    # Auction setup without being the owner should fail
    with pytest.raises(tester.TransactionFailed):
        auction.transact({'from': bidders[1]}).setup(token.address)

    auction.transact({'from': owner}).setup(token.address)
    assert auction.call().stage() == 1  # AuctionSetUp

    token_multiplier = auction.call().token_multiplier()

    # We want to revert to these, because we set them in the fixtures
    initial_args = [
        auction.call().price_start(),
        auction.call().price_constant(),
        auction.call().price_exponent()
    ]

    # changeSettings is a private method
    with pytest.raises(ValueError):
        auction.transact({'from': owner}).changeSettings(1000, 556, 322)

    # startAuction without being the owner should fail
    with pytest.raises(tester.TransactionFailed):
        auction.transact({'from': bidders[1]}).startAuction()

    auction.transact({'from': owner}).startAuction()
    assert auction.call().stage() == 2  # AuctionStarted

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

    assert auction.call().received_wei() == bidded
    auction_end_tests(auction, bidders[index])

    # Claim all tokens
    # Final price per TKN (Tei * token_multiplier)
    final_price = auction.call().final_price()

    funds_at_price = auction.call().num_tokens_auctioned() * final_price // token_multiplier
    received_wei = auction.call().received_wei()
    assert received_wei == funds_at_price

    # Total Tei claimable
    total_tokens_claimable = auction.call().received_wei() * token_multiplier // final_price
    print('FINAL PRICE', final_price)
    print('TOTAL TOKENS CLAIMABLE', int(total_tokens_claimable))
    assert int(total_tokens_claimable) == auction.call().num_tokens_auctioned()

    rounding_error_tokens = 0

    for i in range(0, index):
        bidder = bidders[i]

        auction_claim_tokens_tested(token, auction, bidder)

        # If auction funds not transferred to owner (last claimTokens)
        # we test for a correct claimed tokens calculation
        balance_auction = auction.call().received_wei()
        if balance_auction > 0:

            # Auction supply = unclaimed tokens, including rounding errors
            unclaimed_token_supply = token.call().balanceOf(auction.address)

            # Calculated unclaimed tokens
            unclaimed_funds = balance_auction - auction.call().funds_claimed()
            unclaimed_tokens = token_multiplier * unclaimed_funds // auction.call().final_price()

            # Adding previous rounding errors
            unclaimed_tokens += rounding_error_tokens

            # Token's auction balance should be the same as
            # the unclaimed tokens calculation based on the final_price
            # We assume a rounding error of 1
            if unclaimed_token_supply != unclaimed_tokens:
                rounding_error_tokens += 1
                unclaimed_tokens += 1
            assert unclaimed_token_supply == unclaimed_tokens

    # Auction balance might be > 0 due to rounding errors
    assert token.call().balanceOf(auction.address) == rounding_error_tokens
    print('FINAL UNCLAIMED TOKENS', rounding_error_tokens)

    auction_post_distributed_tests(auction)


def test_waitfor_last_events_timeout():
    with Timeout(20) as timeout:
        timeout.sleep(2)
