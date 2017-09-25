"""
Call Distributor with an array of addresses for token claiming after auction ends
"""
from math import ceil
from web3.utils.compat import (
    Timeout,
)
from utils import (
    check_succesful_tx,
    LogFilter,
    # handle_past_logs,
    # watch_logs,
    print_logs
)


class Distributor:
    def __init__(self, web3, auction, auction_tx, auction_abi, distributor, distributor_tx, distributor_abi, batch_number=5):
        self.web3 = web3
        self.auction = auction
        self.auction_tx = auction_tx
        self.auction_abi = auction_abi
        self.distributor = distributor
        self.distributor_tx = distributor_tx
        self.distributor_abi = distributor_abi
        self.auction_ended = False
        self.distribution_ended = False

        # How many addresses to send in a transaction
        self.batch_number = batch_number

        # Bidder addresses that have not claimed tokens
        self.addresses_claimable = []
        # Bid values
        self.values = []

        # Keep track of claimed tokens and verified claims
        self.claimed = []
        self.verified_claims = []

        # Filters
        self.filter_bids = None
        self.filter_auction_end = None
        self.filter_claims = None
        self.filter_distributed = None

        self.owner = self.auction.call().owner()

        # Set contract deployment block numbers
        self.set_block_numbers()

        # Start event watching
        self.watch_auction_bids()
        self.watch_auction_end()
        self.watch_auction_claim()
        self.watch_auction_distributed()

    def set_block_numbers(self):
        self.auction_block = self.web3.eth.getTransaction(self.auction_tx)['blockNumber']
        self.distributor_block = self.web3.eth.getTransaction(self.distributor_tx)['blockNumber']

    def watch_auction_bids(self):
        self.filter_bids = self.handle_auction_logs('BidSubmission', self.add_address)

    def watch_auction_end(self):
        def set_end(event):
            self.auction_ended = True

        self.filter_auction_end = self.handle_auction_logs('AuctionEnded', set_end)

    def watch_auction_claim(self):
        print_logs(self.distributor, 'ClaimTokensCalled', 'Distributor')
        print_logs(self.distributor, 'Distributed', 'Distributor')
        print_logs(self.auction, 'ClaimedTokens', 'DutchAuction')
        # watch_logs(self.auction, 'ClaimedTokens', self.add_verified)

        self.filter_claims = self.handle_auction_logs('ClaimedTokens', self.add_verified)

    def watch_auction_distributed(self):
        def set_distribution_end(event):
            self.distribution_ended = True
            self.filter_bids.stop()
            self.filter_auction_end.stop()
            print('set_distribution_end')

        # watch_logs(self.auction, 'TokensDistributed', set_distribution_end)
        print_logs(self.auction, 'TokensDistributed', 'DutchAuction')
        print_logs(self.auction, 'TradingStarted', 'DutchAuction')

        self.filter_distributed = self.handle_auction_logs('TokensDistributed', set_distribution_end)


    def add_address(self, event):
        address = event['args']['_sender']

        # We might have multiple bids from the same bidder
        if address not in self.addresses_claimable:
            self.addresses_claimable.append(address)
            self.values.append(0)
            index = len(self.addresses_claimable) - 1
        else:
            index = self.addresses_claimable.index(address)

        self.values[index] += event['args']['_amount']

    def add_verified(self, event):
        address = event['args']['_recipient']
        sent_amount = event['args']['_sent_amount']
        print('add_verified', address, sent_amount, address in self.addresses_claimable, self.addresses_claimable)

        if address in self.verified_claims:
            print('--- Double verified !!!', address)
        self.verified_claims.append(address)

        # This bidder has claimed the tokens himself
        if address in self.addresses_claimable:
            self.addresses_claimable.remove(address)

        if address not in self.claimed:
            self.claimed.append(address)

    def distribution_ended_checks(self):
        print('Waiting to make sure we get all ClaimedTokens events')
        with Timeout(180) as timeout:
            while not self.distribution_ended or len(self.claimed) != len(self.verified_claims):
                print('self.distribution_ended', self.distribution_ended)
                print('self.claimed', len(self.claimed), len(self.verified_claims), self.claimed)
                print('self.verified_claims', self.verified_claims)
                timeout.sleep(2)


        assert len(self.claimed) == len(self.verified_claims)
        self.filter_claims.stop()
        self.filter_distributed.stop()

        print('DISTRIBUTION COMPLETE')

    def handle_auction_logs(self, event_name, callback):
        return LogFilter(
            self.web3,
            self.auction_abi,
            self.auction.address,
            event_name,
            self.auction_block,
            'latest', {},
            callback)

    def distribute(self):
        with Timeout() as timeout:
            while not self.distribution_ended and (not self.auction_ended or not len(self.addresses_claimable)):
                timeout.sleep(2)

        print('Auction ended. We should have all the addresses.', len(self.addresses_claimable), self.addresses_claimable)

        # 82495 gas / claimTokens

        # Call the distributor contract with batches of bidder addresses
        while len(self.addresses_claimable):
            batch_number = min(self.batch_number, len(self.addresses_claimable))
            batch = self.addresses_claimable[:batch_number]
            self.addresses_claimable = self.addresses_claimable[batch_number:]
            self.claimed = self.claimed + batch

            print('Distributing tokens to {0} addresses: {1}'.format(batch_number, batch))
            txhash = self.distributor.transact({'from': self.owner, 'gas': 4000000}).distribute(batch)
            receipt = check_succesful_tx(self.web3, txhash)

        self.distribution_ended_checks()
