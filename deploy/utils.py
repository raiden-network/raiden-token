from populus.utils.wait import wait_for_transaction_receipt
from ecdsa import SigningKey, SECP256k1
import sha3
from ethereum.utils import encode_hex


def createWallet():
    keccak = sha3.keccak_256()
    priv = SigningKey.generate(curve=SECP256k1)
    pub = priv.get_verifying_key().to_string()
    keccak.update(pub)
    address = keccak.hexdigest()[24:]
    return (encode_hex(priv.to_string()), address)


def check_succesful_tx(web3, txid, timeout=180) -> dict:

    receipt = wait_for_transaction_receipt(web3, txid, timeout=timeout)
    txinfo = web3.eth.getTransaction(txid)

    # EVM has only one error mode and it's consume all gas
    assert txinfo["gas"] != receipt["gasUsed"]
    return receipt
