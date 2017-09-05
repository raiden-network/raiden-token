import pytest
from ethereum import tester
from fixtures import (
    create_contract,
    get_token_contract,
    auction_contract,
    token_contract,
    terms_hash,
)

from utils import (
    hash_sign_msg,
)


from web3.utils.compat import (
    Timeout,
)


# Test signing Terms and Consitions
def test_auction_sign(web3, auction_contract, token_contract):
    auction = auction_contract
    token = token_contract(auction.address)
    (A, B) = web3.eth.accounts[2:4]
    A_hash = hash_sign_msg(terms_hash, A)
    B_hash = hash_sign_msg(terms_hash, B)

    assert not auction.call().terms_signed(A)

    # Fail if auction has not started
    with pytest.raises(tester.TransactionFailed):
        auction.transact({'from': A}).sign(A_hash)

    auction.transact().setup(token.address)

    # Fail if auction has not started
    with pytest.raises(tester.TransactionFailed):
        auction.transact({'from': A}).sign(A_hash)

    auction.transact().startAuction()

    # Fail if hash is not correct
    with pytest.raises(tester.TransactionFailed):
        auction.transact({'from': A}).sign(B_hash)

    auction.transact({'from': A}).sign(A_hash)
    assert auction.call().terms_signed(A)


def test_waitfor_last_events_timeout():
    with Timeout(20) as timeout:
        timeout.sleep(2)
