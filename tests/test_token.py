import pytest
from ethereum import tester
from functools import (
    reduce
)
from fixtures import (
    MAX_UINT,
    fake_address,
    owner,
    team,
    get_bidders,
    fixture_decimals,
    contract_params,
    get_token_contract,
    token_contract,
    create_contract,
    print_logs,
    prepare_preallocs,
    create_accounts,
    txnCost,
    test_bytes
)


@pytest.fixture()
def proxy_contract(chain, create_contract):
    AuctionProxy = chain.provider.get_contract_factory('Proxy')
    proxy_contract = create_contract(AuctionProxy, [])

    print_logs(proxy_contract, 'Payable', 'Proxy')

    return proxy_contract


@pytest.fixture()
def proxy_erc223_contract(chain, create_contract):
    AuctionProxy = chain.provider.get_contract_factory('ProxyERC223')
    proxy_erc223_contract = create_contract(AuctionProxy, [])

    return proxy_erc223_contract


@pytest.mark.parametrize('decimals', fixture_decimals)
def test_token_init(
    chain,
    web3,
    get_token_contract,
    proxy_contract,
    decimals):
    (A, B, C, D) = web3.eth.accounts[:4]
    auction = proxy_contract
    multiplier = 10**(decimals)
    initial_supply = 5000 * multiplier

    preallocs = [
        500 * multiplier,
        800 * multiplier,
        1000 * multiplier,
        700 * multiplier
    ]

    # Transaction fails when auction address is invalid
    with pytest.raises(TypeError):
        token = get_token_contract([
            0,
            initial_supply,
            [A, B, C, D],
            preallocs
        ], decimals=decimals)
    with pytest.raises(TypeError):
        token = get_token_contract([
            0x00343,
            initial_supply,
            [A, B, C, D],
            preallocs
        ], decimals=decimals)

    # Transaction fails when team addresses are invalid
    with pytest.raises(TypeError):
        token = get_token_contract([
            proxy_contract.address,
            initial_supply,
            [A, 0, C, D],
            preallocs
        ], decimals=decimals)
    with pytest.raises(TypeError):
        token = get_token_contract([
            proxy_contract.address,
            initial_supply,
            [A, 0x00343, C, D],
            preallocs
        ], decimals=decimals)

    # Transaction fails when supply or preallocations are not uint
    with pytest.raises(TypeError):
        token = get_token_contract([
            proxy_contract.address,
            -2,
            [A, B, C, D],
            preallocs
        ], decimals=decimals)

    with pytest.raises(TypeError):
        token = get_token_contract([
            proxy_contract.address,
            initial_supply,
            [A, B, C, D],
            [500 * multiplier, -2]
        ], decimals=decimals)

    with pytest.raises(TypeError):
        token = get_token_contract([
            proxy_contract.address,
            MAX_UINT,
            [A, B, C, D],
            preallocs
        ], decimals=decimals)

    # Transaction fails if different length arrays for owners & preallocation values
    with pytest.raises(tester.TransactionFailed):
        token = get_token_contract([
            proxy_contract.address,
            1000000 * multiplier,
            [A, B, C, D],
            [4000, 3000, 5000]
        ], decimals=decimals)

    # Transaction fails if initial_supply == 0
    with pytest.raises(tester.TransactionFailed):
        token = get_token_contract([
            proxy_contract.address,
            0,
            [A, B, C, D],
            [0, 0, 0, 0]
        ], decimals=decimals)

    # Transaction fails of there are no preallocations
    with pytest.raises(tester.TransactionFailed):
        token = get_token_contract([
            proxy_contract.address,
            initial_supply,
            [],
            []
        ], decimals=decimals)

    # Fails when initial_supply < preallocations
    with pytest.raises(tester.TransactionFailed):
        token = get_token_contract([
            proxy_contract.address,
            multiplier - 2,
            [A, B, C, D],
            preallocs
        ], decimals=decimals)

    # Fails when auctioned tokens <= 0
    with pytest.raises(tester.TransactionFailed):
        token = get_token_contract([
            proxy_contract.address,
            reduce((lambda x, y: x + y), preallocs),
            [A, B, C, D],
            preallocs
        ], decimals=decimals)

    token = get_token_contract([
        proxy_contract.address,
        initial_supply,
        [A, B, C, D],
        preallocs
    ], decimals=decimals)
    assert token.call().decimals() == decimals


