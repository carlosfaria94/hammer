#!/usr/bin/env python3
"""
@summary: waits until (the first node in) a network is reachable
"""

# extend sys.path for imports:
if __name__ == '__main__' and __package__ is None:
    from os import sys, path
    sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

# standard library:
import time

import requests

import hammer
from hammer.config import RPCaddress
from hammer.client_type import curl_post


def call_port(RPCaddress=RPCaddress):
    """
    Just calls empty GET on RPCaddress, checks whether status_code==200 
    """
    headers = headers = {'Content-type': 'application/json'}
    try:
        # GET does not work on parity instantseal
        response = requests.post(RPCaddress, headers=headers)
    except requests.exceptions.ConnectionError:
        success, error = False, 'ConnectionError'
    else:
        success, error = True, None
        # print ("response.status_code =", response.status_code)
        if response.status_code != 200:
            success, error = False, "response.status_code = %d" % response.status_code
        # print ("response.text =", response.text)

    return success, error


def simple_RPC_call(RPCaddress=RPCaddress, method="web3_clientVersion"):
    """
    calls simplemost RPC call 'web3_clientVersion' and checks answer.
    returns (BOOL success, STRING/None error) 
    """
    try:
        answer = curl_post(method, RPCaddress=RPCaddress, ifPrint=True)
    except requests.exceptions.ConnectionError:
        success, error = False, "ConnectionError"
    except hammer.client_type.MethodNotExistentError:
        success, error = False, "MethodNotExistentError"
    else:
        try:
            nodeName = answer.split("/")[0]
            print('Node name:', nodeName)
            success, error = True, None
        except Exception as e:
            success, error = False, "Exception: (%s) %s" % (type(e), e)

    return success, error


def loop_until_is_up(seconds_between_calls=0.5, ifPrint=False, timeout=20):
    """
    endless loop, until RPC API call answers something
    """
    start = time.monotonic()

    while True:
        success, error = simple_RPC_call()
        if ifPrint:
            print(success, error)
        if success:
            break
        if timeout:
            if time.monotonic() - start > timeout:
                break
        time.sleep(seconds_between_calls)

    return success


if __name__ == '__main__':
    loop_until_is_up(ifPrint=True)
