import pytest
from eth_utils import decode_hex, keccak
from functools import (
    reduce
)

from utils import (
    print_logs,
)

from utils_logs import (
    LogHandler
)


print_the_logs = False

MAX_UINT = 2**256 - 1
fake_address = 0x03432
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

token_events = {
    'deploy': 'Deployed',
    'setup': 'Setup',
    'transfer': 'Transfer',
    'approve': 'Approval',
    'burn': 'Burnt'
}


# auction_supply = initial_supply - reduce((lambda x, y: x + y), prealloc)

def test_bytes(value=10, size=256):
    hex_value = decode_hex('{:x}'.format(value).zfill(size // 4))
    return keccak(hex_value)


def prepare_preallocs(multiplier, preallocs):
    return list(map(lambda x: x * multiplier, preallocs))



@pytest.fixture()
def owner_index():
    return 2


@pytest.fixture()
def wallet(web3):
    return web3.eth.accounts[1]


@pytest.fixture()
def owner(web3, owner_index):
    return web3.eth.accounts[owner_index]


@pytest.fixture()
def team(web3, owner_index, contract_params):
    index_start = owner_index + 1
    index_end = len(contract_params['preallocations']) + index_start
    return web3.eth.accounts[index_start:index_end]

@pytest.fixture()
def get_bidders(web3, owner_index, contract_params, create_accounts):
    def get(number):
        index_start = owner_index + 1 + len(contract_params['preallocations'])
        accounts_len = len(web3.eth.accounts)
        index_end = min(number + index_start, accounts_len)
        bidders = web3.eth.accounts[index_start:index_end]
        if number > len(bidders):
            bidders += create_accounts(number - len(bidders))
        return bidders
    return get


@pytest.fixture(params=contract_args)
def contract_params(request):
    return request.param


@pytest.fixture()
def create_accounts(web3):
    def get(number):
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
    return get


@pytest.fixture()
def auction_contract(
    contract_params,
    chain,
    wallet,
    create_contract):
    Auction = chain.provider.get_contract_factory('DutchAuction')

    auction_contract = create_contract(Auction, [wallet] + contract_params['args'])

    if print_the_logs:
        print_logs(auction_contract, 'Deployed', 'DutchAuction')
        print_logs(auction_contract, 'Setup', 'DutchAuction')
        print_logs(auction_contract, 'SettingsChanged', 'DutchAuction')
        print_logs(auction_contract, 'AuctionStarted', 'DutchAuction')
        print_logs(auction_contract, 'BidSubmission', 'DutchAuction')
        print_logs(auction_contract, 'AuctionEnded', 'DutchAuction')
        print_logs(auction_contract, 'ClaimedTokens', 'DutchAuction')
        print_logs(auction_contract, 'TokensDistributed', 'DutchAuction')

    return auction_contract


@pytest.fixture()
def get_token_contract(chain, create_contract, owner):
    # contract can be auction contract or proxy contract
    def get(arguments, transaction=None, token_type='CustomToken', decimals=18):
        if not decimals == 18:
            token_type = 'CustomToken2'
            arguments.insert(0, decimals)

        CustomToken = chain.provider.get_contract_factory(token_type)

        # print('get_token_contract token_type', token_type, decimals, arguments)

        token_contract = create_contract(CustomToken, arguments, transaction)

        if print_the_logs:
            print_logs(token_contract, 'Transfer', token_type)
            print_logs(token_contract, 'Transfer2', token_type)
            print_logs(token_contract, 'Transfer3', token_type)
            print_logs(token_contract, 'Approval', token_type)
            print_logs(token_contract, 'Deployed', token_type)
            print_logs(token_contract, 'Burnt', token_type)

        return token_contract
    return get


@pytest.fixture()
def event_handler(chain, web3):
    def get(contract=None, address=None, abi=None):
        if contract:
            # Get contract factory name from contract instance
            # TODO is there an actual API for this??
            comp_target = contract.metadata['settings']['compilationTarget']
            name = comp_target[list(comp_target.keys())[0]]

            abi = chain.provider.get_base_contract_factory(name).abi
            address = contract.address

        if address and abi:
            return LogHandler(web3, address, abi)
        else:
            raise Exception('event_handler called without a contract instance')
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
def create_contract(chain, event_handler, owner):
    def get(contract_type, arguments, transaction=None):
        if not transaction:
            transaction = {}
        if 'from' not in transaction:
            transaction['from'] = owner

        deploy_txn_hash = contract_type.deploy(transaction=transaction, args=arguments)
        contract_address = chain.wait.for_contract_address(deploy_txn_hash)
        contract = contract_type(address=contract_address)

        # Check deploy event if not proxy contract
        if len(arguments) > 0:
            ev_handler = event_handler(contract)
            if ev_handler:
                ev_handler.add(deploy_txn_hash, token_events['deploy'])
                ev_handler.check()

        return contract
    return get
