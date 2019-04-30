#!/usr/bin/env python3
"""
@summary: Timing transactions that are getting into the chain
"""

import time
import timeit
import sys
import os
import json

try:
    from web3 import Web3, HTTPProvider
except:
    print("Dependencies unavailable. Start virtualenv first!")
    exit()

# extend path for imports:
if __name__ == '__main__' and __package__ is None:
    from os import sys, path
    sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

from hammer.config import RPC_NODE_WATCH, FILE_LAST_EXPERIMENT, AUTOSTOP_TPS
from hammer.deploy import load_from_disk, FILE_CONTRACT_ADDRESS
from hammer.utils import init_web3, read, file_date


def wait_new_contract(query_interval=0.1):
    """
    Wait for new smart contract to be deployed.

    Continuously polls file "FILE_CONTRACT_ADDRESS".
    Returns when overwritten file has different address or new filedate.

    N.B.: It actually happens that same Ethereum contract address is created again, 
          if blockchain is deleted, and everything restarted. So: Check filedate too.
    """

    address, _ = load_from_disk()
    when = os.path.getmtime(FILE_CONTRACT_ADDRESS)
    print("(filedate %d) last contract address: %s" % (when, address))

    while(True):
        time.sleep(query_interval)

        # checks whether a new contract has been deployed
        # because then a new address has been saved to file:
        newAddress, _ = load_from_disk()
        newWhen = os.path.getmtime(FILE_CONTRACT_ADDRESS)
        if (newAddress != address or newWhen != when):
            print("(filedate %d) new contract address: %s" %
                  (newWhen, newAddress))
            break
    return


def analyze_new_blocks(blockNumber, newBlockNumber, txCount, start_time, peakTpsAv):
    """
    iterate through all new blocks, add up number of transactions
    print status line
    """
    txCount_new = 0
    # TODO check range again - shift by one?
    for block in range(blockNumber + 1, newBlockNumber + 1):
        txCount_new += w3.eth.getBlockTransactionCount(block)

    ts_blockNumber = w3.eth.getBlock(blockNumber).timestamp
    ts_newBlockNumber = w3.eth.getBlock(newBlockNumber).timestamp
    ts_diff = ts_newBlockNumber - ts_blockNumber

    # turn timestamp into (float of) seconds
    # most ethereum clients return block timestamps as whole seconds
    timeunits = 1.0
    blocktimeSeconds = ts_diff / timeunits

    try:
        tps_current = txCount_new / blocktimeSeconds
    except ZeroDivisionError:
        tps_current = 0

    txCount += txCount_new
    elapsed = timeit.default_timer() - start_time
    tpsAv = txCount / elapsed

    if tpsAv > peakTpsAv:
        peakTpsAv = tpsAv

    verb = " is" if peakTpsAv == tpsAv else "was"

    line = "block %d | new #TX %3d / %4.0f ms = " \
           "%5.1f TPS_current | total: #TX %4d / %4.1f s = %5.1f TPS_average " \
           "(peak %s %5.1f TPS_average)"
    line = line % (newBlockNumber, txCount_new, blocktimeSeconds * 1000,
                   tps_current, txCount, elapsed, tpsAv, verb, peakTpsAv)
    print(line)

    return txCount, peakTpsAv, tpsAv


class CodingError(Exception):
    pass


def getNearestEntry(myDict, myIndex):
    """
    because 
      finalTpsAv = tpsAv[block_last]
    can sometimes not be resolved, then choose
      finalTpsAv = tpsAv[block_last+i]
    testing with increasing i, the decreasing i
    """
    answer = myDict.get(myIndex, None)
    if answer:
        return answer

    maxIndex, minIndex = max(myDict.keys()), min(myDict.keys())

    # first look later:
    i = myIndex
    while not answer:
        i += +1
        if i > maxIndex:
            break
        answer = myDict.get(i, None)

    # then look earlier:
    i = myIndex
    while not answer:
        i += -1
        if i < minIndex:
            raise CodingError("Ouch, this should never happen. Info: len(myDict)=%d myIndex=%d" % (
                len(myDict), myIndex))
        answer = myDict.get(i, None)

    return answer


def measure(blockNumber, pause_between_queries=0.3, relaxation_rounds=3):
    """
    when a (or more) new block appeared, add them to the total, and print a line.
    """
    whenBefore = file_date(file=FILE_LAST_EXPERIMENT)

    txCount = w3.eth.getBlockTransactionCount(blockNumber)

    start_time = timeit.default_timer()
    start_epochtime = time.time()
    # TODO: perhaps additional to elapsed system time, show blocktime?

    print('starting timer, at block', blockNumber, 'which has ',
          txCount, ' transactions; at epochtime', start_epochtime)

    peakTpsAv = 0
    counterStart, blocknumberEnd = 0, -1

    tpsAv = {}  # memorize all of them, so we can return value at 'block_last'

    while(True):
        newBlockNumber = w3.eth.blockNumber

        if (blockNumber != newBlockNumber):  # when a new block appears:
            args = (blockNumber, newBlockNumber,
                    txCount, start_time, peakTpsAv)
            txCount, peakTpsAv, tpsAv[newBlockNumber] = analyze_new_blocks(
                *args)
            blockNumber = newBlockNumber

            # for the first 3 rounds, always reset the peakTpsAv again!
            if counterStart < relaxation_rounds:
                peakTpsAv = 0
            counterStart += 1

        # send.py --> store_experiment_data() is called AFTER last tx was mined.
        # THEN do another 10 empty blocks ...
        # only THEN end this:
        # if AUTOSTOP_TPS and blocknumberEnd==-1 and file_date()!=whenBefore:
        if AUTOSTOP_TPS and file_date(file=FILE_LAST_EXPERIMENT) != whenBefore:
            print("Received signal from send.py = updated INFOFILE.")
            block_last = read(file=FILE_LAST_EXPERIMENT)['send']['block_last']
            # finalTpsAv = tpsAv[block_last]
            finalTpsAv = getNearestEntry(myDict=tpsAv, myIndex=block_last)
            break

        # do not query too often; as little side effect on node as possible
        time.sleep(pause_between_queries)

    txt = "Experiment ended! Current blocknumber = %d"
    txt = txt % (w3.eth.blockNumber)
    print(txt)
    return peakTpsAv, finalTpsAv, start_epochtime


def write_measures(peakTpsAv, finalTpsAv, start_epochtime, file=FILE_LAST_EXPERIMENT):
    with open(file, "r") as f:
        data = json.load(f)

    data["tps"] = {}
    data["tps"]["peakTpsAv"] = peakTpsAv
    data["tps"]["finalTpsAv"] = finalTpsAv
    data["tps"]["start_epochtime"] = start_epochtime

    with open(file, "w") as f:
        json.dump(data, f)


if __name__ == '__main__':
    global w3
    w3 = init_web3(RPCaddress=RPC_NODE_WATCH)

    print("\n Block ", w3.eth.blockNumber,
          " - waiting for something to happen")

    wait_new_contract()
    start_block_number = w3.eth.blockNumber
    print("\n Start Block Number:", start_block_number)

    peakTpsAv, finalTpsAv, start_epochtime = measure(start_block_number)

    write_measures(peakTpsAv, finalTpsAv, start_epochtime)

    print("Updated info file:", FILE_LAST_EXPERIMENT, "THE END.")
