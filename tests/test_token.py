import pytest
from ethereum import tester
from fixtures import (
    get_token_contract,
    create_contract,
    print_logs,
    multiplier,
    initial_supply,
    auction_supply,
    prealloc,
    auction_args,
    txnCost
)


# Proxy contract needed because receiveFunds
# can only be called from an Auction contract
@pytest.fixture()
def proxy_contract(chain, create_contract):
    AuctionProxy = chain.provider.get_contract_factory('Proxy')
    proxy_contract = create_contract(AuctionProxy, [])

    print_logs(proxy_contract, 'Payable', 'Proxy')

    return proxy_contract


# TODO generalize this for any method - send bytes instead of args
# see contracts/proxies.sol
@pytest.fixture
def receiveFunds(web3, proxy_contract):
    def get(token_contract, value):
        return proxy_contract.transact({'value': value}).proxyPayable(
            token_contract.address,
            "receiveFunds()"
        )
    return get


def test_token_init(chain, web3, get_token_contract, proxy_contract):
    (A, B, C, D) = web3.eth.accounts[:4]
    auction = proxy_contract
    preallocs = [
        500 * multiplier,
        800 * multiplier,
        1100 * multiplier,
        770 * multiplier
    ]

    # Transaction fails if different length arrays for owners & preallocation values
    with pytest.raises(tester.TransactionFailed):
        token = get_token_contract([
            auction.address,
            initial_supply,
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


def test_token_transfer(chain, web3, get_token_contract, proxy_contract):
    (A, B, C) = web3.eth.accounts[:3]
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

    with pytest.raises(tester.TransactionFailed):
        token.transact({'from': A}).transfer(B, 0)
    with pytest.raises(TypeError):
        token.transact({'from': A}).transfer(B, -5)
    with pytest.raises(tester.TransactionFailed):
        token.transact({'from': A}).transfer(B, preallocs[0] + 1)

    token.transact({'from': A}).transfer(B, 120)
    assert token.call().balanceOf(A) == 380
    assert token.call().balanceOf(B) == 920

    token.transact({'from': B}).transfer(C, 66)
    assert token.call().balanceOf(B) == 920 - 66
    assert token.call().balanceOf(C) == 1166


def test_token_transfer_from(chain, web3, get_token_contract, proxy_contract):
    (A, B, C) = web3.eth.accounts[:3]
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

    with pytest.raises(tester.TransactionFailed):
        token.transact().transferFrom(A, B, 0)
    with pytest.raises(TypeError):
        token.transact().transferFrom(A, B, -1)
    with pytest.raises(tester.TransactionFailed):
        token.transact().transferFrom(A, B, 301)

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


def test_token_variables(chain, web3, get_token_contract, proxy_contract):
    (A, B, C) = web3.eth.accounts[:3]
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


def test_burn(chain, web3, get_token_contract, proxy_contract, txnCost):
    eth = web3.eth
    (A, B, C) = web3.eth.accounts[:3]
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


def test_token_receiveFunds(
    chain,
    web3,
    get_token_contract,
    proxy_contract,
    receiveFunds,
    txnCost
):
    owners = web3.eth.accounts[:2]
    (A, B, C, D) = web3.eth.accounts[2:6]
    auction = proxy_contract
    eth = web3.eth

    # Token initalization + preallocation of tokens
    token = get_token_contract([
        auction.address,
        initial_supply,
        owners,
        prealloc
    ])
    assert token.call().totalSupply() == initial_supply

    # Check auction balance
    assert token.call().balanceOf(auction.address) == auction_supply

    # Check preallocations
    for index, owner in enumerate(owners):
        assert token.call().balanceOf(owner) == prealloc[index]

    # Check token transfers
    token.transact({'from': owners[0]}).transfer(A, 1000 * multiplier)
    token.transact({'from': A}).transfer(B, 400 * multiplier)
    assert token.call().totalSupply() == initial_supply
    assert token.call().balanceOf(owners[0]) == prealloc[0] - 1000 * multiplier
    assert token.call().balanceOf(A) == 600 * multiplier
    assert token.call().balanceOf(B) == 400 * multiplier

    # Cannot destroy more tokens than existing balance
    tokens_A = token.call().balanceOf(A)

    # Simulate auction balance transfer
    # Send the auction some funds
    auction.transact({'from': C, 'value': 10**5 * multiplier}).fund()
    auction.transact({'from': D, 'value': 10**5 * multiplier}).fund()
    auction_balance = eth.getBalance(auction.address)
    assert auction_balance == 2 * 10**5 * multiplier

    assert eth.getBalance(token.address) == 0
    receiveFunds(token, auction_balance)
    assert eth.getBalance(token.address) == auction_balance
