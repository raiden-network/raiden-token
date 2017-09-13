import pytest
from ethereum import tester
from eth_utils import decode_hex
from fixtures import (
    owner,
    contract_params,
    get_token_contract,
    token_contract,
    create_contract,
    print_logs,
    prepare_preallocs,
    txnCost
)


@pytest.fixture()
def proxy_contract(chain, create_contract):
    AuctionProxy = chain.provider.get_contract_factory('Proxy')
    proxy_contract = create_contract(AuctionProxy, [])

    print_logs(proxy_contract, 'Payable', 'Proxy')

    return proxy_contract


def test_token_init(
    chain,
    web3,
    get_token_contract,
    proxy_contract,
    contract_params):
    (A, B, C, D) = web3.eth.accounts[:4]
    auction = proxy_contract
    multiplier = 10**(contract_params['decimals'])
    initial_supply = contract_params['supply'] * multiplier

    preallocs = [
        500 * multiplier,
        800 * multiplier,
        1000 * multiplier,
        700 * multiplier
    ]

    # Transaction fails if different length arrays for owners & preallocation values
    with pytest.raises(tester.TransactionFailed):
        token = get_token_contract([
            auction.address,
            1000000 * multiplier,
            [A, B, C, D],
            [4000, 3000, 5000]
        ])

    with pytest.raises(tester.TransactionFailed):
        token = get_token_contract([
            proxy_contract.address,
            multiplier - 2,
            [A, B, C, D],
            preallocs
        ])

    token = get_token_contract([
        proxy_contract.address,
        initial_supply,
        [A, B, C, D],
        preallocs
    ])


def test_token_transfer(
    chain,
    web3,
    get_token_contract,
    proxy_contract,
    contract_params):
    (A, B, C) = web3.eth.accounts[:3]
    multiplier = 10**(contract_params['decimals'])
    initial_supply = contract_params['supply'] * multiplier
    preallocs = [
        500,
        800,
        1100
    ]
    token = get_token_contract([
        proxy_contract.address,
        initial_supply,
        [A, B, C],
        preallocs
    ])

    with pytest.raises(TypeError):
        token.transact({'from': A}).transfer(B, -5)
    with pytest.raises(tester.TransactionFailed):
        token.transact({'from': A}).transfer(B, preallocs[0] + 1)

    token.transact({'from': A}).transfer(B, 0)
    assert token.call().balanceOf(A) == 500
    assert token.call().balanceOf(B) == 800

    token.transact({'from': A}).transfer(B, 120)
    assert token.call().balanceOf(A) == 380
    assert token.call().balanceOf(B) == 920

    token.transact({'from': B}).transfer(C, 66)
    assert token.call().balanceOf(B) == 920 - 66
    assert token.call().balanceOf(C) == 1166


def test_token_transfer_from(
    chain,
    web3,
    get_token_contract,
    proxy_contract,
    contract_params):
    (A, B, C) = web3.eth.accounts[:3]
    multiplier = 10**(contract_params['decimals'])
    initial_supply = contract_params['supply'] * multiplier
    preallocs = [
        500,
        800,
        1100
    ]
    token = get_token_contract([
        proxy_contract.address,
        initial_supply,
        [A, B, C],
        preallocs
    ])

    # Check approve method
    with pytest.raises(tester.TransactionFailed):
        token.transact({'from': A}).approve(B, 0)
    with pytest.raises(TypeError):
        token.transact({'from': A}).approve(B, -3)

    token.transact({'from': A}).approve(B, 300)
    token.transact({'from': B}).approve(C, 650)

    assert token.call().allowance(A, B) == 300
    assert token.call().allowance(B, C) == 650


    with pytest.raises(TypeError):
        token.transact().transferFrom(A, B, -1)
    with pytest.raises(tester.TransactionFailed):
        token.transact().transferFrom(A, B, 301)

    token.transact().transferFrom(A, B, 0)
    assert token.call().allowance(A, B) == 300
    assert token.call().balanceOf(A) == 500
    assert token.call().balanceOf(B) == 800

    token.transact().transferFrom(A, B, 150)
    assert token.call().allowance(A, B) == 150
    assert token.call().balanceOf(A) == 350
    assert token.call().balanceOf(B) == 950

    with pytest.raises(tester.TransactionFailed):
        token.transact().transferFrom(A, B, 151)

    token.transact().transferFrom(A, B, 20)
    assert token.call().allowance(A, B) == 130
    assert token.call().balanceOf(A) == 330
    assert token.call().balanceOf(B) == 970

    token.transact().transferFrom(B, C, 650)
    assert token.call().allowance(B, C) == 0
    assert token.call().balanceOf(B) == 970 - 650
    assert token.call().balanceOf(C) == preallocs[2] + 650
    with pytest.raises(tester.TransactionFailed):
        token.transact().transferFrom(B, C, 5)


def test_token_transfer_erc223(
    chain,
    web3,
    token_contract,
    proxy_contract):
    (A, B) = web3.eth.accounts[:2]

    # proxy implements tokenFallback
    proxy = proxy_contract
    token = token_contract(proxy.address, {'from': A})

    test_data = decode_hex(B)  # random content at this point
    balance_A = token.call().balanceOf(A)
    balance_proxy = token.call().balanceOf(proxy.address)

    with pytest.raises(TypeError):
        token.transact({'from': A}).transfer(proxy.address, -5)
    with pytest.raises(tester.TransactionFailed):
        token.transact({'from': A}).transfer(proxy.address, balance_A + 1)

    token.transact({'from': A}).transfer(proxy.address, balance_A, test_data)
    assert token.call().balanceOf(A) == 0
    assert token.call().balanceOf(proxy.address) == balance_proxy + balance_A

    # Arbitrary tests to see if the tokenFallback function from the proxy is called
    assert proxy.call().sender() == A
    assert proxy.call().value() == balance_A

    token.transact({'from': A}).transfer(proxy.address, 0)

    assert token.call().balanceOf(A) == 0


def test_token_variables(
    chain,
    web3,
    get_token_contract,
    proxy_contract,
    contract_params):
    (A, B, C) = web3.eth.accounts[:3]
    multiplier = 10**(contract_params['decimals'])
    initial_supply = contract_params['supply'] * multiplier
    preallocs = [
        500,
        800,
        1100
    ]
    token = get_token_contract([
        proxy_contract.address,
        initial_supply,
        [A, B, C],
        preallocs
    ])

    assert token.call().name() == 'The Token'
    assert token.call().symbol() == 'TKN'
    assert token.call().decimals() == 18
    assert token.call().owner() == web3.eth.coinbase
    assert token.call().auction_address() == proxy_contract.address
    assert token.call().totalSupply() == initial_supply


def test_burn(
    chain,
    web3,
    get_token_contract,
    proxy_contract,
    contract_params,
    txnCost):
    eth = web3.eth
    (A, B, C) = web3.eth.accounts[:3]
    multiplier = 10**(contract_params['decimals'])
    initial_supply = contract_params['supply'] * multiplier
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
    ])

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
