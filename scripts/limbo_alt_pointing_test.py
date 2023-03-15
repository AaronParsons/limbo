#! /usr/bin/env python

""" Altitude pointing test for limbo. """

import limbo.telescope as telescope
import numpy as np
import subprocess
import time
import astropy.time

t = telescope.Telescope()

RA, DEC = t.sunpos()
alt, az = t.calc_altaz(RA, DEC)
print('Slewing...')
az_offset = 0.0208 # [deg]
alt_offset = 0.014 # [deg]
t.point(alt - alt_offset, az + az_offset)

A = 5 # [degrees]
f = 1/120 # 1/(120 [s])

t0 = time.time()
print('Turning on data recorder.')
subprocess.run(['/usr/local/bin/enable_record.sh'], shell=True)
try:
    while True:
        RA, DEC = t.sunpos() # ra, dec now
        alt, az = t.calc_altaz(RA, DEC) # alt, az now
        altm = alt - alt_offset + A * np.sin(2 * np.pi * f * (time.time()-t0)) # offset az
        # print('Delta t:', time.time() - t0)
        t.point(altm, az + az_offset)
        # print('Delta Az:', azm - az)
except(KeyboardInterrupt):
    print('Turning off data recorder.')
    subprocess.run(['/usr/local/bin/disable_record.sh'], shell=True)
except(AssertionError):
    print('Turning off data recorder.')
    subprocess.run(['/usr/local/bin/disable_record.sh'], shell=True)
