import pytest
from ethereum import tester

from test_fixtures import (
    auction_contract,
    mint_contract,
    get_token_contract,
    accounts
)


@pytest.fixture()
def token_contract(chain, get_token_contract, mint_contract):
    token_contract = get_token_contract(mint_contract)
    return token_contract


def test_mint_curve(mint_contract, web3):
    mint = mint_contract
    reserve = 100000
    bp = mint.call().base_price()
    supply = mint.call().curveSupplyAtReserve(reserve)
    price = mint.call().curvePriceAtSupply(supply)

    # Test initial state
    assert mint.call().curvePriceAtSupply(0) == mint.call().curvePriceAtReserve(0) == bp
    assert mint.call().curveReserveAtSupply(0) == mint.call().curveSupplyAtReserve(0) == 0

    assert mint.call().curveSupplyAtPrice(bp) == 0
    with pytest.raises(tester.TransactionFailed):
        assert mint.call().curveSupplyAtPrice(0)

    web3.testing.mine(1)

    with pytest.raises(tester.TransactionFailed):
        assert mint.call().curveReserveAtPrice(0) == 0

    web3.testing.mine(1)

    # Test supply-price-reserve transformations
    assert mint.call().curveReserveAtSupply(supply) == mint.call().curveReserveAtPrice(price)

    # TODO
    # assert reserve == mint.call().curveReserveAtSupply(supply)
    # assert reserve == mint.call().curveReserveAtPrice(price)

    assert supply == mint.call().curveSupplyAtPrice(price)
    assert price == mint.call().curvePriceAtReserve(reserve)

    # Test cost calculations
    num = 1000
    token_cost = mint.call().curveCost(supply, num)
    assert token_cost > 0
    # TODO
    # assert num == mint.call().curveIssuable(supply, token_cost)

    # Test market cap
    market_cap = mint.call().curveMarketCapAtSupply(supply)
    assert market_cap == supply * price
    assert supply == mint.call().curveSupplyAtMarketCap(market_cap)


def test_mint(web3, mint_contract, auction_contract, token_contract):
    mint = mint_contract

    web3.testing.mine(3)

    assert mint.call().stage() == 0  # MintDeployed
    mint.transact().setup(auction_contract.address, token_contract.address)
    assert mint.call().stage() == 1  # MintSetUp

    assert mint.call({'from': web3.eth.coinbase}).issuedSupply() == 0
    mint_contract.call().changeSettings(200, 15, 10, 2)
    assert mint.call().stage() == 1  # MintSetUp


'''
def test_ownerFraction(mint_contract):
    #for i in range(len(mint_contract)):
    assert mint_contract.call().ownerFraction(100000) == 10000
    assert mint_contract.call().ownerFraction(123456) == 12345
'''
