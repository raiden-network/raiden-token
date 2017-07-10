import pytest
from ethereum import tester
import test_helpers

# Proxy contract needed because issue and destroy from ContinuousToken
# have the `isMint` modifier; Mint functions are private, better do separate test
@pytest.fixture()
def proxy_contract(chain):
    MintProxy = chain.provider.get_contract_factory('MintProxy')
    proxy_contract = test_helpers.create_contract(chain, MintProxy, [])
    return proxy_contract;

@pytest.fixture()
def token_contract(chain, proxy_contract):
    ContinuousToken = chain.provider.get_contract_factory('ContinuousToken')
    token_contract = test_helpers.create_contract(chain, ContinuousToken, [
        proxy_contract.address
    ])
    return token_contract;

@pytest.fixture
def accounts(web3):
    def get(num):
        return [web3.eth.accounts[i] for i in range(num)]
    return get

# TODO general function call, with 1 data argument in bytes
@pytest.fixture
def issue(web3, proxy_contract, token_contract):
    def get(to, num):
        #bytes(web3.sha3("issue(address,uint256)")), web3.toAscii(to) ,bytes([3]))
        return proxy_contract.transact().proxy(token_contract.address, "issue(address,uint256)", to, num)
    return get

@pytest.fixture
def destroy(web3, proxy_contract, token_contract):
    def get(to, num):
        return proxy_contract.transact().proxy(token_contract.address, "destroy(address,uint256)", to, num)
    return get

def test_ctoken(chain, web3, accounts, issue, destroy, token_contract, proxy_contract):
    (A, B) = accounts(2)

    txn_hash = issue(A, 10)
    assert token_contract.call().totalSupply() == 10


    issue(B, 14)

    assert token_contract.call().totalSupply() == 24
    assert token_contract.call().balanceOf(A) == 10
    assert token_contract.call().balanceOf(B) == 14

    destroy(A, 2)
    destroy(B, 3)

    assert token_contract.call().totalSupply() == 19
    assert token_contract.call().balanceOf(A) == 8
    assert token_contract.call().balanceOf(B) == 11

    token_contract.transact({'from': A}).transfer(B, 2)
    token_contract.transact({'from': A}).transferFrom(A, B, 1)

    assert token_contract.call().totalSupply() == 19
    assert token_contract.call().balanceOf(A) == 5
    assert token_contract.call().balanceOf(B) == 14
