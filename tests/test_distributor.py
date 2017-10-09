import pytest
from ethereum import tester
import math
from web3.utils.compat import (
    Timeout,
)
from fixtures import (
    owner_index,
    owner,
    wallet_address,
    get_bidders,
    contract_params,
    create_contract,
    auction_contract,
    auction_contract_fast_decline,
    get_token_contract,
    token_contract,
    distributor_contract,
    create_accounts,
    print_logs,
    txnCost,
    event_handler,
    fake_address
)

from auction_fixtures import (
    auction_setup_contract,
    auction_ended,
    auction_bid_tested,
    auction_end_tests,
    auction_claim_tokens_tested,
    auction_post_distributed_tests,
)

from populus.utils.wait import wait_for_transaction_receipt
from utils import ClaimsCollector


def test_distributor_init(
    chain,
    web3,
    wallet_address,
    owner,
    get_bidders,
    create_contract,
    contract_params):
    A = get_bidders(1)[0]
    Distributor = chain.provider.get_contract_factory('Distributor')
    Auction = chain.provider.get_contract_factory('DutchAuction')
    auction = create_contract(Auction, [wallet_address] + contract_params['args'], {'from': owner})

    other_auction_params = [wallet_address] + contract_params['args']
    other_owner_auction = create_contract(Auction, other_auction_params, {'from': A})
    other_contract_type = create_contract(Distributor, [auction.address])

    assert owner != A

    # Fail if no auction address is provided
    with pytest.raises(TypeError):
        create_contract(Distributor, [])

    # Fail if non address-type auction address is provided
    with pytest.raises(TypeError):
        create_contract(Distributor, [fake_address])
    with pytest.raises(TypeError):
        create_contract(Distributor, [0x0])

    # Distributor contract can have any owner
    create_contract(Distributor, [other_owner_auction.address])

    distributor_contract = create_contract(Distributor, [auction.address])


def test_distributor_distribute(
    chain,
    web3,
    wallet_address,
    owner,
    get_bidders,
    create_contract,
    token_contract,
    auction_contract_fast_decline,
    auction_bid_tested,
    auction_claim_tokens_tested,
    auction_post_distributed_tests,
    event_handler):
    bidders = get_bidders(10)
    auction = auction_contract_fast_decline
    token = token_contract(auction.address)
    ev_handler = event_handler(auction)

    auction.transact({'from': owner}).setup(token.address)
    auction.transact({'from': owner}).startAuction()

    Distributor = chain.provider.get_contract_factory('Distributor')
    distributor = create_contract(Distributor, [auction.address])

    collector = ClaimsCollector(auction, token)
    bidders_number = 0

    # Simulate some bids and collect the addresses from the events
    for bidder in bidders[:-1]:
        missing = auction.call().missingFundsToEndAuction()
        balance = web3.eth.getBalance(bidder)
        cap = (balance - 500000) // 1000000000000000000
        amount = min(missing, cap)
        # print('-- BIDDING', bidder, amount, missing, balance, cap)
        if(amount > 0):
            tx_hash = auction_bid_tested(auction, bidder, amount)
            ev_handler.add(tx_hash, 'BidSubmission', collector.add)
            ev_handler.check()
            bidders_number += 1

    missing = auction.call().missingFundsToEndAuction()
    if missing > 0:
        tx_hash = auction_bid_tested(auction, bidders[-1], missing)
        ev_handler.add(tx_hash, 'BidSubmission', collector.add)
        ev_handler.check()
        bidders_number += 1

    assert auction.call().missingFundsToEndAuction() == 0
    auction.transact({'from': owner}).finalizeAuction()

    assert len(collector.addresses) == bidders_number

    end_time = auction.call().end_time()
    elapsed = auction.call().token_claim_waiting_period()
    claim_ok_timestamp = end_time + elapsed+1

    if claim_ok_timestamp > web3.eth.getBlock('latest')['timestamp']:
        # We cannot claim tokens before waiting period has passed
        with pytest.raises(tester.TransactionFailed):
            distributor.transact({'from': owner}).distribute(collector.addresses[0:2])

        # Simulate time travel
        web3.testing.timeTravel(claim_ok_timestamp)

    # Send 5 claiming transactions in a single batch to not run out of gas
    safe_distribution_no = 5
    steps = math.ceil(len(collector.addresses) / safe_distribution_no)

    # Call the distributor contract with batches of bidder addresses
    for i in range(0, steps):
        start = i * safe_distribution_no
        end = (i + 1) * safe_distribution_no
        tx_hash = auction_claim_tokens_tested(token, auction, collector.addresses[start:end], distributor)
        ev_handler.add(tx_hash, 'ClaimedTokens', collector.verify)
        ev_handler.check()
        # distributor.transact({'from': owner}).distribute(collector.addresses[start:end])

    auction_post_distributed_tests(auction)


def test_waitfor_last_events_timeout():
    with Timeout(20) as timeout:
        timeout.sleep(2)
