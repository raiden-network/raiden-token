from deploy.utils import watch_logs

import logging

log = logging.getLogger(__name__)


class EventSampler:
    def __init__(self, auction_contract_addr, chain):
        self.contract_addr = auction_contract_addr
        self.chain = chain
        Auction = self.chain.provider.get_contract_factory('DutchAuction')
        auction_contract = Auction(address=auction_contract_addr)
        self.auction_contract_addr = auction_contract_addr
        watch_logs(auction_contract, 'BidSubmission', self.on_bid_submission)
        watch_logs(auction_contract, 'AuctionEnded', self.on_auction_end)
        self.events = []

    def last_event(self):
        return self.events[-1]

    def on_bid_submission(self, args):
        log.info(str(args))
        self.events.append(args)

    def on_auction_end(self, args):
        log.info('auction end')
