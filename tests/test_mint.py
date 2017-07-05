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

@pytest.fixture()
def mint_contract(chain):
    Mint = chain.provider.get_contract_factory('Mint')
    # mint_contracts = [ test_helpers.create_contract(chain, Mint, x[0:2]) for x in fractions ]
    mint_contract = test_helpers.create_contract(chain, Mint, params[0][0])
    return mint_contract;

def test_buyPreAuction(mint_contract):
    pass

def test_buy(mint_contract):
    pass

def test_sell(mint_contract):
    pass

def test_price(mint_contract):
    pass

def test_supply(mint_contract):
    for p in params:
        # mint_contract.call().changeSettings(*p[0])
        assert mint_contract.call().supply(p[1]['supply'][0]) == p[1]['supply'][1]
    # (-p[0] + math.sqrt(p[0]**2 + 2*p[1]*1000)) / p[1]

def test_reserve(mint_contract):
    pass

def test_supplyAtPrice(mint_contract):
    pass

def test_reserveAtPrice(mint_contract):
    pass

def test_cost(mint_contract):
    pass

def test_marketCap(mint_contract):
    pass

def test_saleCost(mint_contract):
    pass

def test_purchaseCost(mint_contract):
    pass

def test_ask(mint_contract):
    pass

def test_valuation(mint_contract):
    pass

def test_ownerFraction(mint_contract):
    #for i in range(len(mint_contract)):
    assert mint_contract.call().ownerFraction(100000) == 10000
    assert mint_contract.call().ownerFraction(123456) == 12345
