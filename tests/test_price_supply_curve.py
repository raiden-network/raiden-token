import pytest
from ethereum import tester
import math

@pytest.fixture()
def curve_contract(chain):
    PriceSupplyCurve = chain.provider.get_contract_factory('PriceSupplyCurve')
    deploy_txn_hash = PriceSupplyCurve.deploy(args=[
        2, 11
    ])
    contract_address = chain.wait.for_contract_address(deploy_txn_hash)
    curve_contract = PriceSupplyCurve(address=contract_address)
    return curve_contract

def test_supply(curve_contract):
    assert curve_contract.call().supply(23) == (-2 + math.sqrt(11**2 + 2*2*23)) / 2;

#(-base_price + Utils.sqrt(base_price**2 + 2 * factor * _reserve)) / factor;
