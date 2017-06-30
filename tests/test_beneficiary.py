import pytest
from ethereum import tester
import test_helpers

fractions = [
    (122, 3, 122, 878),
    (122, 0x0, 122, 878),
    (122, 5, 122, 99878),
]

@pytest.fixture()
def beneficiary_contracts(chain):
    Beneficiary = chain.provider.get_contract_factory('Beneficiary')
    beneficiary_contracts = [ test_helpers.create_contract(chain, Beneficiary, x[0:2]) for x in fractions ]
    return beneficiary_contracts


def test_get_fraction(beneficiary_contracts):
    for i in range(len(beneficiary_contracts)):
        assert beneficiary_contracts[i].call().get_fraction() == fractions[i][2]

def test_released_fraction(beneficiary_contracts):
    for i in range(len(beneficiary_contracts)):
        assert beneficiary_contracts[i].call().released_fraction() == fractions[i][3]
