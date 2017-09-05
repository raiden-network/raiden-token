# get events from logs
# keep an array with bidders
# event - auction ends -> start script

'''

on claimTokens: we need a contract which can be called with a list of addresses and calls claimTokens for each address.
we then use this contract to claim multiple accounts at once with a single txs.
we need to check, how much gas is used per claimTokens, i assume approx. 30K. so this would mean, that we can claim approx. 100 accounts per call. if there are 10k participants, we need to trigger ~100 transactions. as we ` require(bids[receiver] > 0)` and anyone could have claimed there tokens in the meanwhile, we need to sample the set of all unclaimed tokens before every tx. we need a script for getting the list of unclaimed addresses and creating/sending the txs to above contract

we need to know the gas_cost for a standard claim as well as for a transferReserve claim

you can also check that the money was returned by checking sender.balance after the call.


'''

"""
Call Distributor with an array of addresses for token claiming after auction ends
"""
from populus import Project
from populus.utils.wait import wait_for_transaction_receipt
from web3 import Web3

import json
with open('build/contracts.json') as json_data:
    abis = json.load(json_data)


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
    # chain_name = "testrpc"
    # chain_name = "tester"
    auction_address = ''
    token_address = ''

    with project.get_chain(chain_name) as chain:
        #Auction =
        print('Web3', Web3)
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
