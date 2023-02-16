# This script will determine the position of the Sun
# and point the telescope to be just ahead of the Sun
# (approx 5 mins ahead). The Sun will then travel through
# the telescope's beam.
# This is a basic pointing test.

import limbo.telescope
import astropy.units as u
import subprocess
import time

print('Getting ready...')

t = limbo.telescope.Telescope()

# Add 5 mins in RA
ra5 = 1.25*u.deg # [deg]

# Current Sun RA and DEC
sunra, sundec = t.sunpos()*u.deg # [deg]

# Compute alt, az that we will point to
alt, az = t.calc_altaz(sunra+ra5, sundec) # [deg]

# Point telescope
print('Pointing telescope.')
t.point(alt, az)

# Collect data
print('Collecting data...')
subprocess.run(['/usr/local/bin/restart_recorder.sh'], shell=True) # instantiate recorder
subprocess.run(['/usr/local/bin/enable_record.sh'], shell=True) # enable data recording
time.sleep(20*60) # collect data for 20 mins
subprocess.run(['/usr/local/bin/disable_record.sh'], shell=True) # disable data recording
#subprocess.run(['/usr/local/bin/stop_recorder.sh'], shell=True) # stop the data recorder

# Stow when finished
print('Done... Stowing telescope.')
t.stow()
