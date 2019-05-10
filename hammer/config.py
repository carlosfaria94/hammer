#!/usr/bin/env python3
"""
@summary: settings
"""
# The node that send the transactions (send.py)
RPC_NODE_SEND = 'http://localhost:32772/jsonrpc'
# The node that watch the transactions (measure_tps.py)
RPC_NODE_WATCH = 'http://localhost:32772/jsonrpc'

# TODO: Insert MNEMONIC here to generate accounts
MNEMONIC = ""

TIMEOUT_DEPLOY = 300

GAS = 4700000
GAS_PRICE = 20000000000

CHAIN_ID = 1729  # Network or chain id

# contract files:
FILE_CONTRACT_SOURCE = "contract.sol"
FILE_CONTRACT_ABI = "contract-abi.json"
FILE_CONTRACT_ADDRESS = "contract-address.json"
FILE_CONTRACT_BIN = "contract-bin.json"

# last experiment data
FILE_LAST_EXPERIMENT = "last-experiment.json"

# after last txs have been mined, give 10 more blocks before experiment ends
EMPTY_BLOCKS_AT_END = 10

if __name__ == '__main__':
    print("Do not run this. Like you just did. Don't.")
