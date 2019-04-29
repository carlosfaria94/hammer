#!/usr/bin/env python3
"""
@summary: settings
"""
# The node that broadcast the transactions (send.py)
RPC_NODE_BROADCAST = 'http://localhost:8550'
# The node that watch the transactions (tps.py)
RPC_NODE_WATCH = 'http://localhost:8550'

MNEMONIC = "about hair goose output senior short stone decade lock loop kidney beach"

TIMEOUT_DEPLOY = 300

# submit transaction via web3 or directly via RPC
ROUTE = "web3"  # "web3" "RPC"

GAS = 4700000
GAS_PRICE = 20000000000

CHAIN_ID = 2019  # Network or chain id
NETWORK_ID = 2019

# contract files:
FILE_CONTRACT_SOURCE = "contract.sol"
FILE_CONTRACT_ABI = "contract-abi.json"
FILE_CONTRACT_ADDRESS = "contract-address.json"

# account passphrase
FILE_PASSPHRASE = "account-passphrase.txt"

# last experiment data
FILE_LAST_EXPERIMENT = "last-experiment.json"

# if True, the newly written file FILE_LAST_EXPERIMENT is going to stop the loop in tps.py
AUTOSTOP_TPS = True

# after last txs have been mined, give 10 more blocks before experiment ends
EMPTY_BLOCKS_AT_END = 10

# DB file for traversing all blocks
DBFILE = "allblocks.db"

if __name__ == '__main__':
    print("Do not run this. Like you just did. Don't.")
