import pytest
from ethereum import tester
from test_fixtures import (
    get_token_contract,
    accounts,
    create_contract,
    print_logs,
    multiplier,
    initial_supply,
    auction_supply,
    prealloc,
    bad_prealloc
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
        return proxy_contract.transact({'value': value}).proxyPayable(
            token_contract.address,
            "receiveReserve()"
        )
    return get


def test_ctoken(chain, web3, accounts, get_token_contract, proxy_contract, receiveReserve):
    (A, B, C, D) = accounts(4)
    auction = proxy_contract
    eth = web3.eth

    # Test preallocation > than initial supply - auction supply
    assert auction_supply + reduce((lambda x, y: x + y), bad_prealloc) != initial_supply
    with pytest.raises(tester.TransactionFailed):
        token = get_token_contract([
            auction.address,
            [A, B, C, D],
            bad_prealloc
        ])

    # TODO - Token initalization with no preallocation of tokens? - fails

    # Token initalization + preallocation of tokens
    assert auction_supply + reduce((lambda x, y: x + y), prealloc) == initial_supply
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
        token.transact({'from': A}).redeem(tokens_A + 1)

    # Cannot destroy tokens before token receives auction balance
    with pytest.raises(tester.TransactionFailed):
        token.transact({'from': A}).redeem(250)

    # Simulate auction balance transfer
    # Send the auction some funds
    auction.transact({'from': C, 'value': 10**5 * multiplier}).fund()
    auction.transact({'from': D, 'value': 10**5 * multiplier}).fund()
    auction_balance = eth.getBalance(auction.address)
    assert auction_balance == 2 * 10**5 * multiplier

    assert eth.getBalance(token.address) == 0
    receiveReserve(token, auction_balance)
    assert eth.getBalance(token.address) == auction_balance

    # Check token destruction & currency transfer
    tokens_A = token.call().balanceOf(A)
    redeemed = 250 * multiplier
    # balance_A = eth.getBalance(A)
    # expected_payment = eth.getBalance(token.address) * redeemed / initial_supply

    txn_hash = token.transact({'from': A}).redeem(redeemed)
    # receipt = chain.wait.for_receipt(txn_hash)
    # receive_back = receipt['gasUsed'] * eth.gasPrice
    assert token.call().totalSupply() == initial_supply - redeemed
    assert token.call().balanceOf(A) == tokens_A - redeemed
    # TODO add transaction cost
    # assert eth.getBalance(A) == balance_A + expected_payment
