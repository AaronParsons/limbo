import numpy as np
import os

BANDPASS_FILE = os.path.join(os.path.dirname(__file__), 'data', 'bandpass_v002.npz')
bandpass = np.load(BANDPASS_FILE)

