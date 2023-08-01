#! /usr/bin/env python

import limbo
import redis
import os
import time
import numpy as np
import subprocess

REDISHOST = 'localhost'
REDIS_PSPEC_FILES = 'limbo:pspec_to_volt'
PURGATORY_KEY = 'limbo:voltproc_purgatory'
DATA_PATH = '/home/obs/data/save/'
VOLT_NOTEBOOK_PATH = '/home/obs/data/notebook/voltbook'
VOLT_DIR = '/mnt/data01/'
VOLT_SAVE_PATH = os.path.join(VOLT_NOTEBOOK_PATH, 'recovered')
VOLT_REMOVE_PATH = os.path.join(VOLT_NOTEBOOK_PATH, 'nope')

os_env = {
    'LIMBO_PSPEC_FILE': 'None',
    'LIMBO_VOLT_REMOVE_DIR': VOLT_REMOVE_PATH,
    'LIMBO_VOLT_SAVE_DIR': VOLT_SAVE_PATH,
    'LIMBO_VOLT_DIR': VOLT_DIR,
}

r = redis.Redis(REDISHOST, decode_responses=True)

def return_purgatory_files():
    purgfiles = r.hgetall(PURGATORY_KEY)
    for f in purgfiles:
        print(f'Returning {f}')
        r.rpush(REDIS_PSPEC_FILES, f)
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
    context['LIMBO_PSPEC_FILE'] = filename
    os.environ.update(context)
    if not os.path.exists(filename):
        print(f'Did not find {filename}.')
        return
    notebook_out = os.path.join(VOLT_NOTEBOOK_PATH, 'Voltage_' + os.path.basename(filename.split('_')[-1])+'.ipynb')
    print(f'Processing {filename} -> {notebook_out}')
    print(f"jupyter nbconvert --to notebook --execute {os.path.join(os.path.dirname(limbo.__file__), 'data', 'limbo_voltage_processing_template.ipynb')} --output {notebook_out}")
#     p = subprocess.call([f"jupyter nbconvert --to notebook --execute {os.path.join(os.path.dirname(limbo.__file__), 'data', 'limbo_'+src+'_processing_template.ipynb')} --output {notebook_out}"], env=context, shell=True)
    p = subprocess.call(['jupyter-nbconvert', '--execute', '--to', 'notebook', os.path.join(os.path.dirname(limbo.__file__), 'data', 'limbo_voltage_processing_template.ipynb'), '--output', notebook_out])
    r.hdel(PURGATORY_KEY, f)
    print(f'Finished')
    


if __name__ == '__main__':
    import multiprocessing as mp

    qlen = r.llen(REDIS_PSPEC_FILES)
    print(f'Starting LIMBO VOLTAGE processing. Queue length={qlen}')
    children = {}
    nworkers = 1
    try:
        while True:
            qlen = r.llen(REDIS_PSPEC_FILES)
            children = {f: thd for f, thd in children.items()
                            if filter_done(f, thd)}
            print(f'Queue length={qlen}, N workers={len(children)}/{nworkers}')
            if qlen > 0 and len(children) < nworkers:
                f = r.rpop(REDIS_PSPEC_FILES)
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

