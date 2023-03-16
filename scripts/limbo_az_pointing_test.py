#! /usr/bin/env python

""" Azimuth pointing test for limbo. """

import limbo.telescope as telescope
import numpy as np
import subprocess
import time
import astropy.time

t = telescope.Telescope()

# RA, DEC = t.sunpos()
RA, DEC = telescope.CYGA_RA, telescope.CYGA_DEC
alt, az = t.calc_altaz(RA, DEC)
print('Slewing...')
t.point(alt, az)

A = 8 # [degrees]
f = 1/120 # 1/(120 [s])

t0 = time.time()
print('Turning on data recorder.')
subprocess.run(['/usr/local/bin/enable_record.sh'], shell=True)
try:
    while True:
        # RA, DEC = t.sunpos() # ra, dec now
        alt, az = t.calc_altaz(RA, DEC) # alt, az now
        azm = az + A * np.sin(2 * np.pi * f * (time.time()-t0)) # offset az
        # print('Delta t:', time.time() - t0)
        t.point(alt, azm)
        # print('Delta Az:', azm - az)
except(KeyboardInterrupt):
    print('Turning off data recorder.')
    subprocess.run(['/usr/local/bin/disable_record.sh'], shell=True)
except(AssertionError):
    print('Turning off data recorder.')
    subprocess.run(['/usr/local/bin/disable_record.sh'], shell=True)
