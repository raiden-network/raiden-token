import pytest
from ethereum import tester
from functools import (
    reduce
)
from fixtures import (
    MAX_UINT,
    fake_address,
    token_events,
    owner_index,
    owner,
    wallet_address,
    get_bidders,
    fixture_decimals,
    contract_params,
    get_token_contract,
    token_contract,
    create_contract,
    print_logs,
    create_accounts,
    txnCost,
    test_bytes,
    event_handler,
)
from utils_logs import LogFilter


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
    wallet_address,
    get_token_contract,
    proxy_contract,
    decimals):
    (A, B, C, D, E) = web3.eth.accounts[:5]
    auction = proxy_contract
    multiplier = 10**(decimals)
    initial_supply = 5000 * multiplier

    # Transaction fails when auction address is invalid
    with pytest.raises(TypeError):
        token = get_token_contract([
            0,
            wallet_address,
            initial_supply
        ], {'from': E}, decimals=decimals)
    with pytest.raises(TypeError):
        token = get_token_contract([
            proxy_contract.address,
            0,
            wallet_address,
            initial_supply
        ], {'from': E}, decimals=decimals)
    with pytest.raises(TypeError):
        token = get_token_contract([
            fake_address,
            wallet_address,
            initial_supply
        ], {'from': E}, decimals=decimals)

    # Test max uint - 2 as supply (has to be even)
    token = get_token_contract([
        proxy_contract.address,
        wallet_address,
        MAX_UINT - 1
    ], {'from': E}, decimals=decimals)

    with pytest.raises(TypeError):
        token = get_token_contract([
            proxy_contract.address,
            wallet_address,
            MAX_UINT + 1
        ], {'from': E}, decimals=decimals)

    # Transaction fails if initial_supply == 0
    with pytest.raises(tester.TransactionFailed):
        token = get_token_contract([
            proxy_contract.address,
            wallet_address,
            0
        ], {'from': E}, decimals=decimals)

    with pytest.raises(TypeError):
        token = get_token_contract([
            proxy_contract.address,
            wallet_address,
            -2
        ], {'from': E}, decimals=decimals)

    # Fails when supply is an odd number; auction and wallet addresses
    # are assigned a different number of tokens
    with pytest.raises(tester.TransactionFailed):
        token = get_token_contract([
            proxy_contract.address,
            wallet_address,
            10000001,
        ], {'from': E}, decimals=decimals)

    token = get_token_contract([
        proxy_contract.address,
        wallet_address,
        initial_supply
    ], {'from': E}, decimals=decimals)
    assert token.call().decimals() == decimals


@pytest.mark.parametrize('decimals', fixture_decimals)
def test_token_variable_access(
    chain,
    web3,
    wallet_address,
    get_token_contract,
    proxy_contract,
    decimals):
    owner = web3.eth.coinbase
    (A, B, C) = web3.eth.accounts[1:4]
    multiplier = 10**(decimals)
    initial_supply = 3000 * multiplier

    token = get_token_contract([
        proxy_contract.address,
        wallet_address,
        initial_supply
    ], {'from': owner}, decimals=decimals)

    assert token.call().name() == 'Raiden Token'
    assert token.call().symbol() == 'RDN'
    assert token.call().decimals() == decimals
    assert token.call().totalSupply() == initial_supply


def test_token_balanceOf(
    chain,
    web3,
    wallet_address,
    token_contract,
    proxy_contract,
    contract_params):
    token = token_contract(proxy_contract.address)
    multiplier = 10**(contract_params['decimals'])

    supply = contract_params['supply'] * multiplier
    half_balance = supply // 2

    assert token.call().balanceOf(proxy_contract.address) == half_balance
    assert token.call().balanceOf(wallet_address) == half_balance


