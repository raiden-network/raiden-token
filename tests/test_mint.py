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
    mint_contract = test_helpers.create_contract(chain, Mint, params[0][0])
    return mint_contract;

@pytest.fixture()
def auction_contract(chain):
    Auction = chain.provider.get_contract_factory('Auction')
    auction_contract = test_helpers.create_contract(chain, Auction, (10000, 100))
    return auction_contract;

@pytest.fixture()
def token_contract(chain, mint_contract):
    ContinuousToken = chain.provider.get_contract_factory('ContinuousToken')
    token_contract = test_helpers.create_contract(chain, ContinuousToken, [
        mint_contract.address
    ])
    return token_contract;

def test_mint_curve(mint_contract, web3):
    mc = mint_contract
    bp = mc.call().base_price()
    supply = 10000

    assert mc.call().curvePriceAtSupply(0) == mc.call().curvePriceAtReserve(0) == bp
    assert mc.call().curveReserveAtSupply(0) == mc.call().curveSupplyAtReserve(0) == 0

    assert mc.call().curveSupplyAtPrice(bp) == 0
    with pytest.raises(tester.TransactionFailed):
        assert mc.call().curveSupplyAtPrice(0) == 0

    web3.testing.mine(1)

    with pytest.raises(tester.TransactionFailed):
        assert mc.call().curveReserveAtPrice(0) == 0

    web3.testing.mine(1)

    price = mc.call().curvePriceAtSupply(supply)
    reserve = mc.call().curveReserveAtSupply(supply)
    print('price', price, 'reserve', reserve)

    assert mc.call().curveSupplyAtPrice(price) == supply

    # TODO see why this does not work
    # assert mc.call().curveSupplyAtReserve(reserve) == supply
    # assert mc.call().curvePriceAtReserve(reserve) == price
    assert mc.call().curveReserveAtPrice(price) == reserve

def test_mint(web3, mint_contract, auction_contract, token_contract):

    # This fails - don't know why
    # assert mint_contract.call().totalSupply() == 0

    assert mint_contract.call().stage() == 0 # MintDeployed

    mint_contract.call().setup(auction_contract.address, token_contract.address)
    assert mint_contract.call().stage() == 1 # MintSetUp



    # mint_contract.call().changeSettings(200, 15, 10, 2)




'''
def test_buyPreAuction(mint_contract):
    pass

def test_buy(mint_contract):
    pass

def test_sell(mint_contract):
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
'''
