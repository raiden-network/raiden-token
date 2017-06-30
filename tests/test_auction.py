import pytest
from ethereum import tester

@pytest.fixture()
def auction_contract(chain):
    Auction = chain.provider.get_contract_factory('Auction')
    deploy_txn_hash = Auction.deploy(args=[
        100, 2
    ])
    contract_address = chain.wait.for_contract_address(deploy_txn_hash)
    auction_contract = Auction(address=contract_address)
    return auction_contract

def test_price_surcharge(auction_contract):
    assert auction_contract.call().price_surcharge() == 52
