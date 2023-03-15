#! /usr/bin/env python

""" Pointing test for limbo. """

import limbo.telescope as telescope
import numpy as np
import subprocess
import time
import astropy.time

t = telescope.Telescope()

t_ahead = 4 # [mins]
jd_future = astropy.time.Time(time.time() + t_ahead*60, format='unix').jd
print(f'{jd_future = }')

RA, DEC = t.sunpos(jd=jd_future) # Sun
# RA, DEC = telescope.CYGA_RA, telescope.CYGA_DEC # Cyg A
# RA, DEC = telescope.CASA_RA, telescope.CASA_DEC # Cas A
alt, az = t.calc_altaz(RA, DEC, jd=jd_future)

try:
    print('Slewing...')
    t.point(alt, az)
    print('Turning on data recorder.')
    subprocess.run(['/usr/local/bin/enable_record.sh'], shell=True)
    time.sleep(30*60)
except(KeyboardInterrupt):
    print('Ending obs early... Turning off data recorder.')
    subprocess.run(['/usr/local/bin/disable_record.sh'], shell=True)
# except(AssertionError):
#     print('Turning off data recorder.')
#     subprocess.run(['/usr/local/bin/disable_record.sh'], shell=True)

finally:
    print('Turning off data recorder.')
    subprocess.run(['/usr/local/bin/disable_record.sh'], shell=True)
