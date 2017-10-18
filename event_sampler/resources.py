from flask_restful import Resource, reqparse
import logging
import numpy
import ethereum

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


class AuctionStatus(Resource):
    def __init__(self, auction_contract, sampler):
        super(AuctionStatus, self).__init__()
        self.contract = auction_contract
        self.sampler = sampler

    def get_histogram(self):
        if len(self.sampler.events.items()) == 0:
            return None
        parser = reqparse.RequestParser()
        parser.add_argument('bins', help='bins in the histogram', default=20, type=int)
        args = parser.parse_args()
        block_to_events = {}
        for block, events in self.sampler.events.items():
            block_to_events[block] = sum((event['args']['_amount'] for event in events))
        min_block = min(block_to_events.keys())
        max_block = max(block_to_events.keys())
        num_bins = args['bins']
#        assert max_block > min_block
        num_bins = max(min(max_block - min_block, num_bins), 1)
#        bins = range(min_block, max_block, ((max_block - min_block) // num_bins))
        ar, ar_bins = numpy.histogram(list(block_to_events.keys()),
                                      bins=num_bins,
                                      weights=[numpy.float64(x) for x in block_to_events.values()])
        bin_timestamps = []
        for block_id in ar_bins.tolist():
            block_id = int(block_id)
            timestamp = self.sampler.state.block_to_timestamp.get(block_id, None)
            if timestamp is None:
                timestamp = self.sampler.chain.web3.eth.getBlock(block_id)['timestamp']
                self.sampler.state.block_to_timestamp[block_id] = timestamp
            bin_timestamps.append(timestamp)
#        bin_timestamps = [self.sampler.block_to_timestamp[int(block_id)]
#                          for block_id in ar_bins.tolist()]
        return {'timestamped_bins': bin_timestamps,
                'block_bins': bin_timestamps,
                'bin_sum': ar.tolist(),
                'bin_cumulative_sum': numpy.cumsum(ar).tolist()}

    def get_status(self):
        last_event = self.sampler.last_event()
        web3 = self.sampler.chain.web3
        ret = {}
        ret['auction_stage'] = self.contract.call().stage()
        ret['price'] = self.contract.call().price()
        block_to_sum = {}
        for block, events in self.sampler.events.items():
            block_to_sum[block] = sum((event['args']['_amount'] for event in events))

        ret['raised_eth'] = sum((v for v in block_to_sum.values()))
        ret['final_price'] = self.sampler.final_price
        ret['claimed_tokens'] = self.sampler.total_claimed
        if last_event is not None:
            ret['timestamp'] = web3.eth.getBlock(last_event['blockNumber'])['timestamp']
        else:
            ret['timestamp'] = None
        ret['start_time'] = self.sampler.auction_start_time
        ret['end_time'] = self.sampler.auction_end_time
        ret['price_start'] = self.sampler.price_start
        ret['price_constant'] = self.sampler.price_constant
        ret['price_exponent'] = self.sampler.price_exponent
        if ret['auction_stage'] >= 2:
            checksummed_addr = ethereum.utils.add_cool_checksum(self.contract.address)
            ret['auction_contract_address'] = checksummed_addr
        return ret

    def get(self):
        ret = {}
        ret['histogram'] = self.get_histogram()
        ret['status'] = self.get_status()
        return ret
