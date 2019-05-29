#!/usr/bin/env python3
"""
@summary: submit many contract storage.set(uint x) transactions
"""
import sys
import time
import json
from threading import Thread, get_ident
from queue import Queue

import requests

# extend path for imports:
if __name__ == '__main__' and __package__ is None:
    from os import sys, path
    sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

from config import RPC_NODE_SEND, GAS, GAS_PRICE, CHAIN_ID, FILE_LAST_EXPERIMENT, EMPTY_BLOCKS_AT_END, BATCH_TX, TX_PER_BATCH, PMINT
from deploy import init_contract
from utils import init_web3, init_accounts, transfer_funds
from check_control import get_receipts_queue, has_successful_transactions

def send():
    """
    sends many transactions to contract.
    choose algorithm depending on 2nd CLI argument.
    """
    print("\nCurrent blockNumber = ", w3.eth.blockNumber)
    transactions_count = int(sys.argv[1])

    # choose algorithm depending on 2nd CLI argument:
    if sys.argv[2] == "accounts":
        num_accounts = 20
        if len(sys.argv) == 4:
            try:
                num_accounts = int(sys.argv[3])
            except:
                pass
        accounts = init_accounts(w3, num_accounts)
        if not PMINT:
            init_account_balances(w3, accounts)
        accounts = create_signed_transactions(transactions_count, accounts)
        init_experiment_data()
        txs = broadcast_transactions(transactions_count, accounts)
    else:
        print("Nope. Choice '%s'" % sys.argv[2], "not recognized.")
        exit()

    print("%d transaction hashes recorded" % len(txs))
    return txs

def create_signed_transactions(num_tx_per_account, accounts):
    """
    Create and sign transaction that call Storage.set(x) and add it to a Queue on account["signatures"]
    """
    line = "\n> %d accounts creating and signing %d transactions each\n"
    print(line % (len(accounts), num_tx_per_account))

    threads = []

    def sign_worker(account, index):
        signed_txs = []
        for i in range(num_tx_per_account):
            storage_set(i, account, signed_txs)
        account["signed_txs"] = signed_txs
        accounts[index] = account

    for index, account in accounts.items():
        thread = Thread(target=sign_worker, args=(account, index))
        threads.append(thread)

    for thread in threads:
        thread.start()
        sys.stdout.flush()

    for thread in threads:
        thread.join()

    return accounts

def broadcast_transactions(num_tx_per_account, accounts):
    """
    Consumes signed transactions from a Queue, to broadcast each one per account.
    Each account has a thread.
    """
    line = "> %d accounts broadcasting %d transactions each\n"
    print(line % (len(accounts), num_tx_per_account))

    txs = []  # container to keep all transaction hashes
    threads = []
    def account_worker(account, txs):
        signed_txs = account["signed_txs"]
        while True:
            if not signed_txs:
                line = "> No more signed transactions (%d) for account with address: %s"
                print(line % (len(signed_txs), account["address"]))
                break
            if BATCH_TX:
                batch_request = build_batch_call(signed_txs[:TX_PER_BATCH])
                send_batch(batch_request, txs)
                # Remove signed transactions sent
                del signed_txs[:TX_PER_BATCH]
            else:
                tx_signed = signed_txs.pop(0)
                send_transaction(tx_signed, txs)

    for account in accounts.values():
        thread = Thread(target=account_worker, args=(account, txs))
        threads.append(thread)

    for t in threads:
        t.start()
        sys.stdout.flush()
    print("\n> %d account worker threads started" % len(accounts))

    for thread in threads:
        thread.join()
    print("\n> All accounts broadcasted their transactions\n")

    return txs

def storage_set(arg, account, signed_txs=None):
    """
    call the storage.set(uint x) method using the web3 method
    """
    storage_set = STORAGE_CONTRACT.functions.set(x=arg).buildTransaction({
        'gas': GAS,
        'gasPrice': GAS_PRICE,
        'nonce': account["nonce"].increment(w3),
        'chainId': CHAIN_ID
    })
    tx_signed = w3.eth.account.signTransaction(
        storage_set,
        private_key=account["private_key"]
    )

    if signed_txs is not None:
        signed_txs.append(tx_signed)
    return tx_signed

def send_transaction(tx_signed, hashes=None):
    tx_hash = w3.toHex(w3.eth.sendRawTransaction(tx_signed.rawTransaction))

    if hashes is not None:
        hashes.append(tx_hash)
    return tx_hash

