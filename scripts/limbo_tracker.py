#! /usr/bin/env python

""" Observing script for limbo. """

import limbo.telescope as telescope
import subprocess
import argparse
import redis
import time

REDISHOST = 'localhost'
r = redis.Redis(REDISHOST, decode_responses=True)

parser = argparse.ArgumentParser(prog='LIMBO_tracker', description = 'Track an object using the LIMBO/Leuschner telescope system')

parser.add_argument('--object', dest='object', type=str,  help='observing object', default=None, required=False)
parser.add_argument('--ra', dest='ra', type=str, help='Right ascension [hms]', default=None, required=False)
parser.add_argument('--dec', dest='dec', type=str, help='Declination [dms]', default=None, required=False)
parser.add_argument('--verbose', dest='verbose', type=bool, help='Be verbose', default=True, required=False)

args = parser.parse_args()
OBJECT = args.object
INPUT_RA = args.ra
INPUT_DEC = args.dec
VERBOSE = args.verbose

t = telescope.Telescope()

sources = {
        'sun':{'RA':t.sunpos()[0], 'DEC':t.sunpos()[1]},
        'crab':{'RA':telescope.CRAB_RA, 'DEC':telescope.CRAB_DEC},
        'sgr1935':{'RA':telescope.SGR_RA, 'DEC':telescope.SGR_DEC},
        'CygA':{'RA':telescope.CYGA_RA, 'DEC':telescope.CYGA_DEC},
        'CasA':{'RA':telescope.CASA_RA, 'DEC':telescope.CASA_DEC}
            }

if INPUT_RA is None and INPUT_DEC is None:
    RA, DEC = sources[OBJECT]['RA'], sources[OBJECT]['DEC']

if INPUT_RA and INPUT_DEC is not None:
    assert OBJECT is None, "Cannot give both input ra/dec values and specifiy an observing object."
    RA, DEC = INPUT_RA, INPUT_DEC


# Point to first coordinate values (alt, az)
ALT0, AZ0 = t.calc_altaz(RA, DEC)
print('Initial coords:', ALT0, AZ0)

in_range = False
while not in_range:
    try:
        t.point(ALT0, AZ0, wait=True, verbose=VERBOSE)
        in_range = True
    except AssertionError:
        print('Source is out of range. Waiting for it to enter range.')
        time.sleep(10*60)

t.track(RA, DEC, verbose=VERBOSE)

already_recording = False
try:
    while True:
        record = int(r.hget('limbo', 'Record'))
        if record and not already_recording:
            print('Turning on data recorders.')
            subprocess.run(['/usr/local/bin/enable_record.sh'], shell=True) # enable PS recording
            subprocess.run(['/usr/local/bin/enable_vol_record.sh'], shell=True) # enable VS recording 
            already_recording = True
        if not record and already_recording:
            print('Turning off data recorders.')
            subprocess.run(['/usr/local/bin/disable_record.sh'], shell=True) # disable PS recording
            subprocess.run(['/usr/local/bin/diable_vol_record.sh'], shell=True) # disable VS recording
            already_recording = False
except(KeyboardInterrupt):
    print('Ending observation and turning off data recorders.')
    t.stop()
    subprocess.run(['/usr/local/bin/disable_record.sh'], shell=True) 
    subprocess.run(['/usr/local/bin/disable_vol_record.sh'], shell=True) 
