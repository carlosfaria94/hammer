#!/usr/bin/env python3
"""
@summary: deploy a simple storage contract
"""

import sys
import time
import json

try:
    from solc import compile_source  # pip install py-solc
except:
    print("Dependencies unavailable. Start virtualenv first!")
    exit()

# extend path for imports:
if __name__ == '__main__' and __package__ is None:
    from os import sys, path
    sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

from hammer.config import RPC_NODE_SEND, TIMEOUT_DEPLOY, FILE_CONTRACT_SOURCE, FILE_CONTRACT_ABI, FILE_CONTRACT_ADDRESS, GAS, GAS_PRICE, CHAIN_ID
from hammer.utils import init_web3, atomic_nonce


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


def deploy_contract(contract_interface, timeout=TIMEOUT_DEPLOY):
    """
    deploys contract, waits for receipt, returns address
    """
    before = time.time()
    # Instantiate and deploy contract
    storage_contract = w3.eth.contract(abi=contract_interface['abi'],
                                       bytecode=contract_interface['bin'])
    nonce = atomic_nonce(w3)
    contract_tx = storage_contract.constructor().buildTransaction({
        'gas': GAS,
        'gasPrice': GAS_PRICE,
        'nonce': nonce.increment(),
        'chainId': CHAIN_ID
    })
    key = '0xdde94897e9e4f787f6360552a4a723d06b0c730da77c30ce2d4cda61f94e187f'
    signed = w3.eth.account.signTransaction(
        transaction_dict=contract_tx, private_key=key)
    tx_hash = w3.toHex(w3.eth.sendRawTransaction(signed.rawTransaction))

    print("tx_hash = ", tx_hash,
          "--> waiting for receipt (timeout=%d) ..." % timeout)
    sys.stdout.flush()
    # Wait for the transaction to be mined, and get the transaction receipt
    receipt = w3.eth.waitForTransactionReceipt(tx_hash, timeout=timeout)
    print("Receipt arrived. Took %.1f seconds." % (time.time()-before))

    if receipt.status == 1:
        line = "Deployed. Gas Used: {gasUsed}. Contract Address: {contractAddress}"
        print(line.format(**receipt))
    else:
        line = "Deployed failed. Receipt Status: {status}"
        print(line.format(**receipt))
        exit()
    return receipt.contractAddress


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


def init_contract(w3):
    """
    initialise contract object from address, stored in disk file by deploy.py
    """
    contract_address, abi = load_from_disk()
    contract = w3.eth.contract(address=contract_address, abi=abi)
    return contract


def compile_deploy_save(contract_source_file):
    """
    compile, deploy, save
    """
    contract_name, contract_interface = compile_contract(contract_source_file)
    contract_address = deploy_contract(contract_interface)
    save_to_disk(contract_address, abi=contract_interface["abi"])
    return contract_name, contract_interface, contract_address


if __name__ == '__main__':
    global w3
    w3 = init_web3(RPCaddress=RPC_NODE_SEND)
    compile_deploy_save(contract_source_file=FILE_CONTRACT_SOURCE)
