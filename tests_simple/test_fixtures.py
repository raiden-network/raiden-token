import pytest

# base_price, price_factor, owner issuance fraction, owner issuance fraction decimals
mint_args = (10**9, 15, 10, 2)

# price_factor, price_const
auction_args = [
    (2 * 10**12, 10000),
    (3 * 10**10, 10000)
]

# auction order values for accounts; to be corelated with the above
accounts_orders = [
    (10 * 10**11, ),
    (15 * 10**11, ),
    (25 * 10**10, ),
    (60 * 10**10, ),
]

xassert_threshold_price = 10**9


@pytest.fixture()
def auction_contract(chain):
    Auction = chain.provider.get_contract_factory('Auction')
    auction_contract = create_contract(chain, Auction, auction_args[0])
    '''
    print_logs(auction_contract, 'Deployed', 'Auction')
    print_logs(auction_contract, 'Setup', 'Auction')
    print_logs(auction_contract, 'SettingsChanged', 'Auction')
    print_logs(auction_contract, 'AuctionStarted', 'Auction')
    print_logs(auction_contract, 'Ordered', 'Auction')
    print_logs(auction_contract, 'ClaimedTokens', 'Auction')
    print_logs(auction_contract, 'AuctionEnded', 'Auction')
    print_logs(auction_contract, 'AuctionSettled', 'Auction')
    print_logs(auction_contract, 'AuctionPrice', 'Auction')
    print_logs(auction_contract, 'MissingReserve', 'Auction')
    '''

    return auction_contract

@pytest.fixture()
def get_token_contract(chain):
    # contract can be mint_contract or proxy_contract
    def get(arguments):
        ReserveToken = chain.provider.get_contract_factory('ReserveToken')
        token_contract = create_contract(chain, ReserveToken, arguments)

        print_logs(token_contract, 'Redeemed', 'ReserveToken')
        print_logs(token_contract, 'Transfer', 'ReserveToken')

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
