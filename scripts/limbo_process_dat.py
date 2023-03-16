#! /usr/bin/env python

import limbo
import redis
import os
import time
import numpy as np
import subprocess

REDISHOST = 'localhost'
REDIS_RAW_PSPEC_FILES = 'limbo:raw_pspec_files'
PURGATORY_KEY = 'limbo:purgatory'
DATA_PATH = '/home/obs/data'
REMOVE_PATH = os.path.join(DATA_PATH, 'remove')
SAVE_PATH = os.path.join(DATA_PATH, 'save')
NOTEBOOK_PATH = os.path.join(DATA_PATH, 'notebook')
TEMPLATE_FILE = os.path.join(os.path.dirname(__file__), 'data', 'limbo_processing_template.ipynb')

os_env = {
    'LIMBO_PROCFILE': None,
    'LIMBO_INJECT_FRB': False,
    'LIMBO_NSIG': 7,
    'LIMBO_MAX_DM': 500,
    'LIMBO_EXCLUDE_S': 0.05,
    'LIMBO_REMOVE_DIR': REMOVE_PATH,
    'LIMBO_SAVE_DIR': SAVE_PATH,
}


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
    context = os_env.copy()
    context['LIMBO_PROCFILE'] = filename
    if not os.path.exists(filename):
        print(f'Did not find {filename}.')
        return
    notebook_out = os.path.join(NOTEBOOK_PATH, filename+'.ipynb')
    print(f'Processing {filename} -> {notebook_out}')

    subprocess.Popen(['jupyter', 'nbconvert', '--to', 'notebook', '--execute', TEMPLATE_FILE, '--output', notebook_out], env=context)


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
