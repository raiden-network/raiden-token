import pytest
from functools import (
    reduce
)

from web3.utils.compat import (
    Timeout,
)

from utils import (
    print_logs,
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
        CustomToken = chain.provider.get_contract_factory('CustomToken')
        token_contract = create_contract(CustomToken, arguments, transaction)

        print_logs(token_contract, 'Transfer', 'CustomToken')
        print_logs(token_contract, 'Approval', 'CustomToken')
        print_logs(token_contract, 'Deployed', 'CustomToken')
        print_logs(token_contract, 'Burnt', 'CustomToken')

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
