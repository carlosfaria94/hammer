#!/usr/bin/env python3
"""
@summary: submit many contract storage.set(uint x) transactions
"""

# extend sys.path for imports:
if __name__ == '__main__' and __package__ is None:
    from os import sys, path
    sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

import sys, time, random, json
from threading import Thread, Lock
from queue import Queue

try:
    import requests # pip3 install requests
    import web3
    from web3 import Web3, Account, HTTPProvider # pip3 install web3
    from web3.utils.abi import filter_by_name, abi_to_signature
    from web3.utils.encoding import pad_hex
except:
    print("Dependencies unavailable. Start virtualenv first!")
    exit()

from hammer.config import RPC_NODE_SEND, GAS, GAS_PRICE, CHAIN_ID, FILE_LAST_EXPERIMENT, EMPTY_BLOCKS_AT_END
from hammer.deploy import load_from_disk
from hammer.utils import init_web3
from hammer.atomic_nonce import AtomicNonce

def init_contract():
    """
    initialise contract object from address, stored in disk file by deploy.py
    """
    contract_address, abi = load_from_disk()
    contract = w3.eth.contract(address=contract_address, abi=abi)
    return contract

def storage_set(contract, arg, nonce, hashes=None):
    """
    call the storage.set(uint x) method using the web3 method 
    """
    print (".", end=" ")
    
    storage_set = contract.functions.set(x=arg).buildTransaction({
        'gas': GAS,
        'gasPrice': GAS_PRICE,
        'nonce': nonce.increment(),
        'chainId': CHAIN_ID
    })
    key = '0xdde94897e9e4f787f6360552a4a723d06b0c730da77c30ce2d4cda61f94e187f'
    print('storage_set', storage_set['nonce'])
    signed = Account.signTransaction(storage_set, private_key=key)
    tx_hash = w3.toHex(w3.eth.sendRawTransaction(signed.rawTransaction))

    if not hashes == None:
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
    txs = [] # container to keep all transaction hashes
    for i in range(num_tx):
        t = Thread(target = storage_set,
                   args   = (contract, i, nonce, txs))
        threads.append(t)

    print("%d transaction threads created." % len(threads))

    for t in threads:
        t.start()
        sys.stdout.flush()
    print("all threads started.")
    
    for t in threads: 
        t.join()
    print("all threads ended.")
    
    return txs

def many_transactions_threaded_queue(contract, num_tx, num_worker_threads, nonce):
    """
    submit many transactions multi-threaded, 
    with size limited threading Queue
    """

    line = "send %d transactions, via multi-threading queue with %d workers:\n"
    print (line % (num_tx, num_worker_threads))

    q = Queue()
    txs = [] # container to keep all transaction hashes
    
    def worker():
        while True:
            item = q.get()
            storage_set(contract, item, nonce, txs)
            print ("T", end=""); sys.stdout.flush()
            q.task_done()

    for i in range(num_worker_threads):
         t = Thread(target=worker)
         t.daemon = True
         t.start()
         print ("W", end=""); sys.stdout.flush()
    print ("\n%d worker threads created." % num_worker_threads)

    for i in range(num_tx):
        q.put(i)
        print ("I", end=""); sys.stdout.flush()
    print ("\n%d items queued." % num_tx)

    q.join()
    print ("\nall items - done.")
    
    return txs

def has_tx_succeeded(tx_receipt):
    """
    We check tx has succeeded by reading the `status` on the `tx_receipt`
    More info: https://docs.pantheon.pegasys.tech/en/latest/Reference/JSON-RPC-API-Objects/#transaction-receipt-object
    """
    status = tx_receipt.get("status", None)
    if status == 1:
        return True
    return False

def get_receipt(tx_hash, timeout, results):
    try:
        results[tx_hash] = w3.eth.waitForTransactionReceipt(tx_hash, timeout)
    except web3.utils.threads.Timeout:
        pass


def get_receipts(tx_hashes, timeout):
    """
    one thread per tx_hash
    """
    tx_receipts = {}
    print("Waiting for %d transaction receipts, can possibly take a while ..." % len(tx_hashes))
    threads = []    
    for tx_hash in tx_hashes:
        t = Thread(target = get_receipt,
                   args   = (tx_hash, timeout, tx_receipts))
        threads.append(t)
        t.start()

    # wait for all of them coming back:
    for t in threads: 
        t.join()

    return tx_receipts

def get_receipts_queue(tx_hashes, timeout, num_worker_threads=8, ifPrint=False):
    """
    Query the RPC via a multithreading Queue, with 8 worker threads.
    Advantage over 'get_receipts': 
                       Will also work for len(tx_hashes) > 1000 
    """
    start=time.monotonic()
    q = Queue()
    tx_receipts = {}

    def worker():
        while True:
            tx_hash = q.get()
            get_receipt(tx_hash, timeout, tx_receipts)
            q.task_done()

    for i in range(num_worker_threads):
         t = Thread(target=worker)
         t.daemon = True
         t.start()

    for tx in tx_hashes:
        q.put (tx)

    q.join()

    if ifPrint:
        duration = time.monotonic() - start
        print ("%d lookups took %.1f seconds" % (len(tx_receipts), duration))

    return tx_receipts

