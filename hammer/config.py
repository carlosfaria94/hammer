#!/usr/bin/env python3
"""
@summary: settings
"""
import os
from dotenv import load_dotenv
load_dotenv()

# The node that send the transactions (send.py)
RPC_NODE_SEND = os.getenv("RPC_NODE_SEND")
# The node that watch the transactions (measure_tps.py)
RPC_NODE_WATCH = os.getenv("RPC_NODE_WATCH")

MNEMONIC = os.getenv("MNEMONIC")

TIMEOUT_DEPLOY = 300

GAS = 100000  # Estimate gas to change the contract Storage
GAS_DEPLOY = 200000  # Estimate gas to deploy the contract Storage
GAS_PRICE = 20000000000

CHAIN_ID = 2018  # Network or chain id

BATCH_TX = False  # Should transactions sent in batchs?
TX_PER_BATCH = 400  # Number of transactions per batch. Should not pass the node TX pool

# contract files:
FILE_CONTRACT_SOURCE = "contract.sol"
FILE_CONTRACT_ABI = "contract-abi.json"
FILE_CONTRACT_ADDRESS = "contract-address.json"
FILE_CONTRACT_BIN = "contract-bin.json"

# last experiment data
FILE_LAST_EXPERIMENT = "last-experiment.json"

# after last txs have been mined, give 10 more blocks before experiment ends
EMPTY_BLOCKS_AT_END = 1

if __name__ == '__main__':
    print("Do not run this. Like you just did. Don't.")
