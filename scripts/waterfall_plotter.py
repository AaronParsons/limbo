""" Generate a waterfall plot of collected data file. Change params (file name, title, and name of saved image) as needed. """

import limbo
import numpy as np
import matplotlib.pyplot as plt
import glob
import os

NSPEC = 4096
NCHANS = 2048
DATA_DIR = '/home/obs/data'

files = sorted(glob.glob(os.path.join(DATA_DIR, 'Spectra_20230210*')))

# filenames = [os.path.split(files[i])[-1] for i in range(len(files))]

#all_data = np.empty((NSPEC*(len(files)), NCHANS))
avg_data = np.empty((len(files), NCHANS))

for i in range(len(files)):
    hdr, data = limbo.io.read_file(files[i], nspec=NSPEC)
    #all_data[i*NSPEC:(i+1)*NSPEC] = data
    avg_data[i:i+1] = np.mean(data, axis=0)

fig, ax = plt.subplots(constrained_layout=True)
im = ax.imshow(avg_data.T, aspect='auto', origin='lower', extent=[4, 4*len(files), 0, NCHANS])
cbar = fig.colorbar(im, pad=0.01)
cbar.set_label('Power', rotation=270, labelpad=20)
ax.set_xlabel('Time [s]')
ax.set_ylabel('Frequency channel')
ax.set_title('Sun pointing test\n(averaged spectra)')
plt.savefig('/home/obs/limbo/images/20230210_sun_pointing_test.png')
plt.close()
