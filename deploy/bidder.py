import logging
import random
from deploy.utils import (
    passphrase,
    amount_format,
    check_succesful_tx
)
import gevent

log = logging.getLogger(__name__)


class Bidder:
    approx_bid_txn_cost = 40000

    def __init__(self, web3, auction_contract, address):
        self.web3 = web3
        self.address = address
        self.auction_contract = auction_contract

    def bid(self):
        missing_funds = self.auction_contract.call().missingFundsToEndAuction()
        balance = self.web3.eth.getBalance(self.address)
        max_bid = int(missing_funds * 0.6 * random.random())
        amount = int(max(0, min(balance - self.approx_bid_txn_cost, max_bid)))
        if amount == 0:
            amount = 1
        unlocked = self.web3.personal.unlockAccount(self.address, passphrase)
        assert unlocked is True
        log.info('bidder=%s, missing_funds=%d, balance=%d, amount=%s' %
                 (self.address, missing_funds, balance, amount_format(self.web3, amount)))
        txhash = self.auction_contract.transact({'from': self.address, "value": amount}).bid()
        receipt = check_succesful_tx(self.web3, txhash)
        assert receipt is not None

    def run(self):
        log.info('bidder=%s started' % (self.address))
        balance = self.web3.eth.getBalance(self.address)
        while balance > 0:
            self.bid()
            missing_funds = self.auction_contract.call().missingFundsToEndAuction()
            if missing_funds == 0:
                return
            balance = self.web3.eth.getBalance(self.address)
            gevent.sleep(random.random() * 5)
        log.info('auction ended for {bidder}: not enough minerals'.format(bidder=self.address))
