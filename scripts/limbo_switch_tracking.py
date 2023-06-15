#! /usr/bin/env python

""" Switch observing script for LIMBO. This script will switch between sources (in order of priority) when one of them goes down. """

import limbo.telescope as telescope
import subprocess
import argparse
import redis
import time

REDISHOST = 'localhost'
r = redis.Redis(REDISHOST, decode_responses=True)

parser = argparse.ArgumentParser(prog='LIMBO_switch_tracker', description = 'Track objects based on specified priority')

parser.add_argument('--verbose', dest='verbose', type=bool, help='Be verbose', default=True, required=False)

args = parser.parse_args()
VERBOSE = args.verbose

t = telescope.Telescope()

# NOTE: Sources are listed in order of priority
SRCS = {
        'sgr1935':(telescope.SGR_RA, telescope.SGR_DEC),
        'crab':(telescope.CRAB_RA, telescope.CRAB_DEC)
        }

def can_point(ra, dec, jd=None):
    alt, az = t.calc_altaz(ra, dec, jd=jd)
    try:
        t._check_pointing(alt, az)
        return True
    except(AssertionError):
        return False

def select_src(tel, jd=None, srcs=SRCS):
    source = None
    for name, (ra, dec) in SRCS.items():
        if can_point(ra, dec, jd=jd):
            source = name
            break
    if source == None:
        return None, (None, None)
    return source, (ra, dec)

current_src = None
while True:
    src, (ra, dec) = select_src(t)
    
    if current_src != None and current_src != src:
        print('Turning off data recorders.')
        subprocess.run(['/usr/local/bin/disable_record.sh'], shell=True)
        subprocess.run(['/usr/local/bin/disable_vol_record.sh'], shell=True)
        t.stop()
    
    if current_src != src and src != None:
        print(f'Starting observation of {src}')
        alt, az = t.calc_altaz(ra, dec)
        t.point(alt, az, wait=True, verbose=VERBOSE)
        t.track(ra, dec, verbose=VERBOSE)
        r.hset('limbo', 'Source', src)
        print('Turning on data recorders.')
        subprocess.run(['/usr/local/bin/enable_record.sh'], shell=True)
        subprocess.run(['/usr/local/bin/enable_vol_record.sh'], shell=True)
    current_src = src
    print('No source is visible right now.')
    time.sleep(10)
