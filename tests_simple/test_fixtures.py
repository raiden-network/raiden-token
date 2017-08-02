import pytest
from functools import (
    reduce
)

# multiplier based on token decimals: 10^decimals
multiplier = 10**18
initial_supply = 10000000 * multiplier
prealloc = [
    200000 * multiplier,
    800000 * multiplier
]
auction_supply = initial_supply - reduce((lambda x, y: x + y), prealloc)

# price_factor, _price_const
auction_args = [
    [2, 7500],
    [3, 7500]
]


@pytest.fixture()
def auction_contract(chain, create_contract):
    Auction = chain.provider.get_contract_factory('DutchAuction')
    auction_contract = create_contract(Auction, auction_args[0])

    print_logs(auction_contract, 'Deployed', 'DutchAuction')
    print_logs(auction_contract, 'Setup', 'DutchAuction')
    print_logs(auction_contract, 'SettingsChanged', 'DutchAuction')
    print_logs(auction_contract, 'AuctionStarted', 'DutchAuction')
    print_logs(auction_contract, 'BidSubmission', 'DutchAuction')
    print_logs(auction_contract, 'AuctionEnded', 'DutchAuction')
    print_logs(auction_contract, 'ClaimedTokens', 'DutchAuction')
    print_logs(auction_contract, 'TokensDistributed', 'DutchAuction')
    print_logs(auction_contract, 'TradingStarted', 'DutchAuction')

    return auction_contract


@pytest.fixture()
def get_token_contract(chain, create_contract):
    # contract can be auction contract or proxy contract
    def get(arguments, transaction=None):
        ReserveToken = chain.provider.get_contract_factory('ReserveToken')
        token_contract = create_contract(ReserveToken, arguments, transaction)

        print_logs(token_contract, 'Redeemed', 'ReserveToken')
        print_logs(token_contract, 'Transfer', 'ReserveToken')
        print_logs(token_contract, 'ReceivedReserve', 'ReserveToken')

        return token_contract
    return get


@pytest.fixture()
def token_contract(chain, web3, get_token_contract):
    def get(auction_address, transaction=None):
        owners = web3.eth.accounts[:2]
        token_contract = get_token_contract([
            auction_address,
            initial_supply,
            owners,
            prealloc
        ], transaction)

        return token_contract
    return get


@pytest.fixture
def accounts(web3):
    def get(num):
        return [web3.eth.accounts[i] for i in range(num)]
    return get


@pytest.fixture
def txnCost(chain, web3):
    def get(txn_hash):
        receipt = chain.wait.for_receipt(txn_hash)
        txn_cost = receipt['gasUsed'] * web3.eth.gasPrice
        return txn_cost
    return get


@pytest.fixture
def create_contract(chain):
    def get(contract_type, arguments, transaction=None):
        deploy_txn_hash = contract_type.deploy(transaction=transaction, args=arguments)
        contract_address = chain.wait.for_contract_address(deploy_txn_hash)
        contract = contract_type(address=contract_address)
        return contract
    return get


def print_logs(contract, event, name=''):
    transfer_filter_past = contract.pastEvents(event)
    past_events = transfer_filter_past.get()
    if len(past_events):
        print('--(', name, ') past events for ', event, past_events)

    transfer_filter = contract.on(event)
    events = transfer_filter.get()
    if len(events):
        print('--(', name, ') events for ', event, events)

    transfer_filter.watch(lambda x: print('--(', name, ') event ', event, x['args']))


# Almost equal
def xassert(a, b, threshold=0.0001):
    if min(a, b) > 0:
        assert abs(a - b) / min(a, b) <= threshold, (a, b)
    assert abs(a - b) <= threshold, (a, b)
    return True
