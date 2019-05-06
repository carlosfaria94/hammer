#!/usr/bin/env python3
"""
@summary: submit many contract storage.set(uint x) transactions
"""
import sys
import time
import json
from threading import Thread
from queue import Queue

from hammer.config import RPC_NODE_SEND, GAS, GAS_PRICE, CHAIN_ID, FILE_LAST_EXPERIMENT, EMPTY_BLOCKS_AT_END
from hammer.deploy import init_contract
from hammer.utils import init_web3, init_accounts, transfer_funds
from hammer.check_control import get_receipts_queue, has_successful_transactions


def storage_set(arg, account, hashes=None):
    """
    call the storage.set(uint x) method using the web3 method
    """
    print(".", end=" ")
    storage_set = STORAGE_CONTRACT.functions.set(x=arg).buildTransaction({
        'gas': GAS,
        'gasPrice': GAS_PRICE,
        'nonce': account["nonce"].increment(),
        'chainId': CHAIN_ID
    })
    print(storage_set['nonce'], end=" ")
    signed = w3.eth.account.signTransaction(
        storage_set,
        private_key=account["private_key"]
    )
    tx_hash = w3.toHex(w3.eth.sendRawTransaction(signed.rawTransaction))

    if hashes is not None:
        hashes.append(tx_hash)
    return tx_hash


def init_account_balances(w3, accounts):
    print("\n > Transfering funds to %d accounts" % len(accounts))
    sender = accounts.get(0)
    for account in accounts.values():
        transfer_funds(w3, sender, account, 5)


def many_transactions_threaded(num_tx, account):
    """
    submit many transactions multi-threaded.

    N.B.: 1 thread / transaction 
          -- machine can run out of threads, then crash
    """
    line = "\n> send %d transactions by account: %s, multi-threaded, one thread per tx:\n"
    print(line % (num_tx, account["address"]))

    threads = []
    txs = []  # container to keep all transaction hashes
    for i in range(num_tx):
        thread = Thread(target=storage_set, args=(i, account, txs))
        threads.append(thread)
    print("\n> %d transaction threads created" % len(threads))

    for thread in threads:
        thread.start()
        sys.stdout.flush()
    print("\n> all threads started")

    for thread in threads:
        thread.join()
    print("\n> all threads ended")

    return txs


def many_transactions_threaded_queue(num_tx, num_worker_threads, account):
    """
    submit many transactions multi-threaded, with size limited threading Queue
    """
    line = "send %d transactions by account: %d, via multi-threading queue with %s workers:\n"
    print(line % (num_tx, num_worker_threads, account["address"]))

    q = Queue()
    txs = []  # container to keep all transaction hashes

    def worker():
        while True:
            item = q.get()
            storage_set(item, account, txs)
            q.task_done()

    for i in range(num_worker_threads):
        thread = Thread(target=worker)
        thread.daemon = True
        thread.start()
    print("\n> %d worker threads created and started" % num_worker_threads)

    for i in range(num_tx):
        q.put(i)
    print("\n> %d items queued" % num_tx)

    q.join()
    print("\n> all items - done")
    return txs


def many_transactions_by_account(num_tx_per_account, accounts):
    """
    Submit a number of transactions per account.
    Each account has a thread.
    """
    line = "%d accounts sending %d transactions each\n"
    print(line % (len(accounts), num_tx_per_account))

    txs = []  # container to keep all transaction hashes
    threads = []

    def account_worker(account, txs):
        for i in range(num_tx_per_account):
            storage_set(i, account, txs)

    for account in accounts.values():
        thread = Thread(target=account_worker, args=(account, txs))
        threads.append(thread)
    print("\n> %d account worker threads created" % len(threads))

    for thread in threads:
        thread.start()
        sys.stdout.flush()
    print("\n> all threads started")

    for thread in threads:
        thread.join()
    print("\n> all threads ended")

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
    line = "Transaction receipts from beginning and end all arrived. Blockrange %d to %d."
    line = line % (block_from, block_to)
    print(line)

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


def send():
    """
    sends many transactions to contract.
    choose algorithm depending on 2nd CLI argument.
    """
    print("\nCurrent blockNumber = ", w3.eth.blockNumber)
    transactions_count = int(sys.argv[1])

    # choose algorithm depending on 2nd CLI argument:
    if sys.argv[2] == "threaded1":
        # Init only 1 account to send all the transactions
        account = init_accounts(w3, 1).get(0)
        txs = many_transactions_threaded(transactions_count, account)
    elif sys.argv[2] == "threaded2":
        num_workers = 25
        if len(sys.argv) == 4:
            try:
                num_workers = int(sys.argv[3])
            except:
                pass
        # Init only 1 account to send all the transactions
        account = init_accounts(w3, 1).get(0)
        txs = many_transactions_threaded_queue(
            transactions_count, num_workers, account)
    elif sys.argv[2] == "accounts":
        num_accounts = 20
        if len(sys.argv) == 4:
            try:
                num_accounts = int(sys.argv[3])
            except:
                pass
        accounts = init_accounts(w3, num_accounts)
        init_account_balances(w3, accounts)
        txs = many_transactions_by_account(transactions_count, accounts)

    else:
        print("Nope. Choice '%s'" % sys.argv[2], "not recognized.")
        exit()

    print("%d transaction hashes recorded" % len(txs))
    return txs


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