def transfer_tests(
    bidders,
    balances,
    multiplier,
    token,
    event_handler):
    (A, B, C) = bidders
    ev_handler = event_handler(token)

    with pytest.raises(TypeError):
        token.transact({'from': A}).transfer(0, 10)

    with pytest.raises(TypeError):
        token.transact({'from': A}).transfer(fake_address, 10)

    with pytest.raises(TypeError):
        token.transact({'from': A}).transfer(B, MAX_UINT + 1)

    with pytest.raises(TypeError):
        token.transact({'from': A}).transfer(B, -5)

    with pytest.raises(tester.TransactionFailed):
        balance_A = token.call().balanceOf(A)
        token.transact({'from': A}).transfer(B, balance_A + 1)

    with pytest.raises(tester.TransactionFailed):
        balance_B = token.call().balanceOf(B)
        token.transact({'from': A}).transfer(B, MAX_UINT + 1 - balance_B)

    txn_hash = token.transact({'from': A}).transfer(B, 0)
    ev_handler.add(txn_hash, token_events['transfer'])
    assert token.call().balanceOf(A) == balances[0]
    assert token.call().balanceOf(B) == balances[1]

    txn_hash = token.transact({'from': A}).transfer(B, 120)
    ev_handler.add(txn_hash, token_events['transfer'])
    assert token.call().balanceOf(A) == balances[0] - 120
    assert token.call().balanceOf(B) == balances[1] + 120

    txn_hash = token.transact({'from': B}).transfer(C, 66)
    ev_handler.add(txn_hash, token_events['transfer'])
    assert token.call().balanceOf(B) == balances[1] + 120 - 66
    assert token.call().balanceOf(C) == balances[2] + 66

    ev_handler.check()


def transfer_erc223_tests(
    bidders,
    balances,
    multiplier,
    token,
    proxy,
    token_erc223,
    proxy_erc223,
    event_handler):
    (A, B, C) = bidders
    ev_handler = event_handler(token_erc223)
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

    # TODO FIXME erc223 transfer event not handled correctly
    txn_hash = token.transact({'from': A}).transfer(proxy_erc223.address, balance_A, test_data)
    # ev_handler.add(txn_hash, token_events['transfer'])
    assert token.call().balanceOf(A) == 0
    assert token.call().balanceOf(proxy_erc223.address) == balance_proxy_erc223 + balance_A

    # Arbitrary tests to see if the tokenFallback function from the proxy is called
    assert proxy_erc223.call().sender() == A
    assert proxy_erc223.call().value() == balance_A

    balance_B = token.call().balanceOf(B)
    balance_proxy_erc223 = token.call().balanceOf(proxy_erc223.address)
    txn_hash = token.transact({'from': B}).transfer(proxy_erc223.address, 0, test_data2)
    # ev_handler.add(txn_hash, token_events['transfer'])
    assert token.call().balanceOf(B) == balance_B
    assert token.call().balanceOf(proxy_erc223.address) == balance_proxy_erc223
    assert proxy_erc223.call().sender() == B
    assert proxy_erc223.call().value() == 0

    txn_hash = token.transact({'from': A}).transfer(proxy_erc223.address, 0)
    # ev_handler.add(txn_hash, token_events['transfer'])

    txn_hash = token.transact({'from': A}).transfer(proxy.address, 0)
    # ev_handler.add(txn_hash, token_events['transfer'])

    ev_handler.check()


@pytest.mark.parametrize('decimals', fixture_decimals)
def test_token_transfer(
    chain,
    web3,
    wallet_address,
    get_bidders,
    get_token_contract,
    token_contract,
    proxy_contract,
    proxy_erc223_contract,
    decimals,
    event_handler):
    (A, B, C) = get_bidders(3)
    multiplier = 10**(decimals)

    token = get_token_contract([
        proxy_contract.address,
        wallet_address,
        5000 * multiplier,
    ], decimals=decimals)
    assert token.call().decimals() == decimals

    token.transact({'from': wallet_address}).transfer(A, 3000)
    token.transact({'from': wallet_address}).transfer(B, 2000)
    token.transact({'from': wallet_address}).transfer(C, 1000)

    transfer_tests(
        (A, B, C),
        [3000, 2000, 1000],
        multiplier,
        token,
        event_handler)

    token_erc223 = token_contract(proxy_erc223_contract.address)
    token_erc223.transact({'from': wallet_address}).transfer(A, 3000)
    token_erc223.transact({'from': wallet_address}).transfer(B, 2000)
    token_erc223.transact({'from': wallet_address}).transfer(C, 1000)

    transfer_erc223_tests(
        (A, B, C),
        [3000, 2000, 1000],
        multiplier,
        token,
        proxy_contract,
        token_erc223,
        proxy_erc223_contract,
        event_handler)


