#! /usr/bin/env python

import limbo.telescope as telescope
import subprocess
import argparse

parser = argparse.ArgumentParser(prog='LIMBO_tracker', description = 'Track an object using the LIMBO/Leuschner telescope system')

parser.add_argument('--object', dest='object', type=str,  help='observing object', choices=['sun', 'sgr1935', 'crab'], default=None, required=False)
parser.add_argument('--ra', dest='ra', type=str, help='Right ascension [hms]', default=None, required=False)
parser.add_argument('--dec', dest='dec', type=str, help='Declination [dms]', default=None, required=False)
parser.add_argument('--verbose', dest='verbose', type=bool, help='Be verbose', default=False, required=False)

args = parser.parse_args()
OBJECT = args.object
INPUT_RA = args.ra
INPUT_DEC = args.dec
VERBOSE = args.verbose

if INPUT_RA is None and INPUT_DEC is None:
    assert OBJECT is not None, "Observing object was not specified."
    if OBJECT == 'sun':
        RA, DEC = telescope.SUN_RA, telescope.SUN_DEC
    elif OBJECT == 'sgr1935':
        RA, DEC = telescope.SGR_RA, telescope.SGR_DEC
    elif OBJECT == 'crab':
        RA, DEC = telescope.CRAB_RA, telescope.CRAB_DEC
if INPUT_RA and INPUT_DEC is not None:
    assert OBJECT is None, "Cannot give both input ra/dec values and specifiy an observing object."
    RA, DEC = INPUT_RA, INPUT_DEC


t = telescope.Telescope()

# Point to first coordinate values (alt, az)
ALT0, AZ0 = t.calc_altaz(RA, DEC)
print('Slewing...')
t.point(ALT0, AZ0, wait=True, verbose=VERBOSE)

# Start collecting data
subprocess.run(['/usr/local/bin/enable_record.sh'], shell=True) # enable data recording

print('Tracking '+ OBJECT)
try:
    t.track(RA, DEC, verbose=VERBOSE)
except(AssertionError): # if object is out of bounds
    print('Source is out of range. Finishing observation.')
    t.stop()
    subprocess.run(['/usr/local/bin/disable_record.sh'], shell=True) # disable data recording
    print('Stowing...')
    t.stow()
