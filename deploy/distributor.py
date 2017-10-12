"""
Call Distributor with an array of addresses for token claiming after auction ends
"""
from web3.utils.compat import (
    Timeout,
)
from deploy.utils import (
    check_succesful_tx,
    get_expected_tokens
)
from tests.utils_logs import LogFilter
import logging
log = logging.getLogger(__name__)


class Distributor:
    def __init__(self, web3, auction, auction_tx, auction_abi, distributor,
                 batch_number=None, claims_file=None):
        self.web3 = web3
        self.auction = auction
        self.token_multiplier = auction.call().token_multiplier()
        self.auction_abi = auction_abi
        self.distributor = distributor
        self.file = claims_file
        self.auction_ended = False
        self.distribution_ended = False
        self.total_distribute_tx_gas = 4000000

        # How many addresses to send in a transaction
        # If None, will be calculated from the tx gas estimation
        self.batch_number = batch_number

        # Bidder addresses
        self.bidder_addresses = {}

        # Bidder addresses that have not claimed tokens
        self.addresses_unclaimed = []

        # Keep track of distributor claims and verified claims
        self.addresses_claimed = []
        self.verified_claims = []

        # Filters
        self.filter_bids = None
        self.filter_auction_end = None
        self.filter_claims = None
        self.filter_distributed = None

        # Set contract deployment block numbers
        self.auction_block = self.web3.eth.getTransaction(auction_tx)['blockNumber']

        if self.file:
            with open(self.file, 'a') as f:
                f.write('block_number,address,bid_value,received_tokens,expected_tokens,diff\n')

        # Start event watching
        self.watch_auction_bids()

    def watch_auction_bids(self):
        self.filter_bids = self.handle_auction_logs('BidSubmission', self.add_address)
        self.filter_bids.init(self.watch_auction_end)
        self.filter_bids.watch()

    def watch_auction_end(self):
        def set_end(event):
            self.auction_ended = True
            self.final_price = self.auction.call().final_price()

        self.filter_auction_end = self.handle_auction_logs('AuctionEnded', set_end)
        self.filter_auction_end.init(self.watch_auction_claim)
        self.filter_auction_end.watch()

    def watch_auction_claim(self):
        self.filter_claims = self.handle_auction_logs('ClaimedTokens', self.add_verified)
        self.filter_claims.init(self.watch_auction_distributed)
        self.filter_claims.watch()

    def watch_auction_distributed(self):
        def set_distribution_end(event):
            self.distribution_ended = True
            self.filter_bids.stop()
            self.filter_auction_end.stop()

        self.filter_distributed = self.handle_auction_logs('TokensDistributed',
                                                           set_distribution_end)
        self.filter_distributed.init()
        self.filter_distributed.watch()

    def add_address(self, event):
        address = event['args']['_sender']

        # We might have multiple bids from the same bidder
        if address not in self.bidder_addresses:
            self.bidder_addresses[address] = 0
            self.addresses_unclaimed.append(address)

        self.bidder_addresses[address] += event['args']['_amount']

    def add_verified(self, event):
        address = event['args']['_recipient']
        sent_amount = event['args']['_sent_amount']
        expected_tokens = None
        diff_tokens = None

        if address in self.verified_claims:
            log.warning('DOUBLE VERIFIED %s' % (address))
        else:
            self.verified_claims.append(address)

        if address in self.bidder_addresses:
            expected_tokens = get_expected_tokens(
                self.bidder_addresses[address],
                self.token_multiplier, self.final_price)

            if address in self.addresses_unclaimed:
                self.addresses_unclaimed.remove(address)

        # Bidder claimed the tokens himself
        if address not in self.addresses_claimed:
            self.addresses_claimed.append(address)

        if expected_tokens:
            diff_tokens = expected_tokens - sent_amount

        if self.file:
            with open(self.file, 'a') as f:
                f.write('%s,%s,%s,%s,%s,%s\n' % (event['blockNumber'], address,
                                                 self.bidder_addresses[address],
                                                 sent_amount, expected_tokens, diff_tokens))
        else:
            log.info('Verified address %s, diff: %s, sent tokens: %s, expected tokens: %s,'
                     ' bid value: %s)' % (address, diff_tokens, sent_amount,
                                          expected_tokens, self.bidder_addresses[address]))

    def distribution_ended_checks(self):
        log.info('Waiting to make sure we get all ClaimedTokens events')

        with Timeout(300) as timeout:
            while not self.distribution_ended or len(self.addresses_claimed) != \
                    len(self.verified_claims):
                log.info('Distribution ended: %s', str(self.distribution_ended))
                log.info('Claimed %s, verified claims %s' % (len(self.addresses_claimed),
                                                             len(self.verified_claims)))
                timeout.sleep(50)

        assert len(self.addresses_claimed) == len(self.verified_claims)
        self.filter_claims.stop()
        self.filter_distributed.stop()

        log.info('DISTRIBUTION COMPLETE')
        if self.file:
            log.info('The following file has been created: %s', self.file)

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
            while (not self.distribution_ended and
                   (not self.auction_ended or not len(self.addresses_unclaimed))):
                timeout.sleep(2)

        unclaimed_number = len(self.addresses_unclaimed)
        log.info('Auction ended. We should have all the addresses: %s' %
                 (len(self.bidder_addresses.keys())))
        log.info('Unclaimed tokens - addresses: %s' %
                 (unclaimed_number))

        # 87380 gas / claimTokens
        # We need to calculate from gas estimation
        if unclaimed_number > 0 and not self.batch_number:
            valid_bid_address = self.addresses_unclaimed[0]
            claim_tx_gas = self.auction.estimateGas({'from': valid_bid_address}).claimTokens()
            log.info('ESTIMATED claimTokens tx GAS: %s', (claim_tx_gas))

            self.batch_number = self.total_distribute_tx_gas // claim_tx_gas
            log.info('BATCH number: %s', (self.batch_number))

        # Call the distributor contract with batches of bidder addresses
        while len(self.addresses_unclaimed):
            batch_number = min(self.batch_number, len(self.addresses_unclaimed))
            batch = self.addresses_unclaimed[:batch_number]
            self.addresses_unclaimed = self.addresses_unclaimed[batch_number:]
            self.addresses_claimed = self.addresses_claimed + batch

            log.info('Distributing tokens to %s addresses: %s' % (batch_number, ','.join(batch)))
            txhash = self.distributor.transact({
                'gas': self.total_distribute_tx_gas
            }).distribute(batch)

            receipt, success = check_succesful_tx(self.web3, txhash)
            assert success is True
            assert receipt is not None

        self.distribution_ended_checks()
