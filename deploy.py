"""
Deploy ContinuousToken on testnet
"""
from populus import Project
from populus.utils.wait import wait_for_transaction_receipt
from web3 import Web3
from tests_simple.test_fixtures import (
    auction_args,
    initial_supply,
    prealloc
)


def check_succesful_tx(web3: Web3, txid: str, timeout=180) -> dict:

    receipt = wait_for_transaction_receipt(web3, txid, timeout=timeout)
    txinfo = web3.eth.getTransaction(txid)

    # EVM has only one error mode and it's consume all gas
    assert txinfo["gas"] != receipt["gasUsed"]
    return receipt


def main():

    project = Project()

    # This is configured in populus.json
    # We are working on a testnet
    chain_name = "ropsten"
    chain_name = "testrpc"
    # chain_name = "tester"

    with project.get_chain(chain_name) as chain:

        # Load Populus contract proxy classes
        Auction = chain.provider.get_contract_factory('DutchAuction')
        Token = chain.provider.get_contract_factory('ReserveToken')

        web3 = chain.web3
        print("Web3 provider is", web3.currentProvider)

        # The address who will be the owner of the contracts
        beneficiary = web3.eth.coinbase
        owners = web3.eth.accounts[:2]
        assert beneficiary, "Make sure your node has coinbase account created"

        # Deploy Auction
        txhash = Auction.deploy(transaction={"from": beneficiary}, args=auction_args[0])
        print("Deploying auction, tx hash is", txhash)
        receipt = check_succesful_tx(web3, txhash)
        auction_address = receipt["contractAddress"]
        print("Auction contract address is", auction_address)

        # Deploy token
        txhash = Token.deploy(transaction={"from": beneficiary}, args=[
            auction_address,
            initial_supply,
            owners,
            prealloc
        ])
        print("Deploying token, tx hash is", txhash)
        receipt = check_succesful_tx(web3, txhash)
        token_address = receipt["contractAddress"]
        print("Token contract address is", token_address)

        # Make contracts aware of each other
        print("Initializing contracts")
        auction = Auction(address=auction_address)
        token = Token(address=token_address)

        txhash = auction.transact({"from": beneficiary}).setup(token_address)
        check_succesful_tx(web3, txhash)

        # Do some contract reads to see everything looks ok
        print("Token total supply is", token.call().totalSupply())
        print("Auction price is", auction.call().price())


if __name__ == "__main__":
    main()
