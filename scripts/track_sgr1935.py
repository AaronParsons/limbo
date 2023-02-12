import limbo
import subprocess

t = limbo.telescope.Telescope()

sgr_ra, sgr_dec = limbo.telescope.SGR_RA, limbo.telescope.SGR_DEC
sgr_alt0, sgr_az0 = t.calc_altaz(sgr_ra, sgr_dec)

t.point(sgr_alt0, sgr_az0, wait=True)

subprocess.run(['/usr/local/bin/restart_recorder.sh'], shell=True) # instantiate recorder
subprocess.run(['/usr/local/bin/enable_record.sh'], shell=True) # enable data recording

try:
    t.track_sgr1935()
except(AssertionError):
    t.stop()
    subprocess.run(['/usr/local/bin/disable_record.sh'], shell=True) # disable data recording

