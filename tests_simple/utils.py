from eth_utils import (
    keccak,
    is_0x_prefixed,
    decode_hex,
    encode_hex
)


def hash_sign_msg(terms_hash, sender):
    return sol_sha3(terms_hash, sender)


def sol_sha3(*args) -> bytes:
    return keccak(pack(*args))


def pack(*args) -> bytes:
    """
    Simulates Solidity's sha3 packing. Integers can be passed as tuples where the second tuple
    element specifies the variable's size in bits, e.g.:
    sha3((5, 32))
    would be equivalent to Solidity's
    sha3(uint32(5))
    Default size is 256.
    """
    def format_int(value, size):
        assert isinstance(value, int)
        assert isinstance(size, int)
        if value >= 0:
            return decode_hex('{:x}'.format(value).zfill(size // 4))
        else:
            return decode_hex('{:x}'.format((1 << size) + value))

    msg = b''
    for arg in args:
        assert arg
        if isinstance(arg, bytes):
            msg += arg
        elif isinstance(arg, str):
            if is_0x_prefixed(arg):
                msg += decode_hex(arg)
            else:
                msg += arg.encode()
        elif isinstance(arg, int):
            msg += format_int(arg, 256)
        elif isinstance(arg, tuple):
            msg += format_int(arg[0], arg[1])
        else:
            raise ValueError('Unsupported type: {}.'.format(type(arg)))

    return msg


def print_logs(contract, event, name=''):
    transfer_filter_past = contract.pastEvents(event)
    past_events = transfer_filter_past.get()
    if len(past_events):
        print('--(', name, ') past events for ', event, past_events)

    transfer_filter = contract.on(event)
    events = transfer_filter.get()
    if len(events):
        print('--(', name, ') events for ', event, events)

    transfer_filter.watch(lambda x: print('--(', name, ') event ', event, x['args']))


def save_logs(contract, event_name, add):
    transfer_filter_past = contract.pastEvents(event_name)
    past_events = transfer_filter_past.get()
    for event in past_events:
        add(event)

    transfer_filter = contract.on(event_name)

    events = transfer_filter.get()
    for event in events:
        add(event)
    transfer_filter.watch(lambda x: add(x))


def get_gas_used(chain, trxid):
    return chain.wait.for_receipt(trxid)["gasUsed"]


def print_gas_used(chain, trxid, message=None):
    gas_used = get_gas_used(chain, trxid)
    if not message:
        message = trxid

    print('----------------------------------')
    print('GAS USED ' + message, gas_used)
    print('----------------------------------')


def wait(transfer_filter):
    with Timeout(30) as timeout:
        while not transfer_filter.get(False):
            timeout.sleep(2)


# Almost equal
def xassert(a, b, threshold=0.0001):
    if min(a, b) > 0:
        assert abs(a - b) / min(a, b) <= threshold, (a, b)
    assert abs(a - b) <= threshold, (a, b)
    return True