def has_successful_transactions(txs, sample_size=50, timeout=100):
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
    
    print ("Check control sample.")
    N = sample_size if len(txs) > sample_size else len(txs) 
    txs_sample = random.sample(txs, N)
    
    tx_receipts = get_receipts(tx_hashes=txs_sample, timeout=timeout) 
    
    # Test 1: Are all receipts here?    
    M = len(tx_receipts)
    if M != N:
        print ("Bad: Timeout, received receipts only for %d out of %d sampled transactions." % (M, N))
        success = False 
    else:
        print ("Good: No timeout, received the receipts for all %d sampled transactions." % N)
        success = True
            
    # Test 2: Was each an every transaction successful?
    badCounter=0
    for tx_hash, tx_receipt in tx_receipts.items():
        # status = tx_receipt.get("status", None) # unfortunately not all clients support this yet
        # print ((tx_hash, status, tx_receipt.gasUsed ))
        if not has_tx_succeeded(tx_receipt):
            success = False
            print ("Transaction NOT successful:", tx_hash, tx_receipt)
            badCounter = badCounter+1

    if badCounter:
        print ("Bad: %d out of %d not successful!" % (badCounter, M))
        
    print ("Sample of %d transactions checked ... hints at:" % M, end=" ")
    print( "TOTAL SUCCESS :-)" if success else "-AT LEAST PARTIAL- FAILURE :-(" )
    
    return success

def get_sample(txs, tx_ranges=100, timeout=60):
    """
    Also only a heuristic:
    Assuming the first 100 and the last 100 transaction hashes that had been added 
    to the list 'txs' can reveal the min and max block numbers of this whole experiment
    """
    txs_begin_and_end = txs[:tx_ranges] + txs[-tx_ranges:]
    tx_receipts = get_receipts_queue(tx_hashes=txs_begin_and_end, timeout=timeout)
    blockNumbers = [receipt.blockNumber for receipt in tx_receipts.values()]
    blockNumbers = sorted(list(set(blockNumbers))) # make unique
    return min(blockNumbers), max(blockNumbers)

    
def store_experiment_data(success, num_txs, 
                          block_from, block_to, 
                          empty_blocks,
                          filename=FILE_LAST_EXPERIMENT):
    """
    most basic data about this last experiment, 
    stored in same (overwritten) file.
    Purpose: diagramming should be able to calc proper averages & select ranges
    """
    data = {"send" : {
                "block_first" : block_from,
                "block_last": block_to,
                "empty_blocks": empty_blocks, 
                "num_txs" : num_txs,
                "sample_txs_successful": success
                },
            "node" : {
                "rpc_address": RPCaddress,
                "web3.version.node": w3.version.node
                }
            }
            
    with open(filename, "w") as f:
        json.dump(data, f)
    

def wait_some_blocks(waitBlocks=EMPTY_BLOCKS_AT_END, pause_between_queries=0.3):
    """
    Actually, the waiting has to be done here, 
    because ./send.py is started later than ./watch_tps.py
    So when ./send.py ends, the analysis can happen.
    """
    blockNumber_start = w3.eth.blockNumber
    print ("blocknumber now:", blockNumber_start, end=" ")
    print ("waiting for %d empty blocks:" % waitBlocks)
    bn_previous=bn_now=blockNumber_start
    
    while bn_now < waitBlocks + blockNumber_start:
        time.sleep(pause_between_queries)
        bn_now=w3.eth.blockNumber
        # print (bn_now, waitBlocks + blockNumber_start)
        if bn_now!=bn_previous:
            bn_previous=bn_now
            print (bn_now, end=" "); sys.stdout.flush()
         
    print ("Done.")

        
def finish(txs, success):
    block_from, block_to = get_sample(txs)
    txt = "Transaction receipts from beginning and end all arrived. Blockrange %d to %d."
    txt = txt % (block_from, block_to)
    print(txt)
    
    wait_some_blocks()
    
    store_experiment_data(success, len(txs), block_from, block_to, empty_blocks=waitBlocks)
    
    print ("Data stored. This will trigger watch_tps.py to end.\n"
           "(Beware: Wait ~0.5s until watch_tps.py stops and writes to same file.)")

def check_argv():
    """
    before anything, check if number of parameters is fine, or print syntax instructions
    """    
    if not (2 <= len(sys.argv) <= 4):
        print ("Needs parameters:")
        print ("%s numTransactions algorithm [workers]" % sys.argv[0])
        print ("at least numTransactions, e.g.")
        print ("%s 1000" % sys.argv[0])
        exit()


def send(contract, nonce):
    """
    sends many transactions to contract.
    choose algorithm depending on 2nd CLI argument.
    """
    print("\nCurrent blockNumber = ", w3.eth.blockNumber)
    numTransactions = int(sys.argv[1])

    # choose algorithm depending on 2nd CLI argument:
    if sys.argv[2]=="threaded1":
        txs = many_transactions_threaded(contract, numTransactions, nonce=nonce)    
    elif sys.argv[2]=="threaded2":
        num_workers = 25
        if len(sys.argv)==4:
            try:
                num_workers = int(sys.argv[3])
            except:
                pass
        txs = many_transactions_threaded_queue(contract, 
                                         num_tx=numTransactions, 
                                         num_worker_threads=num_workers,
                                         nonce=nonce)
    else:
        print ("Nope. Choice '%s'" % sys.argv[2], "not recognized.")
        exit()

    print ("%d transaction hashes recorded, examples: %s" % (len(txs), txs[:2]))
    return txs

if __name__ == '__main__':
    check_argv()

    global w3
    w3 = init_web3(RPCaddress=RPC_NODE_SEND)

    contract = init_contract()

    initial_nonce = w3.eth.getTransactionCount(
            '0x8717eD44cEB53f15dB9CF1bEc75a037A70232AC8')
    print('initial_nonce', initial_nonce)
    nonce = AtomicNonce(initial_nonce)

    txs = send(contract, nonce)
    sys.stdout.flush() # so that the log files are updated.

    success = has_successful_transactions(txs)
    sys.stdout.flush()

    finish(txs, success)
    sys.stdout.flush()