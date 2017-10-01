import pytest
from eth_utils import decode_hex, keccak

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
fixture_decimals = [18]

auction_fast_decline_args = [10000000, 4, 2]
auction_contracts = ['DutchAuction']  # , 'DutchAuctionTest']


contract_args = [
    {
        'token': 'RaidenToken',
        'decimals': 18,
        'supply': 10000000,
        'args': [10000, 4, 2]
    },
    {
        'token': 'RaidenToken',
        'decimals': 18,
        'supply': 10000000,
        'args': [1000000, 20, 3]
    },
    {
        'token': 'RaidenToken',
        'decimals': 18,
        'supply': 10000000,
        'args': [2 * 10 ** 10, 524880000, 3]
    }
]

token_events = {
    'deploy': 'Deployed',
    'setup': 'Setup',
    'transfer': 'Transfer',
    'approve': 'Approval',
    'burn': 'Burnt'
}


def test_bytes(value=10, size=256):
    hex_value = decode_hex('{:x}'.format(value).zfill(size // 4))
    return keccak(hex_value)


@pytest.fixture()
def owner_index():
    return 2


@pytest.fixture()
def wallet_address(web3):
    return web3.eth.accounts[1]


@pytest.fixture()
def owner(web3, owner_index):
    return web3.eth.accounts[owner_index]


@pytest.fixture()
def get_bidders(web3, owner_index, contract_params, create_accounts):
    def get(number):
        index_start = owner_index + 1
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
def gnosis_multisig_wallet(chain, web3, create_contract):
    def get(owners, required):
        Multisig = chain.provider.get_contract_factory('MultiSigWallet')
        multisig_wallet = create_contract(Multisig, [
            owners, required
        ])

        return multisig_wallet
    return get


@pytest.fixture(params=auction_contracts)
def auction_contract(
    request,
    contract_params,
    chain,
    wallet_address,
    create_contract):
    auction_contract_type = request.param
    Auction = chain.provider.get_contract_factory(auction_contract_type)
    params = [wallet_address] + contract_params['args']
    auction_contract = create_contract(Auction, params, {}, ['Deployed'])

    if print_the_logs:
        print_logs(auction_contract, 'Deployed', auction_contract_type)
        print_logs(auction_contract, 'Setup', auction_contract_type)
        print_logs(auction_contract, 'AuctionStarted', auction_contract_type)
        print_logs(auction_contract, 'BidSubmission', auction_contract_type)
        print_logs(auction_contract, 'AuctionEnded', auction_contract_type)
        print_logs(auction_contract, 'ClaimedTokens', auction_contract_type)
        print_logs(auction_contract, 'TokensDistributed', auction_contract_type)

    return auction_contract


@pytest.fixture(params=auction_contracts)
def auction_contract_fast_decline(
    request,
    contract_params,
    chain,
    web3,
    wallet_address,
    create_contract):
    auction_contract_type = request.param
    Auction = chain.provider.get_contract_factory(auction_contract_type)
    params = [wallet_address] + contract_params['args']
    auction_contract = create_contract(Auction, params, {}, ['Deployed'])

    if print_the_logs:
        print_logs(auction_contract, 'Deployed', auction_contract_type)
        print_logs(auction_contract, 'Setup', auction_contract_type)
        print_logs(auction_contract, 'AuctionStarted', auction_contract_type)
        print_logs(auction_contract, 'BidSubmission', auction_contract_type)
        print_logs(auction_contract, 'AuctionEnded', auction_contract_type)
        print_logs(auction_contract, 'ClaimedTokens', auction_contract_type)
        print_logs(auction_contract, 'TokensDistributed', auction_contract_type)

    return auction_contract


@pytest.fixture()
def get_token_contract(chain, create_contract, owner):
    # contract can be auction contract or proxy contract
    def get(arguments, transaction=None, token_type='RaidenToken', decimals=18):
        if not decimals == 18:
            token_type = 'RaidenToken2'
            arguments.insert(0, decimals)

        RaidenToken = chain.provider.get_contract_factory(token_type)
        token_contract = create_contract(RaidenToken, arguments, transaction, ['Deployed'])

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
    wallet_address,
    contract_params,
    get_token_contract):
    decimals = contract_params['decimals']
    multiplier = 10 ** decimals
    supply = contract_params['supply'] * multiplier
    token_type = contract_params['token']

    def get(auction_address, transaction=None):
        args = [
            auction_address,
            wallet_address,
            supply
        ]

        token_contract = get_token_contract(args, transaction, token_type, decimals)

        return token_contract
    return get


@pytest.fixture()
def distributor_contract(chain, create_contract):
    def get(auction_address):
        Distributor = chain.provider.get_contract_factory('Distributor')
        distributor_contract = create_contract(Distributor, [auction_address])

        if print_the_logs:
            print_logs(distributor_contract, 'Distributed', 'Distributor')
            print_logs(distributor_contract, 'ClaimTokensCalled', 'Distributor')

        return distributor_contract
    return get


@pytest.fixture
def txnCost(chain, web3):
    def get(txn_hash):
        receipt = chain.wait.for_receipt(txn_hash)
        txn_cost = receipt['gasUsed'] * web3.eth.gasPrice
        return txn_cost
    return get


@pytest.fixture
def create_contract(chain, event_handler, owner):
    def get(contract_type, arguments, transaction=None, watch_events=[]):
        if not transaction:
            transaction = {}
        if 'from' not in transaction:
            transaction['from'] = owner

        deploy_txn_hash = contract_type.deploy(transaction=transaction, args=arguments)
        contract_address = chain.wait.for_contract_address(deploy_txn_hash)
        contract = contract_type(address=contract_address)

        for ev in watch_events:
            ev_handler = event_handler(contract)
            if ev_handler:
                ev_handler.add(deploy_txn_hash, ev)
                ev_handler.check()

        return contract
    return get
