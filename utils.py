#!/usr/bin/env python3
import os
import sys

try:
    from web3 import Web3, HTTPProvider  # pip3 install web3
except:
    print("Dependencies unavailable. Start virtualenv first!")
    exit()

# extend sys.path for imports:
if __name__ == '__main__' and __package__ is None:
    from os import sys, path
    sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

from hammer.config import FILE_PASSPHRASE


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


def web3_connection(RPCaddress=None):
    print_versions()
    w3 = Web3(HTTPProvider(RPCaddress, request_kwargs={'timeout': 120}))
    print("web3 connection established, blockNumber =",
          w3.eth.blockNumber, end=", ")
    print("node version string = ", w3.version.node)
    return w3


def get_block_transaction_count(w3, blockNumber):
    """
    testRPC does not provide this endpoint yet, so replicate its functionality:
    """
    block = w3.eth.getBlock(blockNumber)
    return len(block["transactions"])


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


if __name__ == '__main__':
    global w3
    w3 = web3_connection(RPCaddress=None)
