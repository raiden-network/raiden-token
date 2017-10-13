import pytest
from ethereum import tester
from eth_utils import (
    function_signature_to_4byte_selector,
)
from utils import (
    TransactionIdKeeper
)
from fixtures import (
    owner_index,
    owner,
    wallet_address,
    whitelister_address,
    get_bidders,
    gnosis_multisig_wallet,
    foundation_multisig_wallet,
    contract_params,
    create_contract,
    get_token_contract,
    token_contract,
    auction_contract,
    auction_contract_fast_decline,
    create_accounts,
    txnCost,
    event_handler
)


def test_auction_bid_from_gnosis_multisig(
    web3,
    owner,
    wallet_address,
    gnosis_multisig_wallet,
    get_bidders,
    auction_contract_fast_decline,
    token_contract,
    event_handler):
    eth = web3.eth
    auction = auction_contract_fast_decline
    (A, B, C) = get_bidders(3)

    # Initialize token
    token = token_contract(auction.address)
    auction.transact({'from': owner}).setup(token.address)
    auction.transact({'from': owner}).startAuction()

    gnosis_wallet1 = gnosis_multisig_wallet([A, B, C], 1)
    gnosis_wallet2 = gnosis_multisig_wallet([A, B, C], 2)

    gnosis_wallet1_balance = 100000
    gnosis_wallet2_balance = 200000

    web3.eth.sendTransaction({
        'from': B,
        'to': gnosis_wallet1.address,
        'value': gnosis_wallet1_balance
    })
    web3.eth.sendTransaction({
        'from': B,
        'to': gnosis_wallet2.address,
        'value': gnosis_wallet2_balance
    })

    # Test gnosis wallet with 2 owners and 1 confirmation
    # Using Auction's fallback function
    pre_balance_wallet = web3.eth.getBalance(wallet_address)
    gnosis_wallet1.transact({'from': A}).submitTransaction(auction.address, 1000, bytearray())

    gnosis_wallet1_balance -= 1000
    assert web3.eth.getBalance(gnosis_wallet1.address) == gnosis_wallet1_balance
    assert auction.call().bids(gnosis_wallet1.address) == 1000
    assert web3.eth.getBalance(wallet_address) == pre_balance_wallet + 1000

    # Test gnosis wallet with 2 owners and 1 confirmation
    # Using Auction's bid() function
    pre_balance_wallet = web3.eth.getBalance(wallet_address)
    data = function_signature_to_4byte_selector('bid()')
    gnosis_wallet1.transact({'from': A}).submitTransaction(auction.address, 1000, data)

    gnosis_wallet1_balance -= 1000
    assert web3.eth.getBalance(gnosis_wallet1.address) == gnosis_wallet1_balance
    assert auction.call().bids(gnosis_wallet1.address) == 2000
    assert web3.eth.getBalance(wallet_address) == pre_balance_wallet + 1000

    transaction_id_keeper = TransactionIdKeeper()

    # Test gnosis wallet with 3 owners and 2 confirmations
    # Using Auction's fallback function
    pre_balance_wallet = web3.eth.getBalance(wallet_address)
    txhash = gnosis_wallet2.transact({'from': A}).submitTransaction(auction.address, 3000, bytearray())
    assert web3.eth.getBalance(gnosis_wallet2.address) == gnosis_wallet2_balance
    assert auction.call().bids(gnosis_wallet2.address) == 0
    assert web3.eth.getBalance(wallet_address) == pre_balance_wallet

    # Wait for transactionId from the Confirmation event
    ev_handler = event_handler(gnosis_wallet2)
    ev_handler.add(txhash, 'Confirmation', transaction_id_keeper.add)
    ev_handler.check()

    # Second owner confirms the transaction
    transaction_id = transaction_id_keeper.transaction_id
    gnosis_wallet2.transact({'from': B}).confirmTransaction(transaction_id)
    gnosis_wallet2_balance -= 3000
    assert web3.eth.getBalance(gnosis_wallet2.address) == gnosis_wallet2_balance
    assert auction.call().bids(gnosis_wallet2.address) == 3000
    assert web3.eth.getBalance(wallet_address) == pre_balance_wallet + 3000

    # Test gnosis wallet with 3 owners and 2 confirmations
    # Using Auction's bid() function
    pre_balance_wallet = web3.eth.getBalance(wallet_address)
    data = function_signature_to_4byte_selector('bid()')
    txhash1 = gnosis_wallet2.transact({'from': A}).submitTransaction(auction.address, 3000, data)

    # Second owner confirms the transaction
    ev_handler.add(txhash1, 'Confirmation', transaction_id_keeper.add)
    ev_handler.check()
    transaction_id = transaction_id_keeper.transaction_id
    gnosis_wallet2.transact({'from': B}).confirmTransaction(transaction_id)

    gnosis_wallet2_balance -= 3000
    assert web3.eth.getBalance(gnosis_wallet2.address) == gnosis_wallet2_balance
    assert auction.call().bids(gnosis_wallet2.address) == 6000
    assert web3.eth.getBalance(wallet_address) == pre_balance_wallet + 3000


