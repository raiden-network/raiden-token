import pytest
from ethereum import tester
from test_fixtures import (
    auction_contract,
    mint_contract,
    get_token_contract,
    accounts
)
import math

# order value
accountp = [
    (10000, ),
    (15000, ),
    (25000, ),
    (60000, ),
]


def test_auction(chain, accounts, web3, auction_contract, mint_contract, get_token_contract):
    # Buyers accounts
    (Owner, A, B, C, D) = accounts(5)

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
    bidded += missing_reserve

    # TODO check if account has received back the difference
    # gas_price = eth.gasPrice
    # receive_back -= receipt['gasUsed'] * gas_price
    # assert eth.getBalance(D) == receive_back

    # Auction ended, no more orders possible
    with pytest.raises(tester.TransactionFailed):
        auction.transact({'from': D, "value": 1000}).order()

    assert auction.call().stage() == 3  # AuctionEnded

    # Test if funds have been transfered to Mint
    received_value = auction.call().received_value()
    assert auction.call().issued_value() == 0
    assert received_value == bidded
    assert eth.getBalance(auction.address) == 0
    assert eth.getBalance(mint.address) == bidded
    assert mint.call().combinedReserve() == bidded
    assert mint.call().stage() == 3  # AuctionEnded

    # TODO check total_issuance calculations
    # TODO test total_issuance = 0
    total_issuance = auction.call().total_issuance()
    print('total_issuance', total_issuance)
    print('received_value', received_value)

    # We should not be able to mint/destroy tokens until minting starts
    with pytest.raises(tester.TransactionFailed):
        mint.transact({'from': A, "value": accountp[0][0]}).buy()
    with pytest.raises(tester.TransactionFailed):
        mint.transact({'from': A}).sell(5)

    # Claim issued tokens
    issued_A = math.floor(auction.call().bidders(A) * total_issuance / received_value)
    issued_B = math.floor(auction.call().bidders(B) * total_issuance / received_value)
    issued_C = math.floor(auction.call().bidders(C) * total_issuance / received_value)
    issued_D = math.floor(auction.call().bidders(D) * total_issuance / received_value)
    print('issued tokens (A, B, C, D)', issued_A, issued_B, issued_C, issued_D)
    auction.transact().claimTokens(A)
    auction.transact().claimTokens(B)
    auction.transact().claimTokens(C)
    auction.transact().claimTokens(D)
    print('token totalSupply', token.call().totalSupply())

    # Test token receival
    issued_owner = 0
    issued_A_to_owner = mint.call().ownerFraction(issued_A)
    issued_A -= issued_A_to_owner
    issued_owner += issued_A_to_owner

    issued_B_to_owner = mint.call().ownerFraction(issued_B)
    issued_B -= issued_B_to_owner
    issued_owner += issued_B_to_owner

    issued_C_to_owner = mint.call().ownerFraction(issued_C)
    issued_C -= issued_C_to_owner
    issued_owner += issued_C_to_owner

    issued_D_to_owner = mint.call().ownerFraction(issued_D)
    issued_D -= issued_D_to_owner
    issued_owner += issued_D_to_owner

    assert issued_A == token.call().balanceOf(A)
    assert issued_B == token.call().balanceOf(B)
    assert issued_C == token.call().balanceOf(C)
    assert issued_D == token.call().balanceOf(D)

    assert issued_owner == token.call().balanceOf(Owner)
    assert token.call().totalSupply() == issued_A + issued_B + issued_C + issued_D + issued_owner

    assert auction.call().stage() == 4  # AuctionSettled
    assert mint.call().stage() == 4  # MintingActive

    # We should be able to mint/destroy tokens now
    # mint.transact({'from': A, "value": }).buy()
    # mint.transact({'from': A}).sell(5)

    # TODO start another auction with issuance 0 and lastCall=true

    '''
    # We should be able to transfer tokens
    token.transact({'from': D}).transfer(A, 10)
    assert auction.call().bidders(D) == accountp[3][0] - 100
    assert auction.call().bidders(A) == accountp[0][0] + 100

    '''

    # with pytest.raises(tester.TransactionFailed):
    #    pass
