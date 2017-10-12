import pytest
from ethereum import tester
from fixtures import (
    owner_index,
    owner,
    wallet_address,
    get_bidders,
    contract_params,
    create_contract,
    get_token_contract,
    token_contract,
    auction_contract,
    create_accounts,
    txnCost,
    event_handler
)


# We need to change bid_threshold to something smaller for these tests to pass
def test_auction_whitelist(
    web3,
    owner,
    wallet_address,
    get_bidders,
    auction_contract,
    token_contract,
    contract_params,
    event_handler):
    eth = web3.eth
    auction = auction_contract
    (A, B, C, D, E, F) = get_bidders(6)

    # Initialize token
    token = token_contract(auction.address)

    assert auction.call().whitelist(A) == False
    assert auction.call().whitelist(B) == False
    assert auction.call().whitelist(C) == False
    assert auction.call().whitelist(D) == False
    assert auction.call().whitelist(E) == False

    # We should be able to whitelist at this point
    auction.transact({'from': owner}).addToWhitelist([A, B])
    assert auction.call().whitelist(A) == True
    assert auction.call().whitelist(B) == True

    auction.transact({'from': owner}).setup(token.address)

    auction.transact({'from': owner}).addToWhitelist([D])
    assert auction.call().whitelist(D) == True

    auction.transact({'from': owner}).startAuction()

    # Bid more than bid_threshold should fail for E
    value = auction.call().bid_threshold() + 1
    with pytest.raises(tester.TransactionFailed):
        eth.sendTransaction({
            'from': E,
            'to': auction.address,
            'value': value
        })

    with pytest.raises(tester.TransactionFailed):
        auction.transact({'from': E, "value": value}).bid()

    auction.transact({'from': owner}).addToWhitelist([E])
    assert auction.call().whitelist(E) == True

    # Bid more than bid_threshold should be ok for E
    eth.sendTransaction({
        'from': E,
        'to': auction.address,
        'value': value
    })

    auction.transact({'from': A, "value": value}).bid()

    # Test whitelist removal
    auction.transact({'from': B, "value": value}).bid()
    auction.transact({'from': owner}).removeFromWhitelist([B])
    assert auction.call().whitelist(B) == False

    with pytest.raises(tester.TransactionFailed):
        auction.transact({'from': B, "value": value}).bid()
