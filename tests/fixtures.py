import pytest
from eth_utils import decode_hex, keccak
from functools import (
    reduce
)

from utils import (
    print_logs,
)


MAX_UINT = 2**256
fake_address = 0x03432
print_the_logs = False
passphrase = '0'
fixture_decimals = [18, 1]


contract_args = [
    {
        'token': 'CustomToken',
        'decimals': 18,
        'supply': 10000000,
        'preallocations': [200000, 800000],
        'args': [2, 7500]
    },
    {
        'token': 'CustomToken',
        'decimals': 18,
        'supply': 10000000,
        'preallocations': [200400, 150000, 400001, 200010],
        'args': [3, 7500]
    }
]


contract_args += [
    {
        'token': 'CustomToken2',
        'decimals': 1,
        'supply': 10000000,
        'preallocations': [200000, 800000],
        'args': [5982, 59]
    },
    {
        'token': 'CustomToken2',
        'decimals': 1,
        'supply': 10000000,
        'preallocations': [200000, 800000],
        'args': [10000, 7500]
    }
]


# auction_supply = initial_supply - reduce((lambda x, y: x + y), prealloc)

def test_bytes(value=10, size=256):
    hex_value = decode_hex('{:x}'.format(value).zfill(size // 4))
    return keccak(hex_value)


def prepare_preallocs(multiplier, preallocs):
    return list(map(lambda x: x * multiplier, preallocs))


@pytest.fixture()
def owner(web3):
    return web3.eth.accounts[0]


@pytest.fixture()
def team(web3, contract_params):
    index_end = len(contract_params['preallocations']) + 1
    return web3.eth.accounts[2:(index_end + 1)]

@pytest.fixture()
def get_bidders(web3, contract_params, create_accounts):
    def get_these_bidders(number):
        index_start = 2 + len(contract_params['preallocations'])
        accounts_len = len(web3.eth.accounts)
        index_end = min(number + index_start, accounts_len)
        bidders = web3.eth.accounts[index_start:index_end]
        if number > len(bidders):
            bidders += create_accounts(number - len(bidders))
        return bidders
    return get_these_bidders


@pytest.fixture(params=contract_args)
def contract_params(request):
    return request.param


@pytest.fixture()
def create_accounts(web3):
    def create_more_accounts(number):
        new_accounts = []
        for i in range(0, number):
            new_account = web3.personal.newAccount(passphrase)
            amount = int(web3.eth.getBalance(web3.eth.accounts[0]) / 2 / number)
            web3.eth.sendTransaction({
                'from': web3.eth.accounts[0],
                'to': new_account,
                'value': amount
            })
            web3.personal.unlockAccount(new_account, passphrase)
            new_accounts.append(new_account)
        return new_accounts
    return create_more_accounts


@pytest.fixture()
def auction_contract(
    contract_params,
    chain,
    create_contract):
    Auction = chain.provider.get_contract_factory('DutchAuction')
    auction_contract = create_contract(Auction, contract_params['args'])

    if print_the_logs:
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
def get_token_contract(chain, create_contract, owner):
    # contract can be auction contract or proxy contract
    def get(arguments, transaction=None, token_type='CustomToken', decimals=18):
        if not decimals == 18:
            token_type = 'CustomToken2'
            arguments.insert(0, decimals)

        CustomToken = chain.provider.get_contract_factory(token_type)
        if not transaction:
            transaction = {'from': owner}
        # print('get_token_contract token_type', token_type, decimals, arguments)
        token_contract = create_contract(CustomToken, arguments, transaction)

        if print_the_logs:
            print_logs(token_contract, 'Transfer', token_type)
            print_logs(token_contract, 'Approval', token_type)
            print_logs(token_contract, 'Deployed', token_type)
            print_logs(token_contract, 'Burnt', token_type)

        return token_contract
    return get


@pytest.fixture()
def token_contract(
    chain,
    web3,
    owner,
    team,
    contract_params,
    get_token_contract):
    decimals = contract_params['decimals']
    multiplier = 10**(decimals)
    preallocations = contract_params['preallocations']
    supply = contract_params['supply'] * multiplier
    token_type = contract_params['token']

    def get(auction_address, transaction=None):
        args = [
            auction_address,
            supply,
            team,
            prepare_preallocs(multiplier, preallocations)
        ]

        token_contract = get_token_contract(args, transaction, token_type, decimals)

        return token_contract
    return get


@pytest.fixture()
def distributor_contract(
    chain,
    create_contract,
    auction_contract):
    Distributor = chain.provider.get_contract_factory('Distributor')
    distributor_contract = create_contract(Distributor, [auction_contract.address])

    if print_the_logs:
        print_logs(distributor_contract, 'Distributed', 'Distributor')
        print_logs(distributor_contract, 'ClaimTokensCalled', 'Distributor')

    return distributor_contract


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
