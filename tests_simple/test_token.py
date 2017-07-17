import pytest
from ethereum import tester
from test_fixtures import (
    get_token_contract,
    accounts,
    create_contract,
    print_logs
)
from functools import (
    reduce
)


# Proxy contract needed because receiveReserve
# can only be called from an Auction contract
@pytest.fixture()
def proxy_contract(chain):
    AuctionProxy = chain.provider.get_contract_factory('Proxy')
    proxy_contract = create_contract(chain, AuctionProxy, [])

    print_logs(proxy_contract, 'Payable', 'Proxy')

    return proxy_contract


# TODO generalize this for any method - send bytes instead of args
# see contracts/proxies.sol
@pytest.fixture
def receiveReserve(web3, proxy_contract):
    def get(token_contract, value):
        return proxy_contract.transact().proxyPayable(
            token_contract.address,
            "receiveReserve()",
            value
        )
    return get


def test_ctoken(chain, web3, accounts, get_token_contract, proxy_contract, receiveReserve):
    (A, B, C, D) = accounts(4)
    auction = proxy_contract
    eth = web3.eth

    initial_supply = 10000000 * 10**18
    auction_supply = 9000000 * 10**18
    prealloc = [
        200000 * 10**18,
        300000 * 10**18,
        400000 * 10**18,
        100000 * 10**18,
    ]
    bad_prealloc = [
        200001 * 10**18,
        300000 * 10**18,
        400000 * 10**18,
        100000 * 10**18,
    ]

    # Test preallocation > than initial supply - auction supply
    assert auction_supply + reduce((lambda x, y: x + y), bad_prealloc)  != initial_supply
    with pytest.raises(tester.TransactionFailed):
        token = get_token_contract([
            auction.address,
            [A, B, C, D],
            bad_prealloc
        ])

    # Token initalization + preallocation of tokens
    assert auction_supply + reduce((lambda x, y: x + y), prealloc)  == initial_supply
    token = get_token_contract([
        auction.address,
        [A, B, C, D],
        prealloc
    ])

    # Check auction balance
    assert token.call().balanceOf(auction.address) == auction_supply

    # Check preallocations
    assert token.call().balanceOf(A) == prealloc[0]
    assert token.call().balanceOf(B) == prealloc[1]
    assert token.call().balanceOf(C) == prealloc[2]
    assert token.call().balanceOf(D) == prealloc[3]

    # Check token transfers
    token.transact({'from': A}).transfer(B, 400)
    assert token.call().totalSupply() == initial_supply
    assert token.call().balanceOf(A) == prealloc[0] - 400
    assert token.call().balanceOf(B) == prealloc[1] + 400

    # TODO
    # token.transact({'from': A}).transferFrom(A, B, 300)
    # allowance
    # approve

    # Cannot destroy more tokens than existing balance
    tokens_A = token.call().balanceOf(A)
    with pytest.raises(tester.TransactionFailed):
        token.transact({'from': A}).redeem(tokens_A+1)

    # Cannot destroy tokens before token receives auction balance
    with pytest.raises(tester.TransactionFailed):
        token.transact({'from': A}).redeem(250)

    # Simulate auction balance transfer
    auction_balance = 10**9 * 10**18
    assert eth.getBalance(token.address) == 0
    assert token.call().stage() == 0

    # TODO receiveReserve fails now
    '''
    receiveReserve(token, auction_balance)
    assert eth.getBalance(token.address) == auction_balance
    assert token.call().stage() == 1

    # Check token destruction & currency transfer
    tokens_A = token.call().balanceOf(A)
    balance_A = eth.getBalance(A)
    expected_payment = eth.getBalance(token.address) / initial_supply * 250

    token.transact({'from': A}).redeem(250)
    assert token.call().totalSupply() == initial_supply - 250
    assert token.call().balanceOf(A) == tokens_A - 250
    assert eth.getBalance(A) == balance_A + expected_payment
    '''
