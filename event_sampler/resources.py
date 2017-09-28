from flask_restful import Resource
import logging
import numpy

log = logging.getLogger(__name__)


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
