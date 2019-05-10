#!/usr/bin/env python3
"""
@summary: settings
"""
# The node that send the transactions (send.py)
RPC_NODE_SEND = 'http://localhost:32771/bootnode/jsonrpc'
# The node that watch the transactions (watch_tps.py)
RPC_NODE_WATCH = 'http://localhost:32771/pantheon-quickstart_node_1/jsonrpc'

# TODO: Insert MNEMONIC here to generate accounts
MNEMONIC = ""

TIMEOUT_DEPLOY = 300

GAS = 4700000
GAS_PRICE = 20000000000

CHAIN_ID = 6174  # Network or chain id
NETWORK_ID = 6174

# contract files:
FILE_CONTRACT_SOURCE = "contract.sol"
FILE_CONTRACT_ABI = "contract-abi.json"
FILE_CONTRACT_ADDRESS = "contract-address.json"
FILE_CONTRACT_BIN = "contract-bin.json"

# last experiment data
FILE_LAST_EXPERIMENT = "last-experiment.json"

# if True, the newly written file FILE_LAST_EXPERIMENT is going to stop the loop in watch_tps.py
AUTOSTOP_TPS = True

# after last txs have been mined, give 10 more blocks before experiment ends
EMPTY_BLOCKS_AT_END = 10
