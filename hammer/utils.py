#!/usr/bin/env python3
import os
import sys
import json

from web3 import Web3, HTTPProvider
import requests

from hammer.atomic_nonce import AtomicNonce
from hammer.config import MNEMONIC, GAS, GAS_PRICE, CHAIN_ID
from hammer.crypto import HDPrivateKey, HDKey


class Error(Exception):
    pass


class MethodNotExistentError(Error):
    pass


def print_versions():
    from web3 import __version__ as web3version
    from solc import get_solc_version

    import pkg_resources
    pysolcversion = pkg_resources.get_distribution("py-solc").version

    print("versions: web3 %s, py-solc: %s, solc %s, python %s" % (web3version,
                                                                  pysolcversion, get_solc_version(), sys.version.replace("\n", "")))


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


def read(file):
    with open(file, "r") as f:
        data = json.load(f)
    return data


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


def transfer_funds(w3, sender, receiver, amount):
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

    # Wait for the transaction to be mined, and get the transaction receipt
    receipt = w3.eth.waitForTransactionReceipt(tx_hash)
    if receipt.status == 1:
        print("> Sent %d ETH to %s (tx hash: %s)" %
              (amount, receiver["address"], tx_hash))
    else:
        print("> Tx failed when sending %d ETH to %s" %
              (amount, receiver["address"]))
        exit()
    return tx_hash
