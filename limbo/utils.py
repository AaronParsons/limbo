'''Utility functions for LIMBO'''

import numpy as np

def calc_inttime(sample_freq_hz, acc_len, nchan):
    '''Calculate integration time [s] from sample_freq and acc_len.'''
    dt_sample = 1 / sample_freq_hz
    dt_spectrum = dt_sample * (2 * nchan)  # assumes real sampling
    inttime = dt_spectrum * acc_len
    return inttime

def calc_freqs(sample_freq_hz, lo_hz, nchan):
    '''Calculate frequencies [Hz] from sample_freq and lo.'''
    baseband = np.linspace(0, sample_freq_hz/2, nchan, endpoint=False)
    freqs = lo_hz + baseband
    return freqs
    
