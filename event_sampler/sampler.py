from deploy.utils import watch_logs
from collections import defaultdict
from operator import itemgetter

import logging

log = logging.getLogger(__name__)
from web3.utils.filters import construct_event_filter_params
from web3.utils.events import get_event_data
from web3.formatters import input_filter_params_formatter, log_array_formatter


class EventSampler:
    def __init__(self, auction_contract_addr, chain):
        self.contract_addr = auction_contract_addr
        self.chain = chain
        Auction = self.chain.provider.get_contract_factory('DutchAuction')
        self.auction_contract = Auction(address=auction_contract_addr)
        self.auction_contract_addr = auction_contract_addr
        callbacks = {
            'BidSubmission': self.on_bid_submission,
            'AuctionEnded': self.on_auction_end,
            'Deployed': self.on_deployed_event,
            'AuctionStarted': self.on_auction_start,
            'ClaimedTokens': self.on_claimed_tokens
        }
        self.events = defaultdict(list)
        self.auction_start_block = None
        self.total_claimed = 0
        self.final_price = None
        self.auction_start_time = None
        self.auction_end_time = None
        self.price_start = None
        self.price_constant = None
        self.price_exponent = None

        for k, v in callbacks.items():
            self.sync_events(k, v)
            watch_logs(self.auction_contract, k, v)

    def sync_events(self, event_name: str, callback):
        events = self.get_logs(event_name)
        if events is None:
            return
        for event in events:
            callback(event)

    def last_event(self):
        if len(self.events) == 0:
            return None
        last_block = max(self.events.keys())
        return sorted(self.events[last_block], key=itemgetter('logIndex'))[0]

    def on_claimed_tokens(self, event):
        self.total_claimed += event['args']['_sent_amount']

    def on_deployed_event(self, event):
        self.price_start = event['args']['_price_start']
        self.price_constant = event['args']['_price_constant']
        self.price_exponent = event['args']['_price_exponent']

    def on_bid_submission(self, args):
        self.events[args['blockNumber']].append(args)

    def on_auction_end(self, event):
        self.final_price = event['args']['_final_price']
        self.auction_end_block = event['blockNumber']
        self.auction_end_time = self.chain.web3.eth.getBlock(event['blockNumber']).timestamp
        log.info('auction ended %s' % (str(event['args'])))

    def on_auction_start(self, event):
        self.auction_start_block = event['args']['_block_number']
        self.auction_start_time = event['args']['_start_time']
        log.info('auction started %s' % (str(event['args'])))

    def get_logs(self, event_name, from_block=0, to_block='latest', filters=None):
        filter_kwargs = {
            'fromBlock': from_block,
            'toBlock': to_block,
            'address': self.contract_addr
        }
        event_abi = [i for i in self.auction_contract.abi
                     if i['type'] == 'event' and i['name'] == event_name][0]
        assert event_abi
        filters = filters if filters else {}
        filter_ = construct_event_filter_params(event_abi, argument_filters=filters,
                                                **filter_kwargs)[1]
        filter_params = input_filter_params_formatter(filter_)
        response = self.chain.web3._requestManager.request_blocking('eth_getLogs', [filter_params])

        logs = log_array_formatter(response)
        logs = [dict(log) for log in logs]
        for log in logs:
            log['args'] = get_event_data(event_abi, log)['args']
        return logs
