import random
from populus.utils.wait import wait_for_transaction_receipt
from ecdsa import SigningKey, SECP256k1
import sha3
import gevent
from ethereum.utils import encode_hex

from web3.formatters import input_filter_params_formatter, log_array_formatter
from web3.utils.events import get_event_data
from web3.utils.filters import construct_event_filter_params
import logging

log = logging.getLogger(__name__)

passphrase = '0'


def amount_format(web3, wei):
    return "{0} WEI = {1} ETH".format(wei, web3.fromWei(wei, 'ether'))


def createWallet():
    keccak = sha3.keccak_256()
    priv = SigningKey.generate(curve=SECP256k1)
    pub = priv.get_verifying_key().to_string()
    keccak.update(pub)
    address = keccak.hexdigest()[24:]
    return (encode_hex(priv.to_string()), address)


def check_succesful_tx(web3, txid, timeout=180) -> dict:

    receipt = wait_for_transaction_receipt(web3, txid, timeout=timeout)
    txinfo = web3.eth.getTransaction(txid)

    # EVM has only one error mode and it's consume all gas
    assert txinfo["gas"] != receipt["gasUsed"]
    return receipt


class LogFilter:
    def __init__(self,
                 web3,
                 abi,
                 address,
                 event_name,
                 from_block=0,
                 to_block='latest',
                 filters=None,
                 callback=None):
        self.web3 = web3
        filter_kwargs = {
            'fromBlock': from_block,
            'toBlock': to_block,
            'address': address
        }
        self.event_abi = [i for i in abi if i['type'] == 'event' and i['name'] == event_name][0]
        assert self.event_abi
        filters = filters if filters else {}
        self.filter = construct_event_filter_params(
            self.event_abi,
            argument_filters=filters,
            **filter_kwargs)[1]
        filter_params = input_filter_params_formatter(self.filter)

        self.filter = web3.eth.filter(filter_params)

        for log in self.get_logs():
            callback(log)

        self.watch_logs(callback)

    def get_logs(self):
        response = self.web3.eth.getFilterLogs(self.filter.filter_id)
        logs = log_array_formatter(response)
        logs = [dict(log) for log in logs]
        for log in logs:
            log = self.set_log_data(log)
        return logs

    def set_log_data(self, log):
        log['args'] = get_event_data(self.event_abi, log)['args']
        return log

    def watch_logs(self, callback):
        def log_callback(log):
            callback(self.set_log_data(log))

        self.filter.watch(log_callback)

    def stop(self):
        self.filter.stop_watching()
        self.web3.eth.uninstallFilter(self.filter.filter_id)


def watch_logs(contract, event, callback, params={}):
    transfer_filter = contract.on(event, params)
    transfer_filter.watch(callback)


def print_logs(contract, event, name=''):
    watch_logs(contract, event, lambda x: log.info('({0}) event {1} {2}'
                                                   .format(name, event, x['args'])))


# We don't need this anymore, as the auction funds go to the owner after all tokens are claimed
# Return funds to owner, so we keep most of the ETH in the simulation
def returnFundsToOwner(web3, owner, bidder):
    # Return most ETH to owner
    value = web3.eth.getBalance(bidder)
    gas_estimate = web3.eth.estimateGas({'from': bidder, 'to': owner, 'value': value}) + 10000
    value -= gas_estimate

    if value < 0:
        return

    # We have to unlock the account first
    unlocked = web3.personal.unlockAccount(bidder, passphrase)
    assert unlocked is True
    txhash = web3.eth.sendTransaction({'from': bidder, 'to': owner, 'value': value})
    receipt = check_succesful_tx(web3, txhash)
    log.info("{bidder} > {owner} {0}"
             .format(amount_format(web3, value), bidder=bidder, owner=owner))
    assert receipt is not None


def sendFunds(web3, owner, bidder, max_bid):
        value = random.randint(max_bid / 2, max_bid)
        log.info("funding {bidder} {0}".format(amount_format(web3, value), bidder=bidder))
        txhash = web3.eth.sendTransaction({'from': owner, 'to': bidder, 'value': value})
        check_succesful_tx(web3, txhash)


def assignFundsToBidders(web3, owner: str, bidders: list, distribution_limit: int=None):
    # Make sure bidders have random ETH
    owner_balance = web3.eth.getBalance(owner)
    if distribution_limit is not None:
        owner_balance = min(owner_balance, distribution_limit)
    max_bidder_deposit = int(owner_balance / len(bidders))
#    max_bid = max(max_bidder_deposit, 10**18 * 5)
    max_bid = max_bidder_deposit
    gevents = []
    for bidder in bidders:
        gevents.append(gevent.spawn(sendFunds, web3, owner, bidder, max_bid))
    gevent.joinall(gevents)


def set_connection_pool_size(web3, pool_connections, pool_size):
    """Hack to override default poolsize for web3"""
    from web3.utils.compat.compat_requests import _get_session
    from web3 import HTTPProvider
    import requests
    provider = web3.currentProvider
    if isinstance(provider, HTTPProvider) is False:
        return
    logging.info("setting web3 HTTPProvider connections={0} pool_size={1}"
                 .format(pool_connections, pool_size))
    session = _get_session(provider.endpoint_uri)
    adapter = requests.adapters.HTTPAdapter(pool_connections, pool_size)
    session.mount('http://', adapter)
