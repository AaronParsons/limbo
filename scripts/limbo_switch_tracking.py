#! /usr/bin/env python

""" Switch observing script for LIMBO. This script will switch between sources (in order of priority) when one of them goes down. """

import limbo.telescope as telescope
import subprocess
import argparse
import redis
import time
from threading import Thread
import itertools

REDISHOST = 'localhost'
r = redis.Redis(REDISHOST, decode_responses=True)

parser = argparse.ArgumentParser(prog='LIMBO_switch_tracker', description = 'Track objects based on specified priority')

parser.add_argument('--sources', dest='srcs', type=list, help='observing sources (str or tuple of ra and dec)', default=None, required=False)
# parser.add_argument('--priority_source', dest='priority_src', help='Source to observe with priority', default=None, required=False)
parser.add_argument('--verbose', dest='verbose', type=bool, help='Be verbose', default=True, required=False)

args = parser.parse_args()
SRCS = args.srcs
# PRIORITY_SRC = args.priority_src
VERBOSE = args.verbose

t = telescope.Telescope()

SRCS = {
        'sgr1935':(telescope.SGR_RA, telescope.SGR_DEC),
        'crab':(telescope.CRAB_RA, telescope.CRAB_DEC),  
#         'sun':{'RA':t.sunpos()[0], 'DEC':t.sunpos()[1]},
#         'CygA':{'RA':telescope.CYGA_RA, 'DEC':telescope.CYGA_DEC},
#         'CasA':{'RA':telescope.CASA_RA, 'DEC':telescope.CASA_DEC}
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
        if tel.can_point(ra, dec, jd=jd):
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
        alt, az = t.calc_altaz(ra, dec)
        t.point(alt, az, wait=True, verbose=VERBOSE)
        t.track(ra, dec, verbose=VERBOSE)
        r.hset('limbo', 'Source', src)
        print('Turning on data recorders.')
        subprocess.run(['/usr/local/bin/enable_record.sh'], shell=True)
        subprocess.run(['/usr/local/bin/enable_vol_record.sh'], shell=True)
    current_src = src
    time.sleep(10)
    
        
        
        
    
        
        _ALT0, _AZ0 = t.calc_altaz(RA, DEC)
        t.point(_ALT0, _AZ0, wait=True, verbose=VERBOSE)
        print(f'{src} in range. Pointing to {_ALT0}, {_AZ0}.')
        in_range = True
    except AssertionError:
        print(f'{src} out of range. Moving on to next source...')
        
    if in_range:
        t.track(RA, DEC, verbose=VERBOSE)
        already_recording = False
        try:
            while True:
                record = int(r.hget('limbo', 'Record'))
                if record and not already_recording:
                    r.hset('limbo', 'Source', src)
                    print('Turning on data recorders.')
                    subprocess.run(['/usr/local/bin/enable_record.sh'], shell=True)
                    subprocess.run(['/usr/local/bin/enable_vol_record.sh'], shell=True)
                    already_recording = True
                if not record and already_recording:
                    print('Turning off data recorders.')
                    subprocess.run(['/usr/local/bin/disable_record.sh'], shell=True)
                    subprocess.run(['/usr/local/bin/disable_vol_record.sh'], shell=True)
                    already_recording = False