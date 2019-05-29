#!/usr/bin/env python3
"""
@summary: Timing transactions that are getting into the chain
"""
import os
import time
import timeit
import json

# extend path for imports:
if __name__ == '__main__' and __package__ is None:
    from os import sys, path
    sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

from config import RPC_NODE_WATCH, FILE_LAST_EXPERIMENT, FILE_CONTRACT_ADDRESS, FILE_CONTRACT_ABI, FILE_CONTRACT_BIN
from deploy import load_contract
from utils import init_web3, file_date


class CodingError(Exception):
    pass

def wait_file(file=FILE_LAST_EXPERIMENT, interval=0.1):
    """
    Waits for `FILE_LAST_EXPERIMENT` to be initiated.
    It signals that accounts were already funded.
    """
    when = file_date(file)
    print("Waiting %s to be initiated" % file)
    while True:
        time.sleep(interval)
        new_when = file_date(file)
        if new_when != when:
            break
    return

def watch_contract():
    address, _, _ = load_contract(file_address=FILE_CONTRACT_ADDRESS, file_abi=FILE_CONTRACT_ABI, file_bin=FILE_CONTRACT_BIN)
    print("\n Last contract address: %s" % (address))
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
    print(line % (new_block_num, tx_count_new, block_time_sec * 1000,
                  tps_current, tx_count, elapsed, tps_avg, verb, peak_tps_avg))
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
            raise CodingError(
                "Ouch, this should never happen. Info: len(tps_avg)=%d block_last=%d" % (
                    len(tps_avg), block_last)
            )
        answer = tps_avg.get(i, None)
    return answer

def measure(block_num, pause_between_queries=0.3, relaxation_rounds=1):
    """
    when a (or more) new block appeared, add them to the total, and print a line.
    """
    when_before = file_date(file=FILE_LAST_EXPERIMENT)

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
        if file_date(file=FILE_LAST_EXPERIMENT) != when_before:
            print("Received signal from send.py when updating last-experiment.json")
            block_last = json.load(open(FILE_LAST_EXPERIMENT, 'r'))['send']['block_last']
            final_tps_avg = get_nearest_entry(tps_avg, block_last)
            break

        # do not query too often; as little side effect on node as possible
        time.sleep(pause_between_queries)

    print("Experiment ended! Current blocknumber = %d" % (w3.eth.blockNumber))
    write_measures(peak_tps_avg, final_tps_avg, start_epochtime)

def write_measures(peak_tps_avg, final_tps_avg, start_epochtime, file=FILE_LAST_EXPERIMENT):
    with open(file, "r") as f:
        data = json.load(f)

    data["tps"] = {}
    data["tps"]["peak_tps_avg"] = round(peak_tps_avg, 1)
    data["tps"]["final_tps_avg"] = round(final_tps_avg, 1)
    data["tps"]["start_epochtime"] = start_epochtime

    with open(file, "w") as f:
        json.dump(data, f)

    print("Experiment results writen on", FILE_LAST_EXPERIMENT)


if __name__ == '__main__':
    global w3
    w3 = init_web3(RPCaddress=RPC_NODE_WATCH)

    wait_file()
    watch_contract()

    start_block_number = w3.eth.blockNumber
    print("\n Start Block Number:", start_block_number)

    measure(start_block_number)
