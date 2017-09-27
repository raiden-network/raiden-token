from flask_restful import Resource
import json
import logging

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
        evs = self.sampler.events
        BINS = 10
        n = len(evs) // BINS
        binned = [evs[i:i + n] for i in range(0, len(evs), n)]
        ret = []
        for bin_group in binned:
            ret.append({'sum': sum([x['args']['_amount'] for x in bin_group])})
        total = sum([ev['args']['_amount'] for ev in evs])

        assert total == sum([b['sum'] for b in ret])
        return ret
