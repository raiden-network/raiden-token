import pytest
from ethereum import tester
import test_helpers
import math

# (_base_price, _price_factor, _owner_fr, _owner_fr_dec)
params = [
    [
        (100, 15, 10, 2),
        {'supply': [1000, 6]}
    ]
]

# order value
accountp = [
    (200, ),
    (200, ),
    (300, ),
    (500, ),
]

@pytest.fixture()
def auction_contract(chain):
    Auction = chain.provider.get_contract_factory('Auction')
    auction_contract = test_helpers.create_contract(chain, Auction, [
        10**5, 10**3
    ])
    return auction_contract

@pytest.fixture()
def mint_contract(chain):
    Mint = chain.provider.get_contract_factory('Mint')
    mint_contract = test_helpers.create_contract(chain, Mint, params[0][0])
    return mint_contract;

@pytest.fixture
def accounts(web3):
    def get(num):
        return [web3.eth.accounts[i] for i in range(num)]
    return get

def test_auction(auction_contract, mint_contract, accounts, web3):
    assert auction_contract.call().stage() == 0 # AuctionDeployed
    auction_contract.transact().setup(mint_contract.address);
    assert auction_contract.call().stage() == 1 # AuctionSetUp

    auction_contract.transact().startAuction(False);
    assert auction_contract.call().stage() == 1 # AuctionStarted
    auction_contract.transact().startAuction(True);
    assert auction_contract.call().stage() == 2 # AuctionStarted

    # Test Auction curve price
    assert web3.eth.getBalance(auction_contract.address) == 0
    #assert web3.eth.getBalance(web3.eth.coinbase) == 0

    # Buyers start ordering tokens
    (A, B, C, D) = accounts(4)

    # Test multiple orders from 1 buyer
    assert auction_contract.call().bidders(A) == 0
    auction_contract.transact({'from': A, "value": accountp[0][0]-50}).order()
    assert auction_contract.call().bidders(A) == accountp[0][0]-50
    auction_contract.transact({'from': A, "value": 50}).order()
    assert auction_contract.call().bidders(A) == accountp[0][0]

    auction_contract.transact({'from': B, "value": accountp[1][0]}).order()
    auction_contract.transact({'from': C, "value": accountp[2][0]}).order()
    auction_contract.transact({'from': D, "value": accountp[3][0]}).order()
    assert auction_contract.call().bidders(B) == accountp[1][0]
    assert auction_contract.call().bidders(C) == accountp[2][0]
    assert auction_contract.call().bidders(D) == accountp[3][0]

    #assert web3.eth.getBalance(auction_contract.address) ==



#def test_price_surcharge(auction_contract):
#    assert auction_contract.call().price_surcharge() == 52
