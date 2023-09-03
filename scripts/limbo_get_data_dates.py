#! /usr/env/python

import glob
import numpy as np
import os

DIR = '/home/obs/data/notebook'

if __name__ == '__main__':
    all_files = sorted(glob.glob(os.path.join(DIR, '*.ipynb')))
    digits  = [os.path.basename(file)[:16] for file in all_files]
    dates = np.unique(digits)
    keys = [d+'*' for d in dates]
    print(keys)
