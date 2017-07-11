import pytest
from ethereum import tester
from test_fixtures import (
    auction_contract,
    mint_contract,
    get_token_contract,
    accounts
)

# order value
accountp = [
    (10000, ),
    (15000, ),
    (25000, ),
    (60000, ),
]


def test_auction(chain, accounts, web3, auction_contract, mint_contract, get_token_contract):
    # Buyers accounts
    (A, B, C, D) = accounts(4)

    eth = web3.eth
    auction = auction_contract
    mint = mint_contract
    token = get_token_contract(mint)
    mint.transact().setup(auction.address, token.address)

    # Initial Auction state
    assert auction.call().stage() == 0  # AuctionDeployed
    assert eth.getBalance(auction.address) == 0
    assert mint.call().issuedSupply() == 0

    # changeSettings needs AuctionSetUp / AuctionSettled
    with pytest.raises(tester.TransactionFailed):
        auction.transact().changeSettings(30, 40, True)

    auction.transact().setup(mint.address)
    assert auction.call().stage() == 1  # AuctionSetUp
    auction.transact().startAuction()
    assert auction.call().stage() == 2  # AuctionStarted

    # Buyers start ordering tokens

    # Test multiple orders from 1 buyer
    assert auction.call().bidders(A) == 0
    auction.transact({'from': A, "value": accountp[0][0] - 50}).order()
    assert auction.call().bidders(A) == accountp[0][0] - 50
    auction.transact({'from': A, "value": 50}).order()
    assert auction.call().bidders(A) == accountp[0][0]

    auction.transact({'from': B, "value": accountp[1][0]}).order()
    assert auction.call().bidders(B) == accountp[1][0]

    auction.transact({'from': C, "value": accountp[2][0]}).order()
    assert auction.call().bidders(C) == accountp[2][0]

    # Add all the orders up until this point
    bidded = 0
    for bidder in accountp[0:len(accountp) - 1]:
        bidded += bidder[0]
    assert eth.getBalance(auction.address) == bidded
    assert mint.call().combinedReserve() == (
        eth.getBalance(mint.address) + eth.getBalance(auction.address)
    )

    # Make an order > than missing_reserve to end auction
    missing_reserve = auction.call().missingReserveToEndAuction()
    auction.transact({'from': D, "value": missing_reserve + 100}).order()
    assert auction.call().bidders(D) == missing_reserve

    # TODO check if account has received back the difference
    # gas_price = eth.gasPrice
    # receive_back -= receipt['gasUsed'] * gas_price
    # assert eth.getBalance(D) == receive_back

    bidded += missing_reserve
    assert eth.getBalance(auction.address) == bidded

    # Auction ended, no more orders possible
    with pytest.raises(tester.TransactionFailed):
        auction.transact({'from': D, "value": 1000}).order()

    assert auction.call().stage() == 3  # AuctionEnded

    print('received_value', auction.call().received_value())
    print('total_issuance', auction.call().total_issuance())
    print('issued_value', auction.call().issued_value())

    # Test if funds have been transfered to Mint
    assert auction.call().issued_value() == 0
    assert auction.call().received_value() == bidded
    assert eth.getBalance(auction.address) == 0
    assert eth.getBalance(mint.address) == bidded
    assert mint.call().combinedReserve() == bidded

    # We should not be able to mint/destroy tokens
    with pytest.raises(tester.TransactionFailed):
        mint.transact({'from': A, "value": accountp[0][0]}).buy()
    with pytest.raises(tester.TransactionFailed):
        mint.transact({'from': A}).sell(5)

    '''
    # We should be able to transfer tokens
    token.transact({'from': D}).transfer(A, 10)
    assert auction.call().bidders(D) == accountp[3][0] - 100
    assert auction.call().bidders(A) == accountp[0][0] + 100

    '''

    # with pytest.raises(tester.TransactionFailed):
    #    pass


# TODO
# if total_issuance = 0
