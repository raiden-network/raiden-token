"""
Deploy ContinuousToken on testnet
"""
from populus import Project
from populus.utils.wait import wait_for_transaction_receipt
from web3 import Web3

# base_price, price_factor, owner issuance fraction, owner issuance fraction decimals
mint_args = [10**9, 15, 10, 2]

# price_factor, price_const
auction_args = [2 * 10**12, 10000]

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
    chain_name = "testrpclocal"

    with project.get_chain(chain_name) as chain:
        print('chain', chain)
        # web3 = chain.web3
        web3 = Web3
        print("Web3 provider is", web3.currentProvider)

        Auction = chain.provider.get_contract_factory('Auction')
        Mint = chain.provider.get_contract_factory('Mint')
        Token = chain.provider.get_contract_factory('ContinuousToken')

        web3 = chain.web3
        print("Web3 provider is", web3.currentProvider)

        # The address who will be the owner of the contracts
        beneficiary = web3.eth.coinbase
        assert beneficiary, "Make sure your node has coinbase account created"

        # Deploy Auction
        txhash = Auction.deploy(transaction={"from": beneficiary}, args=auction_args)
        print("Deploying auction, tx hash is", txhash)
        receipt = check_succesful_tx(web3, txhash)
        auction_address = receipt["contractAddress"]
        print("Auction contract address is", auction_address)

        # Deploy Mint
        txhash = Mint.deploy(transaction={"from": beneficiary}, args=mint_args)
        print("Deploying mint, tx hash is", txhash)
        receipt = check_succesful_tx(web3, txhash)
        mint_address = receipt["contractAddress"]
        print("Auction mint address is", mint_address)

        # Deploy token
        txhash = Token.deploy(transaction={"from": beneficiary}, args=[mint_address])
        print("Deploying token, tx hash is", txhash)
        receipt = check_succesful_tx(web3, txhash)
        token_address = receipt["contractAddress"]
        print("Token contract address is", token_address)

        # Make contracts aware of each other
        print("Initializing contracts")
        auction = Auction(address=auction_address)
        mint = Mint(address=mint_address)
        token = Token(address=token_address)

        txhash = mint.transact({"from": beneficiary}).setup(auction_address, token_address)
        check_succesful_tx(web3, txhash)

        txhash = auction.transact({"from": beneficiary}).setup(mint_address)
        check_succesful_tx(web3, txhash)

        # Do some contract reads to see everything looks ok
        print("Token total supply is", token.call().totalSupply())
        print("Mint total supply is", mint.call().issuedSupply())
        print("Auction price is", auction.call().price())

if __name__ == "__main__":
    main()
