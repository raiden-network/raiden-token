import pytest

# price_factor, _price_const, _owner_fr, _owner_fr_dec
auction_args = [
    [2, 7500, 10, 2],
    [3, 7500, 555, 3]
]

# auction order values for accounts; to be corelated with the above
accounts_orders = [
    (10 * 10**18, ),
    (15 * 10**18, ),
    (25 * 10**18, ),
    (60 * 10**18, ),
]

xassert_threshold_price = 10**9


@pytest.fixture()
def auction_contract(chain):
    Auction = chain.provider.get_contract_factory('DutchAuction')
    auction_contract = create_contract(chain, Auction, auction_args[0])

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
def get_token_contract(chain):
    # contract can be auction contract or proxy contract
    def get(arguments):
        ReserveToken = chain.provider.get_contract_factory('ReserveToken')
        token_contract = create_contract(chain, ReserveToken, arguments)

        print_logs(token_contract, 'Redeemed', 'ReserveToken')
        print_logs(token_contract, 'Transfer', 'ReserveToken')
        print_logs(token_contract, 'ReceivedReserve', 'ReserveToken')

        return token_contract
    return get


@pytest.fixture()
def token_contract(chain, get_token_contract):
    def get(owners, prealloc, auction):
        token_contract = get_token_contract([
            auction.address,
            owners,
            prealloc
        ])
        auction.transact().setup(token_contract.address)
        return token_contract
    return get


@pytest.fixture
def accounts(web3):
    def get(num):
        return [web3.eth.accounts[i] for i in range(num)]
    return get


def create_contract(chain, contract_type, arguments):
    print(chain, contract_type, arguments)
    deploy_txn_hash = contract_type.deploy(args=arguments)
    contract_address = chain.wait.for_contract_address(deploy_txn_hash)
    contract = contract_type(address=contract_address)
    return contract


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
