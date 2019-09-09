#!/usr/bin/env python3
"""
@summary: Performs control check after sending the transactions
"""
import time
import random
from threading import Thread
from queue import Queue

import web3


def has_tx_succeeded(tx_receipt):
    """
    We check tx has succeeded by reading the `status` on the `tx_receipt`
    More info: https://docs.pantheon.pegasys.tech/en/latest/Reference/JSON-RPC-API-Objects/#transaction-receipt-object
    """
    status = tx_receipt.get("status", None)
    if status == 1:
        return True
    return False


def get_receipt(w3, tx_hash, timeout, results):
    try:
        results[tx_hash] = w3.eth.waitForTransactionReceipt(tx_hash, timeout)
    except web3.utils.threads.Timeout:
        pass


def get_receipts(w3, tx_hashes, timeout):
    """
    one thread per tx_hash
    """
    tx_receipts = {}
    print("Waiting for %d transaction receipts, can possibly take a while ..." %
          len(tx_hashes))
    threads = []
    for tx_hash in tx_hashes:
        thread = Thread(target=get_receipt, args=(
            w3, tx_hash, timeout, tx_receipts))
        threads.append(thread)
        thread.start()

    # wait for all of them coming back:
    for thread in threads:
        thread.join()

    return tx_receipts


def get_receipts_queue(w3, tx_hashes, timeout, num_worker_threads=8, ifPrint=False):
    """
    Query the RPC via a multithreading Queue, with 8 worker threads.
    Advantage over 'get_receipts': 
                       Will also work for len(tx_hashes) > 1000 
    """
    start = time.monotonic()
    q = Queue()
    tx_receipts = {}

    def worker():
        while True:
            tx_hash = q.get()
            get_receipt(w3, tx_hash, timeout, tx_receipts)
            q.task_done()

    for i in range(num_worker_threads):
        thread = Thread(target=worker)
        thread.daemon = True
        thread.start()

    for tx in tx_hashes:
        q.put(tx)

    q.join()

    if ifPrint:
        duration = time.monotonic() - start
        print("%d lookups took %.1f seconds" % (len(tx_receipts), duration))

    return tx_receipts


def has_successful_transactions(w3, txs, sample_size=100, timeout=300):
    """
    Makes sure that the transactions were actually successful, 
    and did not fail because e.g. running out of gas, etc.

    We want to benchmark the speed of successful state changes!!

    Method: Instead of checking EVERY transaction this just takes some sample.
    It can fail in three very different ways:

    * timeout when waiting for tx-receipt, then you try raising the timeout seconds
    * tx_receipt.status == 0 for any of the sampled transactions. Real tx failure!
    * all given gas used up. It's only an indirect indicator for a failed transaction.
    """
    print("Check control sample.")
    txs_sample_count = sample_size if len(txs) > sample_size else len(txs)
    txs_sample = random.sample(txs, txs_sample_count)

    # Test 1: We receive all receipts?
    tx_receipts = get_receipts(w3, tx_hashes=txs_sample, timeout=timeout)
    receipts_count = len(tx_receipts)
    if receipts_count != txs_sample_count:
        print("<FAIL> Timeout. Received receipts only for %d out of %d sampled transactions." % (
            receipts_count, txs_sample_count))
        success = False
    else:
        print("No timeout. Received the receipts for all %d sampled transactions." %
              txs_sample_count)
        success = True

    # Test 2: Was each an every transaction successful?
    failed_txs = 0
    for tx_hash, tx_receipt in tx_receipts.items():
        if not has_tx_succeeded(tx_receipt):
            success = False
            print("<FAIL> Transaction was NOT successful:", tx_hash, tx_receipt)
            failed_txs = failed_txs + 1

    if failed_txs > 0:
        print("<FAIL> %d out of %d not successful!" %
              (failed_txs, receipts_count))

    print("Sample of %d transactions checked." % receipts_count)
    if success:
        print("\nDONE.")
    else:
        print("\nFAILURE.")
        exit()

    return success
