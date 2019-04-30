#!/usr/bin/env python3
"""
@summary: waits until (the first node in) a network is reachable
"""

# extend sys.path for imports:
if __name__ == '__main__' and __package__ is None:
    from os import sys, path
    sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

import time

from requests import ConnectionError

from hammer.config import RPC_NODE_SEND
from hammer.utils import curl_post, MethodNotExistentError


def simple_RPC_call(RPCaddress=RPC_NODE_SEND, method="web3_clientVersion"):
    """
    calls simplemost RPC call 'web3_clientVersion' and checks answer.
    returns (BOOL success, STRING/None error) 
    """
    try:
        answer = curl_post(method, RPCaddress=RPCaddress, ifPrint=True)
    except ConnectionError:
        success, error = False, "ConnectionError"
    except MethodNotExistentError:
        success, error = False, "MethodNotExistentError"
    else:
        try:
            node_name = answer.split("/")[0]
            print('Node name:', node_name)
            success, error = True, None
        except Exception as e:
            success, error = False, "Exception: (%s) %s" % (type(e), e)

    return success, error


def loop_until_is_up(seconds_between_calls=0.5, timeout=20):
    """
    endless loop, until RPC API call answers something
    """
    start = time.monotonic()

    while True:
        success, error = simple_RPC_call()
        print('success?', success, '\nerror?', error)
        if success:
            break
        if timeout:
            if time.monotonic() - start > timeout:
                break
        time.sleep(seconds_between_calls)

    return success


if __name__ == '__main__':
    loop_until_is_up()
