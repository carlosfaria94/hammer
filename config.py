#!/usr/bin/env python3
"""
@summary: settings
"""

RPCaddress = 'http://localhost:8550'
RPCaddress2 = 'http://localhost:8550'

TIMEOUT_DEPLOY = 300

# submit transaction via web3 or directly via RPC
ROUTE = "web3"  # "web3" "RPC"

# gas given for .set(x) transaction
# N.B.: must be different from (i.e. higher than) the eventually used gas in
# a successful transaction; because difference is used as sign for a FAILED
# transaction in the case of those clients which do not have a
# 'transactionReceipt.status' field yet
GAS_FOR_SET_CALL = 90000

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
