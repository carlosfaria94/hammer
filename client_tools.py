#!/usr/bin/env python3
"""
@summary: tools to talk to an Ethereum client node 
"""

import os

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
from hammer.config import FILE_PASSPHRASE
from hammer.client_type import clientType


def print_versions():
    import sys
    from web3 import __version__ as web3version
    from solc import get_solc_version

    import pkg_resources
    pysolcversion = pkg_resources.get_distribution("py-solc").version

    print("versions: web3 %s, py-solc: %s, solc %s, python %s" % (web3version,
                                                                  pysolcversion, get_solc_version(), sys.version.replace("\n", "")))


def start_web3_connection(RPCaddress, account=None):
    """
    get a web3 object, and make it global 
    """
    global w3
    w3 = Web3(HTTPProvider(RPCaddress, request_kwargs={'timeout': 120}))

    print("web3 connection established, blockNumber =",
          w3.eth.blockNumber, end=", ")
    print("node version string = ", w3.version.node)

    account_name = "chosen"
    if not account:
        # set first account as sender
        print(w3.eth.accounts)
        w3.eth.defaultAccount = w3.eth.accounts[0]
        account_name = "first"
    print(account_name + " account of node is",
          w3.eth.defaultAccount, end=", ")
    print("balance is %s Ether" % w3.fromWei(
        w3.eth.getBalance(w3.eth.defaultAccount), "ether"))

    return w3


def setGlobalVariables_clientType(w3):
    """
    Set global variables.
    """
    global NODENAME, NODETYPE, NODEVERSION, CONSENSUS, NETWORKID, CHAINNAME, CHAINID

    NODENAME, NODETYPE, NODEVERSION, CONSENSUS, NETWORKID, CHAINNAME, CHAINID = clientType(
        w3)

    formatter = "nodeName: %s, nodeType: %s, nodeVersion: %s, consensus: %s, network: %s, chainName: %s, chainId: %s"
    print(formatter % (NODENAME, NODETYPE, NODEVERSION,
                       CONSENSUS, NETWORKID, CHAINNAME, CHAINID))

    # for when imported into other modules
    return NODENAME, NODETYPE, NODEVERSION, CONSENSUS, NETWORKID, CHAINNAME, CHAINID


def web3_connection(RPCaddress=None, account=None):
    """
    prints dependency versions, starts web3 connection, identifies client node type
    """
    print_versions()
    w3 = start_web3_connection(RPCaddress=RPCaddress, account=account)

    NODENAME, NODETYPE, NODEVERSION, CONSENSUS, NETWORKID, CHAINNAME, CHAINID = setGlobalVariables_clientType(
        w3)

    chainInfos = NODENAME, NODETYPE, NODEVERSION, CONSENSUS, NETWORKID, CHAINNAME, CHAINID

    return w3, chainInfos


################################################################################
# generally useful tools


def getBlockTransactionCount(w3, blockNumber):
    """
    testRPC does not provide this endpoint yet, so replicate its functionality:
    """
    block = w3.eth.getBlock(blockNumber)
    return len(block["transactions"])


def correctPath(file):
    """
    This is a semi-dirty hack for FILE_PASSPHRASE (="account-passphrase.txt")
    to repair the FileNotFound problem which only appears when running the tests 
    because then the currentWorkDir is "chainhammer" not "chainhammer/hammer" 
    P.S.: If ever consistent solution, then also fix for the two
          "contract-{abi,address}.json" which tests put into the root folder
    """
    # print ("os.getcwd():", os.getcwd())

    if os.getcwd().split("/")[-1] != "hammer":
        return os.path.join("hammer", file)
    else:
        return file


def unlockAccount(account=None):
    """
    unlock once, then leave open
    """

    if not account:
        account = w3.eth.defaultAccount

    w3.personal.unlockAccount(account, '')
    print("unlocked:", answer)
    return answer


if __name__ == '__main__':
    answer = web3_connection(RPCaddress=RPCaddress, account=None)
    w3, chainInfos = answer
    global NODENAME, NODETYPE, NODEVERSION, CONSENSUS, NETWORKID, CHAINNAME, CHAINID
    NODENAME, NODETYPE, NODEVERSION, CONSENSUS, NETWORKID, CHAINNAME, CHAINID = chainInfos
