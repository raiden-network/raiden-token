import pytest
from ethereum import tester
import test_helpers
import math
#from import coder = require('../lib/solidity/coder');

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
    #Auction = chain.base.BaseChain.provider.get_contract_factory('Auction')
    auction_contract = test_helpers.create_contract(chain, Auction, [
        10000, 100
    ])
    return auction_contract

@pytest.fixture()
def mint_contract(chain):
    Mint = chain.provider.get_contract_factory('Mint')
    mint_contract = test_helpers.create_contract(chain, Mint, params[0][0])
    return mint_contract;

@pytest.fixture()
def token_contract(chain, auction_contract, mint_contract):
    ContinuousToken = chain.provider.get_contract_factory('ContinuousToken')
    token_contract = test_helpers.create_contract(chain, ContinuousToken, [
        mint_contract.address
    ])
    mint_contract.call().setup(auction_contract.address, token_contract.address)
    return token_contract;

@pytest.fixture
def accounts(web3):
    def get(num):
        return [web3.eth.accounts[i] for i in range(num)]
    return get

def test_auction(chain, accounts, web3, auction_contract, mint_contract, token_contract):
    # Buyers accounts
    (A, B, C, D) = accounts(4)

    assert auction_contract.call().stage() == 0 # AuctionDeployed

    # changeSettings needs AuctionSetUp / AuctionSettled
    with pytest.raises(tester.TransactionFailed):
        auction_contract.transact().changeSettings(30, 40, True)

    auction_contract.transact().setup(mint_contract.address);
    assert auction_contract.call().stage() == 1 # AuctionSetUp

    auction_contract.transact().startAuction();
    assert auction_contract.call().stage() == 2 # AuctionStarted

    assert web3.eth.getBalance(auction_contract.address) == 0

    # Test Auction curve price
    start = auction_contract.call().startTimestamp()
    missing_reserve = auction_contract.call().missingReserveToEndAuction()
    print('block', web3.eth.getBlock('latest')['number'], 'start timestamp', start, 'missing_reserve', missing_reserve);

    '''
    auction_price = auction_contract.call().price()
    a_p = auction_contract.call().price_factor() / 15 + auction_contract.call().price_const()
    assert auction_price == math.floor(a_p)
    print('auction_price', auction_price, a_p)

    print('block', web3.eth.getBlock('latest')['timestamp'], web3.eth.getBlock('latest')['number']);
    #chain.wait.for_block(block_number=2, timeout=4)
    '''

    # Buyers start ordering tokens

    # Test multiple orders from 1 buyer
    assert auction_contract.call().bidders(A) == 0
    auction_contract.transact({'from': A, "value": accountp[0][0]-50}).order()
    assert auction_contract.call().bidders(A) == accountp[0][0]-50
    auction_contract.transact({'from': A, "value": 50}).order()
    assert auction_contract.call().bidders(A) == accountp[0][0]

    auction_contract.transact({'from': B, "value": accountp[1][0]}).order()
    assert auction_contract.call().bidders(B) == accountp[1][0]

    auction_contract.transact({'from': C, "value": accountp[2][0]}).order()
    assert auction_contract.call().bidders(C) == accountp[2][0]

    auction_contract.transact({'from': D, "value": accountp[3][0]}).order()
    assert auction_contract.call().bidders(D) == accountp[3][0]

    # Add all the orders up until this point
    bidded = 0
    for bidder in accountp:
        bidded += bidder[0]
    assert web3.eth.getBalance(auction_contract.address) == bidded

    # We should not be able to mint/destroy tokens
    with pytest.raises(tester.TransactionFailed):
        mint_contract.transact({'from': A, "value": accountp[0][0]}).buy()
    with pytest.raises(tester.TransactionFailed):
        mint_contract.transact({'from': A}).sell(5)
    '''
    # We should be able to transfer tokens
    token_contract.transact({'from': D}).transfer(A, 100)
    assert auction_contract.call().bidders(D) == accountp[3][0] - 100
    assert auction_contract.call().bidders(A) == accountp[0][0] + 100
    '''

    # Fast forward to end auction
    web3.testing.mine(3)

    # Make an order > than missing_reserve
    missing_reserve = auction_contract.call().missingReserveToEndAuction()
    bA = web3.eth.getBalance(A)

    print('balance', web3.eth.getBalance(auction_contract.address))
    print('missing_reserve', missing_reserve)

    # This fails now - due to mint.totalSupply() failing
    txn_hash = auction_contract.transact({'from': A, "value": 1500}).order()
    receipt = chain.wait.for_receipt(txn_hash)
    logs = test_helpers.get_logs(chain, web3, receipt, ['uint'])
    print('logs', logs)

    # TODO check if account has received back the difference
    # this fails now - maybe transaction gas related
    # receive_back = bA - missing_reserve
    # gas_price = web3.eth.gasPrice
    # receive_back -= receipt['gasUsed'] * gas_price
    # assert web3.eth.getBalance(A) == receive_back

    # assert web3.eth.getBalance(auction_contract.address) == bidded + missing_reserve



    # Auction ended, no more orders possible
    with pytest.raises(tester.TransactionFailed):
        auction_contract.transact({'from': D, "value": 1000}).order()


    #with pytest.raises(tester.TransactionFailed):
    #    pass



#def test_price_surcharge(auction_contract):
#    assert auction_contract.call().price_surcharge() == 52
