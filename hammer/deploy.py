#!/usr/bin/env python3
"""
@summary: deploy a simple storage contract
"""
import sys
import time
import json

# extend path for imports:
if __name__ == '__main__' and __package__ is None:
    from os import sys, path
    sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

from hammer.utils import init_web3, init_accounts
from hammer.config import RPC_NODE_SEND, TIMEOUT_DEPLOY, FILE_CONTRACT_ABI, FILE_CONTRACT_BIN, FILE_CONTRACT_ADDRESS, GAS, GAS_PRICE, CHAIN_ID


def deploy(account, timeout=TIMEOUT_DEPLOY):
    """
    deploys contract, waits for receipt, returns address
    """
    before = time.time()
    _, abi, contract_bin = load_contract()
    storage_contract = w3.eth.contract(abi=abi, bytecode=contract_bin)
    contract_tx = storage_contract.constructor().buildTransaction({
        'gas': GAS,
        'gasPrice': GAS_PRICE,
        'nonce': account["nonce"].increment(w3),
        'chainId': CHAIN_ID
    })
    signed = w3.eth.account.signTransaction(contract_tx, account["private_key"])
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
        save_address(receipt.contractAddress)
        return
    else:
        line = "Deployed failed. Receipt Status: {status}"
        print(line.format(**receipt))
        exit()


def contract_object(contract_address, abi):
    """
    recreates SimpleStorage contract object when given address on chain, and ABI
    """
    return w3.eth.contract(address=contract_address, abi=abi)


def save_address(contract_address):
    """
    Save contract address, to use on measure_tps.py
    """
    json.dump({"address": contract_address}, open(FILE_CONTRACT_ADDRESS, 'w'))


def load_contract(
    file_address=FILE_CONTRACT_ADDRESS, file_abi=FILE_CONTRACT_ABI, file_bin=FILE_CONTRACT_BIN):
    """
    Load contract from disk. Returns: address, ABI and Bin from the contract
    """
    try:
        contract_address = json.load(open(file_address, 'r'))
    except FileNotFoundError:
        contract_address = None
    abi = json.load(open(file_abi, 'r'))
    contract_bin = json.load(open(file_bin, 'r'))
    return contract_address["address"], abi, contract_bin["bin"]


def init_contract(w3):
    """
    initialise contract object from address, stored in disk file by deploy.py
    """
    contract_address, abi, _ = load_contract()
    contract = w3.eth.contract(address=contract_address, abi=abi)
    return contract

if __name__ == '__main__':
    global w3
    w3 = init_web3(RPCaddress=RPC_NODE_SEND)
    # Init the first account to deploy contract
    account = init_accounts(w3, 1).get(0)
    deploy(account)