@pytest.mark.parametrize('decimals', fixture_decimals)
def test_token_approve(
    web3,
    wallet_address,
    get_token_contract,
    proxy_contract,
    decimals,
    event_handler):
    (A, B, C) = web3.eth.accounts[1:4]
    multiplier = 10**(decimals)

    token = get_token_contract([
        proxy_contract.address,
        wallet_address,
        5000 * multiplier
    ], decimals=decimals)
    assert token.call().decimals() == decimals
    ev_handler = event_handler(token)

    token.transact({'from': wallet_address}).transfer(A, 3000)
    token.transact({'from': wallet_address}).transfer(B, 2000)
    token.transact({'from': wallet_address}).transfer(C, 1000)

    with pytest.raises(TypeError):
        token.transact({'from': A}).approve(0, B)

    with pytest.raises(TypeError):
        token.transact({'from': A}).approve(fake_address, B)

    with pytest.raises(TypeError):
        token.transact({'from': A}).approve(B, -3)

    # We can approve more than we have
    # with pytest.raises(tester.TransactionFailed):
    txn_hash = token.transact({'from': A}).approve(B, 3000 + 1)
    ev_handler.add(txn_hash, token_events['approve'])

    txn_hash = token.transact({'from': A}).approve(A, 300)
    ev_handler.add(txn_hash, token_events['approve'])
    assert token.call().allowance(A, A) == 300

    with pytest.raises(tester.TransactionFailed):
        txn_hash = token.transact({'from': A}).approve(B, 300)

    txn_hash = token.transact({'from': A}).approve(B, 0)
    txn_hash = token.transact({'from': A}).approve(B, 300)
    ev_handler.add(txn_hash, token_events['approve'])

    txn_hash = token.transact({'from': B}).approve(C, 650)
    ev_handler.add(txn_hash, token_events['approve'])

    assert token.call().allowance(A, B) == 300
    assert token.call().allowance(B, C) == 650

    ev_handler.check()


@pytest.mark.parametrize('decimals', fixture_decimals)
def test_token_allowance(
    web3,
    wallet_address,
    get_bidders,
    get_token_contract,
    proxy_contract,
    decimals):
    (A, B) = get_bidders(2)
    multiplier = 10**(decimals)

    token = get_token_contract([
        proxy_contract.address,
        wallet_address,
        5000 * multiplier
    ], decimals=decimals)
    assert token.call().decimals() == decimals

    token.transact({'from': wallet_address}).transfer(A, 3000)
    token.transact({'from': wallet_address}).transfer(B, 2000)

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
    wallet_address,
    get_bidders,
    get_token_contract,
    proxy_contract,
    decimals,
    event_handler):
    (A, B, C) = get_bidders(3)
    multiplier = 10**(decimals)

    token = get_token_contract([
        proxy_contract.address,
        wallet_address,
        5000 * multiplier
    ], decimals=decimals)
    assert token.call().decimals() == decimals
    ev_handler = event_handler(token)

    token.transact({'from': wallet_address}).transfer(A, 3000)
    token.transact({'from': wallet_address}).transfer(B, 2000)
    token.transact({'from': wallet_address}).transfer(C, 1000)

    txn_hash = token.transact({'from': B}).approve(A, 300)
    ev_handler.add(txn_hash, token_events['approve'])
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
        token.transact({'from': A}).transferFrom(B, C, MAX_UINT + 1)

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
        overflow = MAX_UINT + 1 - balance_B
        token.transact({'from': B}).approve(A, overflow)
        token.transact({'from': A}).transferFrom(B, C, overflow)

    with pytest.raises(tester.TransactionFailed):
        txn_hash = token.transact({'from': B}).approve(A, 300)

    txn_hash = token.transact({'from': B}).approve(A, 0)
    txn_hash = token.transact({'from': B}).approve(A, 300)
    ev_handler.add(txn_hash, token_events['approve'])
    assert token.call().allowance(B, A) == 300

    balance_A = token.call().balanceOf(A)
    balance_B = token.call().balanceOf(B)
    balance_C = token.call().balanceOf(C)

    txn_hash = token.transact({'from': A}).transferFrom(B, C, 0)
    ev_handler.add(txn_hash, token_events['transfer'])
    assert token.call().balanceOf(A) == balance_A
    assert token.call().balanceOf(B) == balance_B
    assert token.call().balanceOf(C) == balance_C

    txn_hash = token.transact({'from': A}).transferFrom(B, C, 150)
    ev_handler.add(txn_hash, token_events['transfer'])
    assert token.call().balanceOf(A) == balance_A
    assert token.call().balanceOf(B) == balance_B - 150
    assert token.call().balanceOf(C) == balance_C + 150

    ev_handler.check()


