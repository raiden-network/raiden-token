import pytest

mint_args = (100, 15, 10, 2)


@pytest.fixture()
def auction_contract(chain):
    Auction = chain.provider.get_contract_factory('Auction')
    auction_contract = create_contract(chain, Auction, [
        200000, 100
    ])

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

    return auction_contract


@pytest.fixture()
def mint_contract(chain):
    Mint = chain.provider.get_contract_factory('Mint')
    mint_contract = create_contract(chain, Mint, mint_args)

    print_logs(mint_contract, 'Deployed', 'Mint')
    print_logs(mint_contract, 'Setup', 'Mint')
    print_logs(mint_contract, 'SettingsChanged', 'Mint')
    print_logs(mint_contract, 'StartedMinting', 'Mint')
    print_logs(mint_contract, 'ReceivedAuctionFunds', 'Mint')
    print_logs(mint_contract, 'IssuedFromAuction', 'Mint')
    print_logs(mint_contract, 'Issued', 'Mint')
    print_logs(mint_contract, 'Bought', 'Mint')
    print_logs(mint_contract, 'Sold', 'Mint')
    print_logs(mint_contract, 'Burnt', 'Mint')

    return mint_contract


@pytest.fixture()
def get_token_contract(chain):
    # contract can be mint_contract or proxy_contract
    def get(contract):
        ContinuousToken = chain.provider.get_contract_factory('ContinuousToken')
        token_contract = create_contract(chain, ContinuousToken, [
            contract.address
        ])
        print_logs(token_contract, 'Deployed', 'ContinuousToken')
        print_logs(token_contract, 'Issued', 'ContinuousToken')
        print_logs(token_contract, 'Destroyed', 'ContinuousToken')
        return token_contract
    return get


@pytest.fixture
def accounts(web3):
    def get(num):
        return [web3.eth.accounts[i] for i in range(num)]
    return get


def create_contract(chain, contract_type, arguments):
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

    transfer_filter.watch(lambda x: print('--(', name, ') log', event, x['args']))
