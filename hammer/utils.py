#!/usr/bin/env python3
import os
import sys
import json

from web3 import Web3, HTTPProvider
import requests

# extend path for imports:
if __name__ == '__main__' and __package__ is None:
    from os import sys, path
    sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

from crypto import HDPrivateKey, HDKey
from config import MNEMONIC, GAS, GAS_PRICE, CHAIN_ID, ERC20_ADDRESS, ERC20_ABI
from atomic_nonce import AtomicNonce

class Error(Exception):
    pass


class MethodNotExistentError(Error):
    pass


def print_versions():
    from web3 import __version__ as web3version
    print("versions: web3 %s, python %s" % (web3version, sys.version.replace("\n", "")))


def init_web3(RPCaddress=None):
    w3 = Web3(HTTPProvider(RPCaddress, request_kwargs={'timeout': 120}))
    from web3.middleware import geth_poa_middleware
    w3.middleware_stack.inject(geth_poa_middleware, layer=0)

    print_versions()
    print("web3 connection established, blockNumber =",
          w3.eth.blockNumber, end=", ")
    print("node version string = ", w3.version.node)
    return w3


def curl_post(method, txParameters=None, RPCaddress=None, ifPrint=False):
    """
    call Ethereum RPC functions
    """
    payload = {"jsonrpc": "2.0",
               "method": method,
               "id": 1}
    if txParameters:
        payload["params"] = [txParameters]
    headers = {'Content-type': 'application/json'}
    response = requests.post(RPCaddress, json=payload, headers=headers)
    response_json = response.json()

    if ifPrint:
        print('raw json response: {}'.format(response_json))

    if "error" in response_json:
        raise MethodNotExistentError()
    else:
        return response_json['result']


def file_date(file):
    try:
        when = os.path.getmtime(file)
    except FileNotFoundError:
        when = 0
    return when


def init_accounts(w3, how_many):
    master_key = HDPrivateKey.master_key_from_mnemonic(MNEMONIC)
    root_keys = HDKey.from_path(master_key, "m/44'/60'/0'")
    acct_priv_key = root_keys[-1]
    accounts = {}
    for i in range(how_many):
        keys = HDKey.from_path(
            acct_priv_key, '{change}/{index}'.format(change=0, index=i))
        private_key = keys[-1]
        public_key = private_key.public_key
        address = private_key.public_key.address()
        address = w3.toChecksumAddress(address)
        initial_nonce = AtomicNonce(w3, address)

        accounts[i] = {
            "private_key": private_key._key.to_hex(),
            "address": address,
            "nonce": initial_nonce
        }
    return accounts

def has_balance(w3, account):
    balance = w3.eth.getBalance(account["address"])
    balance = w3.fromWei(balance, 'ether')
    if balance >= 1:
        return True
    else:
        return False

def transfer_funds(w3, sender, receiver, amount):
    if not has_balance(w3, receiver):
        amount = w3.toWei(amount, 'ether')
        tx = {
            'to': receiver["address"],
            'value': amount,
            'gas': GAS,
            'gasPrice': GAS_PRICE,
            'nonce': sender["nonce"].increment(w3),
            'chainId': CHAIN_ID
        }
        signed = w3.eth.account.signTransaction(tx, sender["private_key"])
        tx_hash = w3.toHex(w3.eth.sendRawTransaction(signed.rawTransaction))

def transfer_erc(w3, sender, receiver, amount=10000):
    _, abi, _ = load_contract(file_address=None, file_abi=ERC20_ABI, file_bin=None)
    erc20 = w3.eth.contract(address=ERC20_ADDRESS, abi=abi)

    transfer_erc20 = erc20.functions.transfer(to=receiver["address"], value=amount).buildTransaction({
        'gas': GAS,
        'gasPrice': GAS_PRICE,
        'nonce': sender["nonce"].increment(w3),
        'chainId': CHAIN_ID
    })

    signed = w3.eth.account.signTransaction(transfer_erc20, sender["private_key"])
    tx_hash = w3.toHex(w3.eth.sendRawTransaction(signed.rawTransaction))

def load_contract(file_abi, file_address=None, file_bin=None):
    """
    Load contract from disk. Returns: address, ABI and Bin from the contract
    """
    if file_address is not None:
        try:
            contract_address = json.load(open(file_address, 'r'))["address"]
        except FileNotFoundError:
            contract_address = None
    else:
        contract_address = None
    abi = json.load(open(file_abi, 'r'))
    if file_bin is not None:
        contract_bin = json.load(open(file_bin, 'r'))["bin"]
    else:
        contract_bin = None

    return contract_address, abi, contract_bin
