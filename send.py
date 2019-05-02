#!/usr/bin/env python3
"""
@summary: submit many contract storage.set(uint x) transactions
"""

# extend sys.path for imports:
if __name__ == '__main__' and __package__ is None:
    from os import sys, path
    sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

import sys
import time
import json
from threading import Thread
from queue import Queue

from hammer.config import RPC_NODE_SEND, GAS, GAS_PRICE, CHAIN_ID, FILE_LAST_EXPERIMENT, EMPTY_BLOCKS_AT_END
from hammer.deploy import init_contract
from hammer.utils import init_web3, atomic_nonce
from hammer.check_control import get_receipts_queue, has_successful_transactions


def storage_set(contract, arg, nonce, hashes=None):
    """
    call the storage.set(uint x) method using the web3 method 
    """
    print(".", end=" ")
    storage_set = contract.functions.set(x=arg).buildTransaction({
        'gas': GAS,
        'gasPrice': GAS_PRICE,
        'nonce': nonce.increment(),
        'chainId': CHAIN_ID
    })
    key = '0xdde94897e9e4f787f6360552a4a723d06b0c730da77c30ce2d4cda61f94e187f'
    print('storage_set', storage_set['nonce'])
    signed = w3.eth.account.signTransaction(storage_set, private_key=key)
    tx_hash = w3.toHex(w3.eth.sendRawTransaction(signed.rawTransaction))

    if hashes is not None:
        hashes.append(tx_hash)
    return tx_hash


def many_transactions_threaded(contract, num_tx, nonce):
    """
    submit many transactions multi-threaded.

    N.B.: 1 thread / transaction 
          -- machine can run out of threads, then crash
    """
    print("send %d transactions, multi-threaded, one thread per tx:\n" % (num_tx))

    threads = []
    txs = []  # container to keep all transaction hashes
    for i in range(num_tx):
        thread = Thread(target=storage_set, args=(contract, i, nonce, txs))
        threads.append(thread)

    print("%d transaction threads created." % len(threads))

    for thread in threads:
        thread.start()
        sys.stdout.flush()
    print("all threads started.")

    for thread in threads:
        thread.join()
    print("all threads ended.")

    return txs


def many_transactions_threaded_queue(contract, num_tx, num_worker_threads, nonce):
    """
    submit many transactions multi-threaded, 
    with size limited threading Queue
    """

    line = "send %d transactions, via multi-threading queue with %d workers:\n"
    print(line % (num_tx, num_worker_threads))

    q = Queue()
    txs = []  # container to keep all transaction hashes

    def worker():
        while True:
            item = q.get()
            storage_set(contract, item, nonce, txs)
            print("T", end="")
            sys.stdout.flush()
            q.task_done()

    for i in range(num_worker_threads):
        thread = Thread(target=worker)
        thread.daemon = True
        thread.start()
        print("W", end="")
        sys.stdout.flush()

    print("\n%d worker threads created." % num_worker_threads)

    for i in range(num_tx):
        q.put(i)
        print("I", end="")
        sys.stdout.flush()

    print("\n%d items queued." % num_tx)

    q.join()
    print("\nall items - done.")
    return txs


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


def store_experiment_data(success, num_txs, block_from, block_to, empty_blocks, filename=FILE_LAST_EXPERIMENT):
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

    with open(filename, "w") as f:
        json.dump(data, f)


def wait_some_blocks(wait_blocks=EMPTY_BLOCKS_AT_END, pause_between_queries=0.3):
    """
    Actually, the waiting has to be done here,
    because ./send.py is started later than ./watch_tps.py
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
    txt = "Transaction receipts from beginning and end all arrived. Blockrange %d to %d."
    txt = txt % (block_from, block_to)
    print(txt)

    wait_some_blocks()

    store_experiment_data(success, len(txs), block_from,
                          block_to, empty_blocks=EMPTY_BLOCKS_AT_END)

    print("Data stored. This will trigger watch_tps.py to end.\n",
          "(Beware: Wait ~0.5s until watch_tps.py stops and writes to same file.)")


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


def send(contract, nonce):
    """
    sends many transactions to contract.
    choose algorithm depending on 2nd CLI argument.
    """
    print("\nCurrent blockNumber = ", w3.eth.blockNumber)
    transactions_count = int(sys.argv[1])

    # choose algorithm depending on 2nd CLI argument:
    if sys.argv[2] == "threaded1":
        txs = many_transactions_threaded(
            contract, transactions_count, nonce=nonce)
    elif sys.argv[2] == "threaded2":
        num_workers = 25
        if len(sys.argv) == 4:
            try:
                num_workers = int(sys.argv[3])
            except:
                pass
        txs = many_transactions_threaded_queue(contract,
                                               num_tx=transactions_count,
                                               num_worker_threads=num_workers,
                                               nonce=nonce)
    else:
        print("Nope. Choice '%s'" % sys.argv[2], "not recognized.")
        exit()

    print("%d transaction hashes recorded, examples: %s" % (len(txs), txs[:2]))
    return txs


if __name__ == '__main__':
    check_argv()

    global w3
    w3 = init_web3(RPCaddress=RPC_NODE_SEND)

    contract = init_contract(w3)
    txs = send(contract, atomic_nonce(w3))
    sys.stdout.flush()  # so that the log files are updated.

    success = has_successful_transactions(w3, txs)
    sys.stdout.flush()

    finish(txs, success)
    sys.stdout.flush()