def test_auction_bid_from_foundation_multisig(
    web3,
    owner,
    wallet_address,
    foundation_multisig_wallet,
    get_bidders,
    auction_contract_fast_decline,
    token_contract,
    event_handler):
    eth = web3.eth
    auction = auction_contract_fast_decline
    (A, B, C) = get_bidders(3)

    # Initialize token
    token = token_contract(auction.address)
    auction.transact({'from': owner}).setup(token.address)
    auction.transact({'from': owner}).startAuction()

    foundation_wallet1 = foundation_multisig_wallet([A, B, C], 1, 10000)
    foundation_wallet2 = foundation_multisig_wallet([A, B, C], 2, 100)

    foundation_wallet1_balance = 100000
    foundation_wallet2_balance = 200000

    web3.eth.sendTransaction({
        'from': A,
        'to': foundation_wallet1.address,
        'value': foundation_wallet1_balance
    })
    web3.eth.sendTransaction({
        'from': B,
        'to': foundation_wallet2.address,
        'value': foundation_wallet2_balance
    })

    # Test gnosis wallet with 2 owners and 1 confirmation
    # Using Auction's fallback function
    pre_balance_wallet = web3.eth.getBalance(wallet_address)
    foundation_wallet1.transact({'from': A}).execute(auction.address, 1000, bytearray())

    foundation_wallet1_balance -= 1000
    assert web3.eth.getBalance(foundation_wallet1.address) == foundation_wallet1_balance
    assert auction.call().bids(foundation_wallet1.address) == 1000
    assert web3.eth.getBalance(wallet_address) == pre_balance_wallet + 1000

    # Test gnosis wallet with 2 owners and 1 confirmation
    # Using Auction's bid() function
    pre_balance_wallet = web3.eth.getBalance(wallet_address)
    data = function_signature_to_4byte_selector('bid()')
    foundation_wallet1.transact({'from': A}).execute(auction.address, 1000, data)

    foundation_wallet1_balance -= 1000
    assert web3.eth.getBalance(foundation_wallet1.address) == foundation_wallet1_balance
    assert auction.call().bids(foundation_wallet1.address) == 2000
    assert web3.eth.getBalance(wallet_address) == pre_balance_wallet + 1000

    transaction_id_keeper = TransactionIdKeeper('operation')

    # Test gnosis wallet with 3 owners and 2 confirmations
    # Using Auction's fallback function
    pre_balance_wallet = web3.eth.getBalance(wallet_address)
    txhash = foundation_wallet2.transact({'from': A}).execute(auction.address, 3000, bytearray())
    assert web3.eth.getBalance(foundation_wallet2.address) == foundation_wallet2_balance
    assert auction.call().bids(foundation_wallet2.address) == 0
    assert web3.eth.getBalance(wallet_address) == pre_balance_wallet

    # Wait for transactionId from the Confirmation event
    ev_handler = event_handler(foundation_wallet2)
    ev_handler.add(txhash, 'Confirmation', transaction_id_keeper.add)
    ev_handler.check()

    # Second owner confirms the transaction
    transaction_id = transaction_id_keeper.transaction_id
    foundation_wallet2.transact({'from': B}).confirm(transaction_id)
    foundation_wallet2_balance -= 3000
    assert web3.eth.getBalance(foundation_wallet2.address) == foundation_wallet2_balance
    assert auction.call().bids(foundation_wallet2.address) == 3000
    assert web3.eth.getBalance(wallet_address) == pre_balance_wallet + 3000

    # Test gnosis wallet with 3 owners and 2 confirmations
    # Using Auction's bid() function
    pre_balance_wallet = web3.eth.getBalance(wallet_address)
    data = function_signature_to_4byte_selector('bid()')
    txhash1 = foundation_wallet2.transact({'from': A}).execute(auction.address, 3000, data)

    # Second owner confirms the transaction
    ev_handler.add(txhash1, 'Confirmation', transaction_id_keeper.add)
    ev_handler.check()
    transaction_id = transaction_id_keeper.transaction_id
    foundation_wallet2.transact({'from': B}).confirm(transaction_id)

    foundation_wallet2_balance -= 3000
    assert web3.eth.getBalance(foundation_wallet2.address) == foundation_wallet2_balance
    assert auction.call().bids(foundation_wallet2.address) == 6000
    assert web3.eth.getBalance(wallet_address) == pre_balance_wallet + 3000
