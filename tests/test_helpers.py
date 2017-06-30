def create_contract(chain, contract_type, arguments):
    deploy_txn_hash = contract_type.deploy(args=arguments)
    contract_address = chain.wait.for_contract_address(deploy_txn_hash)
    contract = contract_type(address=contract_address)
    return contract
