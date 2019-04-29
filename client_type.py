#!/usr/bin/env python3
"""
@summary: Which client type do we have? 
          quorum-raft/ibft OR energyweb OR parity OR geth OR ...
"""

import json
import requests  # pip3 install requests

try:
    from web3 import Web3, HTTPProvider  # pip3 install web3
except:
    print("Dependencies unavailable. Start virtualenv first!")
    exit()

# extend sys.path for imports:
if __name__ == '__main__' and __package__ is None:
    from os import sys, path
    sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

from hammer.config import RPCaddress


class Error(Exception):
    pass


class MethodNotExistentError(Error):
    pass


def curl_post(method, txParameters=None, RPCaddress=RPCaddress, ifPrint=False):
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


def clientType(w3):
    """
    get more info about the client
    """
    consensus = "IBFT"
    chainName = "???"
    networkId = -1
    chainId = -1

    try:
        answer = curl_post(method="net_version")
        networkId = int(answer)
    except MethodNotExistentError:
        pass

    nodeString = w3.version.node
    nodeName = nodeString.split("/")[0]
    nodeVersion = nodeString.split("/")[1]

    nodeType = nodeName
    chainId = networkId
    return nodeName, nodeType, nodeVersion, consensus, networkId, chainName, chainId


def run_clientType(w3):
    """
    test the above
    """
    nodeName, nodeType, nodeVersion, consensus, networkId, chainName, chainId = clientType(
        w3)
    txt = "nodeName: %s, nodeType: %s, nodeVersion: %s, consensus: %s, network: %s, chainName: %s, chainId: %s"
    print(txt % (nodeName, nodeType, nodeVersion,
                 consensus, networkId, chainName, chainId))


def web3_connection(RPCaddress):
    w3 = Web3(HTTPProvider(RPCaddress, request_kwargs={'timeout': 120}))
    print("web3 connection established, blockNumber =",
          w3.eth.blockNumber, end=", ")
    print("node version string = ", w3.version.node)
    return w3


if __name__ == '__main__':
    w3 = web3_connection(RPCaddress=RPCaddress)
    run_clientType(w3)
