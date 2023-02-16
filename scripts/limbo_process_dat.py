#! /usr/bin/env python

import limbo
import redis
import os
import time
import numpy as np

REDISHOST = 'localhost'
REDIS_RAW_PSPEC_FILES = 'limbo:raw_pspec_files'
PURGATORY_KEY = 'limbo:purgatory'
DATA_PATH = '/home/obs/data'

r = redis.Redis(REDISHOST, decode_responses=True)

def return_purgatory_files():
    purgfiles = r.hgetall(PURGATORY_KEY)
    for f in purgfiles:
        print(f'Returning {f}')
        r.rpush(REDIS_RAW_PSPEC_FILES, f)
        r.hdel(PURGATORY_KEY, f)

def filter_done(f, thd):
    is_alive = thd.is_alive()
    if not is_alive:
        purgfiles = r.hgetall(PURGATORY_KEY)
        if f in purgfiles:
            r.hdel(PURGATORY_KEY, f)
    return is_alive

def process_next(f):
    filename = os.path.join(DATA_PATH, f)
    if not os.path.exists(filename):
        print(f'Did not find {filename}.')
        return
    outfile = os.path.join(DATA_PATH, f+'.avg.npz')
    print(f'Processing {filename} -> {outfile}')
    hdr, data = limbo.io.read_file(filename)
    avg_spec = np.mean(data, axis=0)
    med_spec = np.median(data, axis=0)
    std_spec = np.std(data, axis=0)
    np.savez(outfile, avg_spec=avg_spec, med_spec=med_spec, std_spec=std_spec,
             **hdr)
    os.remove(filename)


if __name__ == '__main__':
    import multiprocessing as mp

    qlen = r.llen(REDIS_RAW_PSPEC_FILES)
    print(f'Starting LIMBO processing. Queue length={qlen}')
    children = {}
    nworkers = 2
    try:
        while True:
            qlen = r.llen(REDIS_RAW_PSPEC_FILES)
            children = {f: thd for f, thd in children.items()
                            if filter_done(f, thd)}
            print(f'Queue length={qlen}, N workers={len(children)}/{nworkers}')
            if qlen > 0 and len(children) < nworkers:
                f = r.rpop(REDIS_RAW_PSPEC_FILES)
                r.hset(PURGATORY_KEY, f, 0)
                print(f'Starting worker on {f}')
                thd = mp.Process(target=process_next, args=(f,))
                thd.start()
                children[f] = thd
            else:
                time.sleep(1)
    except Exception as e:
        print(f'Closing down {len(children)} threads')
        for f, thd in children.items():
            thd.terminate()
        for thd in children.values():
            thd.join()
    finally:
        print('Cleanup')
        return_purgatory_files()