def send_batch(batch_request, hashes=None):
    res = requests.post(
        RPC_NODE_SEND,
        json=batch_request,
        headers={'Content-type': 'application/json'}
    )
    if hashes is not None:
        for tx in res.json():
            hashes.append(tx["result"])
    return hashes

def build_batch_call(signed_txs):
    batch_request = []
    for i, signed_tx in enumerate(signed_txs):
        call = {
            'jsonrpc': '2.0',
            'method': 'eth_sendRawTransaction',
            'params': [w3.toHex(signed_tx.rawTransaction)],
            'id': i
        }
        batch_request.append(call)
    return batch_request

def init_account_balances(w3, accounts):
    print("\n> Transfering funds to %d accounts" % len(accounts))
    sender = accounts.get(0)
    threads = []

    for account in accounts.values():
        thread = Thread(target=transfer_funds, args=(w3, sender, account, 5))
        threads.append(thread)

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

def get_sample(txs, tx_ranges=100, timeout=60):
    """
    Also only a heuristic:
    Assuming the first 100 and the last 100 transaction hashes that had been added 
    to the list 'txs' can reveal the min and max block numbers of this whole experiment
    """
    txs_begin_and_end = txs[:tx_ranges] + txs[-tx_ranges:]
    tx_receipts = get_receipts_queue(
        w3=w3, tx_hashes=txs_begin_and_end, timeout=timeout)
    block_numbers = [receipt.blockNumber for receipt in tx_receipts.values()]
    block_numbers = sorted(list(set(block_numbers)))  # make unique
    return min(block_numbers), max(block_numbers)


def store_experiment_data(success, num_txs, block_from, block_to, empty_blocks, file=FILE_LAST_EXPERIMENT):
    """
    most basic data about this last experiment, stored in same (overwritten) file.
    Purpose: diagramming should be able to calc proper averages & select ranges
    """
    data = {
        "send": {
            "block_first": block_from,
            "block_last": block_to,
            "empty_blocks": empty_blocks,
            "num_txs": num_txs,
            "sample_txs_successful": success
        },
        "node": {
            "rpc_address": RPC_NODE_SEND,
            "web3.version.node": w3.version.node
        }
    }

    with open(file, "w") as f:
        json.dump(data, f)

def init_experiment_data(file=FILE_LAST_EXPERIMENT):
    """
    When we init the `FILE_LAST_EXPERIMENT` it will init TPS measurement (measure_tps.py) 
    """
    data = {}
    with open(file, "w") as f:
        json.dump(data, f)

def wait_some_blocks(wait_blocks=EMPTY_BLOCKS_AT_END, pause_between_queries=0.3):
    """
    Actually, the waiting has to be done here,
    because ./send.py is started later than ./measure_tps.py
    So when ./send.py ends, the analysis can happen.
    """
    block_number_start = w3.eth.blockNumber
    print("Block number now:", block_number_start, end=" ")
    print("Waiting for %d empty blocks:" % wait_blocks)
    bn_previous = bn_now = block_number_start

    while bn_now < wait_blocks + block_number_start:
        time.sleep(pause_between_queries)
        bn_now = w3.eth.blockNumber
        if bn_now != bn_previous:
            bn_previous = bn_now
            print(bn_now, end=" ")
            sys.stdout.flush()

    print("Done waiting for blocks")


def finish(txs, success):
    block_from, block_to = get_sample(txs)
    line = "Transaction receipts from beginning and end all arrived. Blockrange %d to %d."
    line = line % (block_from, block_to)
    print(line)

    wait_some_blocks()

    store_experiment_data(success, len(txs), block_from, block_to, empty_blocks=EMPTY_BLOCKS_AT_END)

    print("Data stored. This will trigger measure_tps.py to end.\n",
          "(Beware: Wait ~0.5s until measure_tps.py stops and writes to same file.)")


def check_argv():
    """
    before anything, check if number of parameters is fine, or print syntax instructions
    """
    if not 2 <= len(sys.argv) <= 4:
        print("Needs parameters:")
        print("%s transactions_count algorithm [workers]" % sys.argv[0])
        print("at least transactions_count, e.g.")
        print("%s 1000" % sys.argv[0])
        exit()

if __name__ == '__main__':
    global w3, STORAGE_CONTRACT
    check_argv()

    w3 = init_web3(RPCaddress=RPC_NODE_SEND)

    STORAGE_CONTRACT = init_contract(w3)
    txs = send()
    sys.stdout.flush()  # so that the log files are updated.

    success = has_successful_transactions(w3, txs)
    sys.stdout.flush()

    finish(txs, success)
    sys.stdout.flush()
