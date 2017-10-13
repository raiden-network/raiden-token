import pytest
from ethereum import tester
from fixtures import (
    owner_index,
    owner,
    wallet_address,
    whitelister_address,
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
    chain,
    web3,
    owner,
    wallet_address,
    whitelister_address,
    get_bidders,
    create_contract,
    token_contract,
    contract_params,
    event_handler):
    eth = web3.eth
    (A, B, C, D, E, F) = get_bidders(6)

    Auction = chain.provider.get_contract_factory('DutchAuction')
    args = [wallet_address, whitelister_address, 2 * 10 ** 18, 1574640000, 3]
    auction = create_contract(Auction, args, {'from': owner})

    # Initialize token
    token = token_contract(auction.address)
    bid_threshold = auction.call().bid_threshold()

    assert auction.call().whitelist(A) == False
    assert auction.call().whitelist(B) == False
    assert auction.call().whitelist(C) == False
    assert auction.call().whitelist(D) == False
    assert auction.call().whitelist(E) == False

    # Only the whitelister_address can add addresses to the whitelist
    with pytest.raises(tester.TransactionFailed):
        auction.transact({'from': owner}).addToWhitelist([A, B])
    with pytest.raises(tester.TransactionFailed):
        auction.transact({'from': wallet_address}).addToWhitelist([A, B])
    with pytest.raises(tester.TransactionFailed):
        auction.transact({'from': A}).addToWhitelist([A, B])
    with pytest.raises(tester.TransactionFailed):
        auction.transact({'from': C}).addToWhitelist([A, B])

    # We should be able to whitelist at this point
    auction.transact({'from': whitelister_address}).addToWhitelist([A, B])
    assert auction.call().whitelist(A) == True
    assert auction.call().whitelist(B) == True

    auction.transact({'from': owner}).setup(token.address)

    auction.transact({'from': whitelister_address}).addToWhitelist([D])
    assert auction.call().whitelist(D) == True

    auction.transact({'from': owner}).startAuction()

    # Bid more than bid_threshold should fail for E
    value = bid_threshold + 1
    with pytest.raises(tester.TransactionFailed):
        eth.sendTransaction({
            'from': E,
            'to': auction.address,
            'value': value
        })

    with pytest.raises(tester.TransactionFailed):
        auction.transact({'from': E, "value": value}).bid()

    auction.transact({'from': whitelister_address}).addToWhitelist([E])
    assert auction.call().whitelist(E) == True

    print('--- web3.eth.getBalance(E)-- ', web3.eth.getBalance(E))
    print('--- value                 -- ', value)
    print('--- bids                  -- ', auction.call().bids(E))
    assert web3.eth.getBalance(E) > value

    # Bid more than bid_threshold should be ok for E
    eth.sendTransaction({
        'from': E,
        'to': auction.address,
        'value': value
    })

    auction.transact({'from': A, "value": value}).bid()

    # Test whitelist removal
    auction.transact({'from': B, "value": value}).bid()

    # Only the whitelister_address can add addresses to the whitelist
    with pytest.raises(tester.TransactionFailed):
        auction.transact({'from': owner}).removeFromWhitelist([B])
    with pytest.raises(tester.TransactionFailed):
        auction.transact({'from': wallet_address}).removeFromWhitelist([B])
    with pytest.raises(tester.TransactionFailed):
        auction.transact({'from': A}).removeFromWhitelist([B])
    with pytest.raises(tester.TransactionFailed):
        auction.transact({'from': C}).removeFromWhitelist([B])

    auction.transact({'from': whitelister_address}).removeFromWhitelist([B])
    assert auction.call().whitelist(B) == False

    with pytest.raises(tester.TransactionFailed):
        auction.transact({'from': B, "value": value}).bid()
