from flask_restful import Resource
import logging
import numpy

log = logging.getLogger(__name__)

## {"event": "BidSubmission", "blockNumber": 3607, "blockHash": "0xd0fb1e61d57841984ae470215fcc46bc3f65475d3a25cc1a89726cfeff76644c", "transactionHash": "0x188192b39f695f9b05b1caefc8fdf317bc4fd55f20d8134b13f3f0ce7650e8f5", "transactionIndex": 0, "args": {"_sender": "0x90c647f94ca29a840a6736117d45f768ccf4b69a", "_missing_funds": 80, "_amount": 13}, "logIndex": 0, "address": "0xd1d8649b19ec31680c5ca285cf07b8c0aef0e564"} # noqa


# {
#    auction_stage, // web3 req?
#    final_price, // Only when auction is finished
#    last_balance_at_timestamp, // total ETH raised - total sum of _amount from BidSubmission event
#   histogram:
#    bids: {
#        timestamp,
#        *price, // based on timestamp
#        balance_at_timestamp, // total ETH sent to the auction at timestamp
#        *missing_funds_at_timestamp // based on timestamp and balance_at_timestamp
#    }
#
#    last_timestamp, // last block? - from /last_bid (blockNumber)
#    claimed_tokens // number of claimed tokens at a point in time,
#           after auction ends (optional now) -> from /last_bid (total - _missing_funds)
#    *last_missing_funds_at_timestamp // based on last_timestamp and last_balance_at_timestamp
#           -> from /last_bid  (_missing_funds)
# }


class LastBidSubmission(Resource):
    def __init__(self, sampler):
        super(LastBidSubmission, self).__init__()
        self.sampler = sampler

    def get(self):
        return self.sampler.last_event()


class BidsHistogram(Resource):
    def __init__(self, sampler):
        super(BidsHistogram, self).__init__()
        self.sampler = sampler

    def get(self):
        block_to_events = {}
        for block, events in self.sampler.events.items():
            block_to_events[block] = sum((event['args']['_amount'] for event in events))
        min_block = min(block_to_events.keys())
        max_block = max(block_to_events.keys())
        bins = range(min_block, max_block, ((max_block - min_block) // 10))
        ar, ar_bins = numpy.histogram(list(block_to_events.keys()),
                                      bins=bins,
                                      weights=list(block_to_events.values()))
        return {'y': ar.tolist(), 'x': ar_bins.tolist()}


class AuctionStatus(Resource):
    def __init__(self, auction_contract, sampler):
        super(AuctionStatus, self).__init__()
        self.contract = auction_contract
        self.sampler = sampler

    def get(self):
        ret = {}
        ret['auction_stage'] = self.contract.call().stage()
        block_to_sum = {}
        for block, events in self.sampler.events.items():
            block_to_sum[block] = sum((event['args']['_amount'] for event in events))

        ret['raised_eth'] = sum((v for v in block_to_sum.values()))
        return ret