@pytest.mark.parametrize('decimals', fixture_decimals)
def test_burn(
    chain,
    web3,
    wallet_address,
    get_bidders,
    get_token_contract,
    proxy_contract,
    decimals,
    txnCost,
    event_handler):
    decimals = 18
    eth = web3.eth
    (A, B) = get_bidders(2)
    multiplier = 10**(decimals)
    initial_supply = 5000 * multiplier

    token = get_token_contract([
        proxy_contract.address,
        wallet_address,
        initial_supply
    ], decimals=decimals)
    assert token.call().decimals() == decimals

    ev_handler = event_handler(token)

    token.transact({'from': wallet_address}).transfer(A, 3000)
    token.transact({'from': wallet_address}).transfer(B, 2000)

    with pytest.raises(TypeError):
        token.transact({'from': B}).burn(-3)

    with pytest.raises(TypeError):
        token.transact({'from': B}).burn(MAX_UINT + 1)

    with pytest.raises(tester.TransactionFailed):
        token.transact({'from': B}).burn(0)

    with pytest.raises(tester.TransactionFailed):
        token.transact({'from': B}).burn(2000 + 1)

    # Balance should not change besides transaction costs
    tokens_B = token.call().balanceOf(B)
    balance_B = eth.getBalance(B)
    burnt = 250
    txn_hash = token.transact({'from': B}).burn(burnt)
    txn_cost = txnCost(txn_hash)
    ev_handler.add(txn_hash, token_events['burn'])

    assert token.call().totalSupply() == initial_supply - burnt
    assert token.call().balanceOf(B) == tokens_B - burnt
    assert balance_B == eth.getBalance(B) + txn_cost

    tokens_B = token.call().balanceOf(B)
    balance_B = eth.getBalance(B)
    total_supply = token.call().totalSupply()

    txn_hash = token.transact({'from': B}).burn(tokens_B)
    txn_cost = txnCost(txn_hash)

    assert token.call().totalSupply() == total_supply - tokens_B
    assert token.call().balanceOf(B) == 0
    assert balance_B == eth.getBalance(B) + txn_cost

    ev_handler.check()


def test_event_handler(token_contract, proxy_contract, event_handler):
    token = token_contract(proxy_contract.address)
    ev_handler = event_handler(token)

    fake_txn = 0x0343

    # Add fake events with no transactions
    ev_handler.add(fake_txn, token_events['deploy'])
    ev_handler.add(fake_txn, token_events['setup'])
    ev_handler.add(fake_txn, token_events['transfer'])
    ev_handler.add(fake_txn, token_events['approve'])
    ev_handler.add(fake_txn, token_events['burn'])

    # This should fail
    with pytest.raises(Exception):
        ev_handler.check(1)
