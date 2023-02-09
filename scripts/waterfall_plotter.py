""" Generate a waterfall plot of collected data file. Change params (file name, title, and name of saved image) as needed. """

import limbo
import numpy as np
import matplotlib.pyplot as plt
import glob
import os

NSPEC = 4096
NCHANS = 2048
DATA_DIR = '/home/obs/data'

files = sorted(glob.glob(os.path.join(DATA_DIR, '*Spectra_20230209')))

# filenames = [os.path.split(files[i])[-1] for i in range(len(files))]

all_data = []
for i in range(len(files)):
    hdr, data = limbo.io.read_file(files[i], nspec=NSPEC)
    all_data.append(data)
all_data = np.array(all_data)
all_data = all_data.reshape((NSPEC*(len(files)), NCHANS))

fig = plt.figure()
plt.imshow(all_data.T, aspect='auto', origin='lower')
plt.ylabel('Frequency channel')
plt.xlabel('Time [ms]')
plt.title('Sun pointing test')
plt.savefig('/home/obs/Pictures/sun_pointing_test.png')
plt.close()