@pytest.mark.parametrize('decimals', fixture_decimals)
def test_token_variable_access(
    chain,
    owner,
    web3,
    get_token_contract,
    proxy_contract,
    decimals):
    (A, B, C) = web3.eth.accounts[1:4]
    multiplier = 10**(decimals)
    initial_supply = 3000 * multiplier
    preallocs = [
        500 * multiplier,
        800 * multiplier,
        1100 * multiplier
    ]
    token = get_token_contract([
        proxy_contract.address,
        initial_supply,
        [A, B, C],
        preallocs
    ], decimals=decimals)

    assert token.call().name() == 'The Token'
    assert token.call().symbol() == 'TKN'
    assert token.call().decimals() == decimals
    assert token.call().owner() == web3.eth.coinbase
    assert token.call().auction_address() == proxy_contract.address
    assert token.call().totalSupply() == initial_supply


def test_token_balanceOf(
    chain,
    web3,
    team,
    token_contract,
    proxy_contract,
    contract_params):
    token = token_contract(proxy_contract.address)
    multiplier = 10**(contract_params['decimals'])
    auction_address = token.call().auction_address()

    supply = contract_params['supply'] * multiplier
    preallocs = contract_params['preallocations']
    preallocs = prepare_preallocs(multiplier, preallocs)
    auction_balance = supply - reduce((lambda x, y: x + y), preallocs)

    assert token.call().balanceOf(auction_address) == auction_balance

    for i, member in enumerate(team):
        assert token.call().balanceOf(member) == preallocs[i]


def transfer_tests(
    bidders,
    multiplier,
    preallocs,
    token):
    (A, B, C) = bidders

    with pytest.raises(TypeError):
        token.transact({'from': A}).transfer(0, 10)

    with pytest.raises(TypeError):
        token.transact({'from': A}).transfer(fake_address, 10)

    with pytest.raises(TypeError):
        token.transact({'from': A}).transfer(B, MAX_UINT)

    with pytest.raises(TypeError):
        token.transact({'from': A}).transfer(B, -5)

    with pytest.raises(tester.TransactionFailed):
        balance_A = token.call().balanceOf(A)
        token.transact({'from': A}).transfer(B, balance_A + 1)

    with pytest.raises(tester.TransactionFailed):
        balance_B = token.call().balanceOf(B)
        token.transact({'from': A}).transfer(B, MAX_UINT + 1 - balance_B)

    token.transact({'from': A}).transfer(B, 0)
    assert token.call().balanceOf(A) == preallocs[0]
    assert token.call().balanceOf(B) == preallocs[1]

    token.transact({'from': A}).transfer(B, 120)
    assert token.call().balanceOf(A) == preallocs[0] - 120
    assert token.call().balanceOf(B) == preallocs[1] + 120

    token.transact({'from': B}).transfer(C, 66)
    assert token.call().balanceOf(B) == preallocs[1] + 120 - 66
    assert token.call().balanceOf(C) == preallocs[2] + 66


def transfer_erc223_tests(
    bidders,
    multiplier,
    preallocs,
    token,
    proxy,
    token_erc223,
    proxy_erc223):
    (A, B, C) = bidders
    test_data = test_bytes()  # 32 bytes
    test_data2 = test_bytes(value=20)
    assert not test_data == test_data2

    balance_A = token.call().balanceOf(A)
    balance_proxy = token.call().balanceOf(proxy.address)
    balance_proxy_erc223 = token.call().balanceOf(proxy_erc223.address)

    with pytest.raises(TypeError):
        token.transact({'from': A}).transfer(B, balance_A, 0)

    # Make sure it fails when internal call of transfer(to, value) fails
    with pytest.raises(tester.TransactionFailed):
        token.transact({'from': A}).transfer(B, balance_A + 1, test_data)

    with pytest.raises(tester.TransactionFailed):
        token.transact({'from': A}).transfer(proxy_erc223.address, balance_A + 1, test_data)

    # Receiver contracts without a tokenFallback
    with pytest.raises(tester.TransactionFailed):
        token.transact({'from': A}).transfer(proxy.address, balance_A, test_data)

    token.transact({'from': A}).transfer(proxy_erc223.address, balance_A, test_data)
    assert token.call().balanceOf(A) == 0
    assert token.call().balanceOf(proxy_erc223.address) == balance_proxy_erc223 + balance_A

    # Arbitrary tests to see if the tokenFallback function from the proxy is called
    assert proxy_erc223.call().sender() == A
    assert proxy_erc223.call().value() == balance_A

    balance_B = token.call().balanceOf(B)
    balance_proxy_erc223 = token.call().balanceOf(proxy_erc223.address)
    token.transact({'from': B}).transfer(proxy_erc223.address, 0, test_data2)
    assert token.call().balanceOf(B) == balance_B
    assert token.call().balanceOf(proxy_erc223.address) == balance_proxy_erc223
    assert proxy_erc223.call().sender() == B
    assert proxy_erc223.call().value() == 0

    token.transact({'from': A}).transfer(proxy_erc223.address, 0)
    token.transact({'from': A}).transfer(proxy.address, 0)


