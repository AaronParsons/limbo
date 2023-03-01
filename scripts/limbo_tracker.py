#! /usr/bin/env python

""" Observing script for limbo. """

import limbo.telescope as telescope
import subprocess
import argparse
import redis

REDISHOST = 'localhost'
r = redis.Redis(REDISHOST, decode_responses=True)

parser = argparse.ArgumentParser(prog='LIMBO_tracker', description = 'Track an object using the LIMBO/Leuschner telescope system')

parser.add_argument('--object', dest='object', type=str,  help='observing object', choices=['sun', 'sgr1935', 'crab', 'CygA'], default=None, required=False)
parser.add_argument('--ra', dest='ra', type=str, help='Right ascension [hms]', default=None, required=False)
parser.add_argument('--dec', dest='dec', type=str, help='Declination [dms]', default=None, required=False)
parser.add_argument('--verbose', dest='verbose', type=bool, help='Be verbose', default=False, required=False)

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
        'CygA':{'RA':telescope.CYGA_RA, 'DEC':telescope.CYGA_DEC}
            }

if INPUT_RA is None and INPUT_DEC is None:
    assert OBJECT in sources, 'Observing object was not specified.'
    RA, DEC = sources[OBJECT]['RA'], sources[OBJECT]['DEC']

if INPUT_RA and INPUT_DEC is not None:
    assert OBJECT is None, "Cannot give both input ra/dec values and specifiy an observing object."
    RA, DEC = INPUT_RA, INPUT_DEC


# Point to first coordinate values (alt, az)
ALT0, AZ0 = t.calc_altaz(RA, DEC)
print('Slewing...')
t.point(ALT0, AZ0, wait=True, verbose=VERBOSE)

t.track(RA, DEC, verbose=VERBOSE)

already_recording = False
try:
    while True:
        record = r.hget('limbo:Record')
        if record == 1 and not already_recording:
            subprocess.run(['/usr/local/bin/enable_record.sh'], shell=True) # enable data recording
            already_recording = True
        if record == 0 and already_recording:
            subprocess.run(['/usr/local/bin/disable_record.sh'], shell=True) # disable data recording
            already_recording = False
except(KeyboardInterrupt):
    t.stop()
    subprocess.run(['/usr/local/bin/disable_record.sh'], shell=True) # disable data recording
    t.stow()
