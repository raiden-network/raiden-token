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
    bp = mint.call().base_price()
    supply = 10000

    assert mint.call().curvePriceAtSupply(0) == mint.call().curvePriceAtReserve(0) == bp
    assert mint.call().curveReserveAtSupply(0) == mint.call().curveSupplyAtReserve(0) == 0

    assert mint.call().curveSupplyAtPrice(bp) == 0
    with pytest.raises(tester.TransactionFailed):
        assert mint.call().curveSupplyAtPrice(0) == 0

    web3.testing.mine(1)

    with pytest.raises(tester.TransactionFailed):
        assert mint.call().curveReserveAtPrice(0) == 0

    web3.testing.mine(1)

    price = mint.call().curvePriceAtSupply(supply)
    reserve = mint.call().curveReserveAtSupply(supply)
    print('price', price, 'reserve', reserve)

    assert mint.call().curveSupplyAtPrice(price) == supply

    # TODO see why this does not work
    # assert mint.call().curveSupplyAtReserve(reserve) == supply
    # assert mint.call().curvePriceAtReserve(reserve) == price
    assert mint.call().curveReserveAtPrice(price) == reserve


def test_mint(web3, mint_contract, auction_contract, token_contract):
    mint = mint_contract

    web3.testing.mine(3)

    assert mint.call().stage() == 0  # MintDeployed
    mint.transact().setup(auction_contract.address, token_contract.address)
    assert mint.call().stage() == 1  # MintSetUp

    assert mint.call({'from': web3.eth.coinbase}).issuedSupply() == 0
    # mint_contract.call().changeSettings(200, 15, 10, 2)


'''
def test_ownerFraction(mint_contract):
    #for i in range(len(mint_contract)):
    assert mint_contract.call().ownerFraction(100000) == 10000
    assert mint_contract.call().ownerFraction(123456) == 12345
'''