@pytest.mark.parametrize('decimals', fixture_decimals)
def test_token_transfer(
    chain,
    web3,
    get_token_contract,
    token_contract,
    proxy_contract,
    proxy_erc223_contract,
    decimals):
    (A, B, C) = web3.eth.accounts[1:4]
    multiplier = 10**(decimals)
    preallocs = [
        500 * multiplier,
        800 * multiplier,
        1100 * multiplier
    ]
    token = get_token_contract([
        proxy_contract.address,
        5000 * multiplier,
        [A, B, C],
        preallocs
    ], decimals=decimals)
    assert token.call().decimals() == decimals

    transfer_tests(
        (A, B, C),
        multiplier,
        preallocs,
        token)

    token = token_contract(proxy_contract.address)
    token_erc223 = token_contract(proxy_erc223_contract.address)

    transfer_erc223_tests(
        (A, B, C),
        multiplier,
        preallocs,
        token,
        proxy_contract,
        token_erc223,
        proxy_erc223_contract)


@pytest.mark.parametrize('decimals', fixture_decimals)
def test_token_approve(
    web3,
    get_token_contract,
    proxy_contract,
    decimals):
    (A, B, C) = web3.eth.accounts[1:4]
    multiplier = 10**(decimals)
    preallocs = [
        500 * multiplier,
        800 * multiplier,
        1100 * multiplier
    ]

    token = get_token_contract([
        proxy_contract.address,
        5000 * multiplier,
        [A, B, C],
        preallocs
    ], decimals=decimals)
    assert token.call().decimals() == decimals

    with pytest.raises(TypeError):
        token.transact({'from': A}).approve(0, B)

    with pytest.raises(TypeError):
        token.transact({'from': A}).approve(fake_address, B)

    with pytest.raises(TypeError):
        token.transact({'from': A}).approve(B, -3)

    with pytest.raises(tester.TransactionFailed):
        token.transact({'from': A}).approve(B, 0)

    # We can approve more than we have
    # with pytest.raises(tester.TransactionFailed):
    token.transact({'from': A}).approve(B, preallocs[0] + 1)

    token.transact({'from': A}).approve(A, 300)
    assert token.call().allowance(A, A) == 300

    token.transact({'from': A}).approve(B, 300)
    token.transact({'from': B}).approve(C, 650)

    assert token.call().allowance(A, B) == 300
    assert token.call().allowance(B, C) == 650


@pytest.mark.parametrize('decimals', fixture_decimals)
def test_token_allowance(
    web3,
    get_token_contract,
    proxy_contract,
    decimals):
    (A, B, C) = web3.eth.accounts[1:4]
    multiplier = 10**(decimals)
    preallocs = [
        500 * multiplier,
        800 * multiplier,
        1100 * multiplier
    ]
    token = get_token_contract([
        proxy_contract.address,
        5000 * multiplier,
        [A, B, C],
        preallocs
    ], decimals=decimals)
    assert token.call().decimals() == decimals

    with pytest.raises(TypeError):
        token.call().allowance(0, B)

    with pytest.raises(TypeError):
        token.call().allowance(fake_address, B)

    with pytest.raises(TypeError):
        token.call().allowance(A, 0)

    with pytest.raises(TypeError):
        token.call().allowance(A, fake_address)

    assert token.call().allowance(A, B) == 0
    assert token.call().allowance(B, A) == 0

    token.transact({'from': A}).approve(B, 300)
    assert token.call().allowance(A, B) == 300


