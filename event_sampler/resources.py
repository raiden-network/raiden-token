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
