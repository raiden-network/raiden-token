from deploy.utils import watch_logs

import logging

log = logging.getLogger(__name__)
from web3.utils.filters import construct_event_filter_params
from web3.utils.events import get_event_data
from web3.formatters import input_filter_params_formatter, log_array_formatter


def get_logs(web3, address, abi, event_name, from_block=0, to_block='latest', filters=None):
    filter_kwargs = {
        'fromBlock': from_block,
        'toBlock': to_block,
        'address': address
    }
    event_abi = [i for i in abi if i['type'] == 'event' and i['name'] == event_name][0]
    assert event_abi
    filters = filters if filters else {}
    filter_ = construct_event_filter_params(event_abi, argument_filters=filters,
                                            **filter_kwargs)[1]
    filter_params = input_filter_params_formatter(filter_)
    response = web3._requestManager.request_blocking('eth_getLogs', [filter_params])

    logs = log_array_formatter(response)
    logs = [dict(log) for log in logs]
    for log in logs:
        log['args'] = get_event_data(event_abi, log)['args']
    return logs


class EventSampler:
    def __init__(self, auction_contract_addr, chain):
        self.contract_addr = auction_contract_addr
        self.chain = chain
        Auction = self.chain.provider.get_contract_factory('DutchAuction')
        self.auction_contract = Auction(address=auction_contract_addr)
        self.auction_contract_addr = auction_contract_addr
        watch_logs(self.auction_contract, 'BidSubmission', self.on_bid_submission)
        watch_logs(self.auction_contract, 'AuctionEnded', self.on_auction_end)
        self.events = []
        self.sync_all()

    def sync_all(self):
        self.events = get_logs(
            self.chain.web3, self.contract_addr, self.auction_contract.abi, 'BidSubmission')
        log.info("synced %d events" % len(self.events))

    def last_event(self):
        return self.events[-1]

    def events(self):
        return self.events

    def on_bid_submission(self, args):
        log.info(str(args))
        self.events.append(args)

    def on_auction_end(self, args):
        log.info('auction end')
