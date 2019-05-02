#!/usr/bin/env python3
"""
@summary: Timing transactions that are getting into the chain
"""

import time
import timeit
import sys
import os
import json

# extend path for imports:
if __name__ == '__main__' and __package__ is None:
    from os import sys, path
    sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

from hammer.config import RPC_NODE_WATCH, FILE_LAST_EXPERIMENT, AUTOSTOP_TPS, FILE_CONTRACT_ADDRESS
from hammer.deploy import load_from_disk
from hammer.utils import init_web3, read, file_date


class CodingError(Exception):
    pass


def watch_contract(query_interval=0.1):
    """
    Wait for new smart contract to be deployed.
    Continuously polls file "FILE_CONTRACT_ADDRESS".
    Returns when overwritten file has different address or new filedate.
    """
    address, _ = load_from_disk()
    when = os.path.getmtime(FILE_CONTRACT_ADDRESS)
    print("Last contract address: %s" % (address))

    # while True:
    #     time.sleep(query_interval)
    #     # checks whether a new contract has been deployed
    #     # because then a new address has been saved to file:
    #     new_address, _ = load_from_disk()
    #     new_when = os.path.getmtime(FILE_CONTRACT_ADDRESS)
    #     if (new_address != address or new_when != when):
    #         print("New contract address: %s" % (new_address))
    #         break
    return


def analyze_new_blocks(block_num, new_block_num, tx_count, start_time, peak_tps_avg):
    """
    iterate through all new blocks, add up number of transactions
    print status line
    """
    tx_count_new = 0
    # TODO check range again - shift by one?
    for block in range(block_num + 1, new_block_num + 1):
        tx_count_new += w3.eth.getBlockTransactionCount(block)

    ts_block_num = w3.eth.getBlock(block_num).timestamp
    ts_new_block_num = w3.eth.getBlock(new_block_num).timestamp
    ts_diff = ts_new_block_num - ts_block_num

    # turn timestamp into (float of) seconds
    # most ethereum clients return block timestamps as whole seconds
    timeunits = 1.0
    block_time_sec = ts_diff / timeunits

    try:
        tps_current = tx_count_new / block_time_sec
    except ZeroDivisionError:
        tps_current = 0

    tx_count += tx_count_new
    elapsed = timeit.default_timer() - start_time
    tps_avg = tx_count / elapsed

    if tps_avg > peak_tps_avg:
        peak_tps_avg = tps_avg

    verb = " is" if peak_tps_avg == tps_avg else "was"

    line = "block %d | new #TX %3d / %4.0f ms = " \
           "%5.1f TPS_current | total: #TX %4d / %4.1f s = %5.1f TPS_average " \
           "(peak %s %5.1f TPS_average)"
    line = line % (new_block_num, tx_count_new, block_time_sec * 1000,
                   tps_current, tx_count, elapsed, tps_avg, verb, peak_tps_avg)
    print(line)

    return tx_count, peak_tps_avg, tps_avg


def get_nearest_entry(tps_avg, block_last):
    """
    because
      final_tps_avg = tps_avg[block_last]
    can sometimes not be resolved, then choose
      final_tps_avg = tps_avg[block_last+i]
    testing with increasing i, the decreasing i
    """
    answer = tps_avg.get(block_last, None)
    if answer:
        return answer

    max_index, min_index = max(tps_avg.keys()), min(tps_avg.keys())

    # first look later:
    i = block_last
    while not answer:
        i += +1
        if i > max_index:
            break
        answer = tps_avg.get(i, None)

    # then look earlier:
    i = block_last
    while not answer:
        i += -1
        if i < min_index:
            raise CodingError("Ouch, this should never happen. Info: len(tps_avg)=%d block_last=%d" % (
                len(tps_avg), block_last))
        answer = tps_avg.get(i, None)

    return answer


def measure(block_num, pause_between_queries=0.3, relaxation_rounds=3):
    """
    when a (or more) new block appeared, add them to the total, and print a line.
    """
    whenBefore = file_date(file=FILE_LAST_EXPERIMENT)

    tx_count = w3.eth.getBlockTransactionCount(block_num)

    start_time = timeit.default_timer()
    start_epochtime = time.time()
    # TODO: perhaps additional to elapsed system time, show blocktime?

    print('starting timer, at block', block_num, 'which has ',
          tx_count, ' transactions; at epochtime', start_epochtime)

    peak_tps_avg, count = 0, 0
    tps_avg = {}  # memorize all of them, so we can return value at 'block_last'
    while True:
        new_block_num = w3.eth.blockNumber
        if block_num != new_block_num:  # when a new block appears:
            tx_count, peak_tps_avg, tps_avg[new_block_num] = analyze_new_blocks(
                block_num,
                new_block_num,
                tx_count,
                start_time,
                peak_tps_avg
            )
            block_num = new_block_num

            # for the first 3 rounds, always reset the peak_tps_avg again!
            if count < relaxation_rounds:
                peak_tps_avg = 0
            count += 1

        # send.py --> store_experiment_data() is called AFTER last tx was mined.
        # THEN do another 10 empty blocks...
        # only THEN end this loop:
        if AUTOSTOP_TPS and file_date(file=FILE_LAST_EXPERIMENT) != whenBefore:
            print("Received signal from send.py when updating last-experiment.json")
            block_last = read(file=FILE_LAST_EXPERIMENT)['send']['block_last']
            final_tps_avg = get_nearest_entry(
                tps_avg=tps_avg, block_last=block_last)
            break

        # do not query too often; as little side effect on node as possible
        time.sleep(pause_between_queries)

    print("Experiment ended! Current blocknumber = %d" % (w3.eth.blockNumber))
    return peak_tps_avg, final_tps_avg, start_epochtime


def write_measures(peak_tps_avg, final_tps_avg, start_epochtime, file=FILE_LAST_EXPERIMENT):
    with open(file, "r") as f:
        data = json.load(f)

    data["tps"] = {}
    data["tps"]["peak_tps_avg"] = peak_tps_avg
    data["tps"]["final_tps_avg"] = final_tps_avg
    data["tps"]["start_epochtime"] = start_epochtime

    with open(file, "w") as f:
        json.dump(data, f)


if __name__ == '__main__':
    global w3
    w3 = init_web3(RPCaddress=RPC_NODE_WATCH)

    print("\n Block ", w3.eth.blockNumber,
          " - waiting for something to happen")

    watch_contract()
    start_block_number = w3.eth.blockNumber
    print("\n Start Block Number:", start_block_number)

    peak_tps_avg, final_tps_avg, start_epochtime = measure(start_block_number)

    write_measures(peak_tps_avg, final_tps_avg, start_epochtime)

    print("Updated info file:", FILE_LAST_EXPERIMENT, "THE END.")
