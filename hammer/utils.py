#!/usr/bin/env python3
import os
import sys
import json

from web3 import Web3, HTTPProvider
import requests

from hammer.atomic_nonce import AtomicNonce
from hammer.config import MNEMONIC
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


def init_atomic_nonce(w3, address):
    initial_nonce = w3.eth.getTransactionCount(address) - 1
    nonce = AtomicNonce(initial_nonce)
    return nonce


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

        accounts[i] = {
            "private_key": private_key._key.to_hex(),
            "address": address,
            "nonce": init_atomic_nonce(w3, address)
        }
    return accounts