@pytest.mark.parametrize('decimals', fixture_decimals)
def test_token_transfer_from(
    chain,
    web3,
    get_token_contract,
    proxy_contract,
    decimals):
    (A, B, C) = web3.eth.accounts[1:4]
    multiplier = 10**(decimals)
    preallocs = [
        500 * multiplier,
        800 * multiplier,
        1100 * multiplier
    ]
    token = get_token_contract([
        proxy_contract.address,
        5000 * multiplier,
        [A, B, C],
        preallocs
    ], decimals=decimals)
    assert token.call().decimals() == decimals

    token.transact({'from': B}).approve(A, 300)
    assert token.call().allowance(B, A) == 300

    with pytest.raises(TypeError):
        token.transact({'from': A}).transferFrom(0, C, 10)

    with pytest.raises(TypeError):
        token.transact({'from': A}).transferFrom(B, 0, 10)

    with pytest.raises(TypeError):
        token.transact({'from': A}).transferFrom(fake_address, C, 10)

    with pytest.raises(TypeError):
        token.transact({'from': A}).transferFrom(B, fake_address, 10)

    with pytest.raises(TypeError):
        token.transact({'from': A}).transferFrom(B, C, MAX_UINT)

    with pytest.raises(TypeError):
        token.transact({'from': A}).transferFrom(B, C, -5)

    with pytest.raises(tester.TransactionFailed):
        allowance_B = token.call().allowance(B, A)
        token.transact({'from': A}).transferFrom(B, C, allowance_B + 1)

    # We can allow more than the balance, but we cannot transfer more
    with pytest.raises(tester.TransactionFailed):
        balance_B = token.call().balanceOf(B)
        token.transact({'from': B}).approve(A, balance_B + 10)
        token.transact({'from': A}).transferFrom(B, C, balance_B + 10)

    # Test for overflow
    with pytest.raises(tester.TransactionFailed):
        balance_B = token.call().balanceOf(B)
        overflow = MAX_UINT - balance_B
        token.transact({'from': B}).approve(A, overflow)
        token.transact({'from': A}).transferFrom(B, C, overflow)

    token.transact({'from': B}).approve(A, 300)
    assert token.call().allowance(B, A) == 300

    balance_A = token.call().balanceOf(A)
    balance_B = token.call().balanceOf(B)
    balance_C = token.call().balanceOf(C)

    token.transact({'from': A}).transferFrom(B, C, 0)
    assert token.call().balanceOf(A) == balance_A
    assert token.call().balanceOf(B) == balance_B
    assert token.call().balanceOf(C) == balance_C

    token.transact({'from': A}).transferFrom(B, C, 150)
    assert token.call().balanceOf(A) == balance_A
    assert token.call().balanceOf(B) == balance_B - 150
    assert token.call().balanceOf(C) == balance_C + 150


@pytest.mark.parametrize('decimals', fixture_decimals)
def test_burn(
    chain,
    web3,
    get_token_contract,
    proxy_contract,
    decimals,
    txnCost):
    eth = web3.eth
    (A, B, C) = eth.accounts[1:4]
    multiplier = 10**(decimals)
    initial_supply = 5000 * multiplier
    preallocs = [
        500 * multiplier,
        800 * multiplier,
        1100 * multiplier
    ]
    token = get_token_contract([
        proxy_contract.address,
        initial_supply,
        [A, B, C],
        preallocs
    ], decimals=decimals)
    assert token.call().decimals() == decimals

    with pytest.raises(TypeError):
        token.transact({'from': B}).burn(-3)

    with pytest.raises(TypeError):
        token.transact({'from': B}).burn(MAX_UINT)

    with pytest.raises(tester.TransactionFailed):
        token.transact({'from': B}).burn(0)

    with pytest.raises(tester.TransactionFailed):
        token.transact({'from': B}).burn(preallocs[1] + 1)

    # Balance should not change besides transaction costs
    tokens_B = token.call().balanceOf(B)
    balance_B = eth.getBalance(B)
    burnt = 250 * multiplier
    txn_cost = txnCost(token.transact({'from': B}).burn(burnt))

    assert token.call().totalSupply() == initial_supply - burnt
    assert token.call().balanceOf(B) == tokens_B - burnt
    assert balance_B == eth.getBalance(B) + txn_cost

    tokens_B = token.call().balanceOf(B)
    balance_B = eth.getBalance(B)
    total_supply = token.call().totalSupply()

    txn_cost = txnCost(token.transact({'from': B}).burn(tokens_B))

    assert token.call().totalSupply() == total_supply - tokens_B
    assert token.call().balanceOf(B) == 0
    assert balance_B == eth.getBalance(B) + txn_cost
