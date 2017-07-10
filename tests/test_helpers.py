from web3.utils.encoding import (
    to_decimal,
)

def create_contract(chain, contract_type, arguments):
    deploy_txn_hash = contract_type.deploy(args=arguments)
    contract_address = chain.wait.for_contract_address(deploy_txn_hash)
    contract = contract_type(address=contract_address)
    return contract

def get_logs(chain, web3, receipt, types):
    logs = []
    for log in receipt['logs']:
        logs.append(decode_params(web3, log['data'], types))
    return logs

# Decode event data - get logged values
# not working with more than 1 event argument
def decode_params(web3, hex_str, types):
    decode = {
        'uint': web3.toDecimal,
        'string': web3.toUtf8,
        'hex': web3.fromAscii,
        'bytes': lambda x: x
    }

    # print('hex_str', hex_str)
    hex_str = hex_str.replace('0x', '')
    params = []
    char_num = int(len(hex_str) / len(types))

    for i in range(0, len(types)):
        m = i * char_num
        n = m + char_num
        param = '0x' + hex_str[m:n]
        decode_function = decode[types[i]]
        decoded = decode_function(param)
        # print('i', i, m, n, param, types[i], decoded)
        params.append(decoded)

    # print('params', params)
    return params
