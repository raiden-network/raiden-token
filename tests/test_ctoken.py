import pytest
from ethereum import tester

@pytest.fixture()
def ctoken_contract(chain):
    PriceSupplyCurve = chain.provider.get_contract_factory('PriceSupplyCurve')
    deploy_txn_hash = PriceSupplyCurve.deploy(args=[100, 2])
    contract_address = chain.wait.for_contract_address(deploy_txn_hash)
    curve_contract = PriceSupplyCurve(address=contract_address)

    Beneficiary = chain.provider.get_contract_factory('Beneficiary')
    deploy_txn_hash = Beneficiary.deploy(args=[100, 2])
    contract_address = chain.wait.for_contract_address(deploy_txn_hash)
    ben_contract = Beneficiary(address=contract_address)

    Auction = chain.provider.get_contract_factory('Auction')
    deploy_txn_hash = Auction.deploy(args=[100, 2])
    contract_address = chain.wait.for_contract_address(deploy_txn_hash)
    auction_contract = Auction(address=contract_address)

    ContinuousToken = chain.provider.get_contract_factory('ContinuousToken')
    deploy_txn_hash = ContinuousToken.deploy(args=[
        curve_contract, ben_contract, auction_contract
    ])
    contract_address = chain.wait.for_contract_address(deploy_txn_hash)
    ctoken_contract = ContinuousToken(address=contract_address)

    return ctoken_contract
