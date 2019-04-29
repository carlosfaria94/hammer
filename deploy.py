#!/usr/bin/env python3
"""
@summary: deploy contract
"""

import sys
import time
import json
import requests  # pip3 install requests

try:
    from web3 import Web3, HTTPProvider  # pip3 install web3
    from solc import compile_source  # pip install py-solc
except:
    print("Dependencies unavailable. Start virtualenv first!")
    exit()

# extend path for imports:
if __name__ == '__main__' and __package__ is None:
    from os import sys, path
    sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

from hammer.config import RPCaddress, TIMEOUT_DEPLOY
from hammer.config import FILE_CONTRACT_SOURCE, FILE_CONTRACT_ABI, FILE_CONTRACT_ADDRESS
from hammer.config import GAS_FOR_SET_CALL

from hammer.client_tools import web3_connection, unlockAccount


def compile_contract(contract_source_file):
    """
    Reads file, compiles, returns contract name and interface
    """
    with open(contract_source_file, "r") as f:
        contract_source_code = f.read()
    compiled_sol = compile_source(contract_source_code)  # Compiled source code
    contract_interface = compiled_sol['<stdin>:SimpleStorage']
    contract_name = list(compiled_sol.keys())[0]
    return contract_name, contract_interface


def deploy_contract(contract_interface, ifPrint=True, timeout=TIMEOUT_DEPLOY):
    """
    deploys contract, waits for receipt, returns address
    """
    before = time.time()
    # Instantiate and deploy contract
    storage_contract = w3.eth.contract(abi=contract_interface['abi'],
                                       bytecode=contract_interface['bin'])
    # Submit the transaction that deploys the contract
    tx_hash = w3.toHex(storage_contract.constructor().transact())
    print("tx_hash = ", tx_hash,
          "--> waiting for receipt (timeout=%d) ..." % timeout)
    sys.stdout.flush()
    # Wait for the transaction to be mined, and get the transaction receipt
    tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash, timeout=timeout)
    print("Receipt arrived. Took %.1f seconds." % (time.time()-before))

    if ifPrint:
        line = "Deployed. gasUsed={gasUsed} contractAddress={contractAddress}"
        print(line.format(**tx_receipt))
    return tx_receipt.contractAddress


def contract_object(contract_address, abi):
    """
    recreates SimpleStorage contract object when given address on chain, and ABI
    """
    return w3.eth.contract(address=contract_address, abi=abi)


def save_to_disk(contract_address, abi):
    """
    save address & abi, for usage in the other script
    """
    json.dump({"address": contract_address}, open(FILE_CONTRACT_ADDRESS, 'w'))
    json.dump(abi, open(FILE_CONTRACT_ABI, 'w'))


def load_from_disk():
    """
    load address & abi from previous run of 'compile_deploy_save'
    """
    contract_address = json.load(open(FILE_CONTRACT_ADDRESS, 'r'))
    abi = json.load(open(FILE_CONTRACT_ABI, 'r'))
    return contract_address["address"], abi


def compile_deploy_save(contract_source_file):
    """
    compile, deploy, save
    """
    contract_name, contract_interface = compile_contract(contract_source_file)
    print("unlock: ", unlockAccount())
    contract_address = deploy_contract(contract_interface)
    save_to_disk(contract_address, abi=contract_interface["abi"])
    return contract_name, contract_interface, contract_address


def test_smart_contract(storage_contract, gasForSetCall=GAS_FOR_SET_CALL):
    """
    just a test if the storage_contract's methods are working
    --> call getter then setter then getter  
    """

    # get
    first_answer = storage_contract.functions.get().call()
    print('.get(): {}'.format(first_answer))

    # set
    print('.set()')
    param = {'from': w3.eth.defaultAccount,
             'gas': gasForSetCall}
    tx = storage_contract.functions.set(first_answer + 1).transact(param)
    tx_hash = w3.toHex(tx)
    print("transaction", tx_hash, "... ")
    sys.stdout.flush()
    tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
    print("... mined. Receipt --> gasUsed={gasUsed}". format(**tx_receipt))

    # get
    second_answer = storage_contract.functions.get().call()
    print('.get(): {}'.format(second_answer))

    return first_answer, tx_receipt, second_answer


if __name__ == '__main__':
    global w3, NODENAME, NODETYPE, NODEVERSION, CONSENSUS, NETWORKID, CHAINNAME, CHAINID
    w3, chainInfos = web3_connection(RPCaddress=RPCaddress, account=None)
    NODENAME, NODETYPE, NODEVERSION, CONSENSUS, NETWORKID, CHAINNAME, CHAINID = chainInfos

    compile_deploy_save(contract_source_file=FILE_CONTRACT_SOURCE)

    # argument "test" runs the .set() test transaction
    if len(sys.argv) > 1 and sys.argv[1] == "andtests":
        contract_address, abi = load_from_disk()
        contract = contract_object(contract_address, abi)
        test_smart_contract(contract)
