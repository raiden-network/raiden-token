import pytest
from ethereum import tester
import math
from web3.utils.compat import (
    Timeout,
)
from utils import (
    handle_logs,
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

    # Fail if auction has another owner
    with pytest.raises(tester.TransactionFailed):
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
    auction_post_distributed_tests):
    bidders = get_bidders(10)
    auction = auction_contract_fast_decline
    token = token_contract(auction.address)
    auction.transact({'from': owner}).setup(token.address)
    auction.transact({'from': owner}).startAuction()

    Distributor = chain.provider.get_contract_factory('Distributor')
    distributor = create_contract(Distributor, [auction.address])

    # Retrieve bidder addresses from contract bid events
    def get_bidders_addresses(event):
        address = event['args']['_sender']

        if address not in addresses:
            addresses.append(address)
            values.append(0)
            index = len(addresses) - 1
        else:
            index = addresses.index(address)

        values[index] += event['args']['_amount']

    def verify_claim(event):
        addr = event['args']['_recipient']
        sent_amount = event['args']['_sent_amount']

        # Check for double claiming
        assert addr not in verified_claim
        assert auction.call().bids(addr) == 0
        assert sent_amount == token.call().balanceOf(addr)
        verified_claim.append(address)

    for bidder in bidders:
        missing = auction.call().missingFundsToEndAuction()
        balance = web3.eth.getBalance(bidder)
        amount = min(missing, balance - 500000)
        if(amount > 0):
            print('-- BIDDING', amount, missing, balance)
            auction_bid_tested(auction, bidder, amount)

    assert auction.call().missingFundsToEndAuction() == 0
    auction.transact({'from': owner}).finalizeAuction()

    addresses = []
    values = []
    claimed = []
    verified_claim = []

    handle_logs(contract=auction, event='BidSubmission', callback=get_bidders_addresses)

    # Send 5 claiming transactions in a single batch to not run out of gas
    safe_distribution_no = 5
    steps = math.ceil(len(addresses) / safe_distribution_no)

    # Call the distributor contract with batches of bidder addresses
    for i in range(0, steps):
        start = i * safe_distribution_no
        end = (i + 1) * safe_distribution_no
        auction_claim_tokens_tested(token, auction, addresses[start:end], distributor)
        # distributor.transact({'from': owner}).distribute(addresses[start:end])

    auction_post_distributed_tests(auction)

    # Verify that a single "ClaimedTokens" event has been issued by the auction contract
    # for each address
    for j in range(0, len(addresses) - 1):
        address = addresses[j]
        assert auction.call().bids(address) == 0

        # check if auction event was triggered for this user
        handle_logs(
            contract=auction,
            event='ClaimedTokens',
            params={
                'filter': {'_recipient': address}
            },
            callback=verify_claim)


def test_waitfor_last_events_timeout():
    with Timeout(20) as timeout:
        timeout.sleep(2)
