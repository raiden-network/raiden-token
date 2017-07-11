import pytest
from test_fixtures import (
    get_token_contract,
    accounts,
    create_contract
)


# Proxy contract needed because issue and destroy from ContinuousToken
# have the `isMint` modifier; Mint functions are private, better do separate test
@pytest.fixture()
def proxy_contract(chain):
    MintProxy = chain.provider.get_contract_factory('MintProxy')
    proxy_contract = create_contract(chain, MintProxy, [])
    return proxy_contract


@pytest.fixture()
def token_contract(chain, get_token_contract, proxy_contract):
    token_contract = get_token_contract(proxy_contract)
    return token_contract


# TODO generalize this for any method - send bytes instead of args
# see contracts/proxies.sol
@pytest.fixture
def issue(web3, proxy_contract, token_contract):
    def get(to, num):
        return proxy_contract.transact().proxy(
            token_contract.address,
            "issue(address,uint256)",
            to,
            num
        )
    return get


@pytest.fixture
def destroy(web3, proxy_contract, token_contract):
    def get(to, num):
        return proxy_contract.transact().proxy(
            token_contract.address,
            "destroy(address,uint256)",
            to,
            num
        )
    return get


def test_ctoken(chain, web3, accounts, issue, destroy, token_contract):
    (A, B) = accounts(2)
    token = token_contract

    issue(A, 10)
    assert token.call().totalSupply() == 10

    issue(B, 14)
    assert token.call().totalSupply() == 24
    assert token.call().balanceOf(A) == 10
    assert token.call().balanceOf(B) == 14

    destroy(A, 2)
    destroy(B, 3)
    assert token.call().totalSupply() == 19
    assert token.call().balanceOf(A) == 8
    assert token.call().balanceOf(B) == 11

    token.transact({'from': A}).transfer(B, 2)
    token.transact({'from': A}).transferFrom(A, B, 1)
    assert token.call().totalSupply() == 19
    assert token.call().balanceOf(A) == 5
    assert token.call().balanceOf(B) == 14

    token.transact({'from': B}).transfer(A, 4)
    assert token.call().totalSupply() == 19
    assert token.call().balanceOf(A) == 9
    assert token.call().balanceOf(B) == 10

    # assert False
