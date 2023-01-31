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

DM_CONST = 4140e12 # s Hz^2 / (pc / cm^3)

def DM_delay(DM, freq):
    """
    Computes the frequency-dependent dispersion measure
    time delay.
    Inputs:
        - DM [pc*cm^-3]: dispersion measure
        - freq [Hz]: frequency
    Returns:
        - Pulse time delay in [s] 
    """
    return np.float32(DM * DM_CONST) / freq**2

def dedisperse(profile, DM, times, freqs):
    _ffreq = np.fft.rfftfreq(times.size, times[1] - times[0])
    delays = DM_delay(DM, freqs) - DM_delay(DM, freqs[-1])
    phs = np.exp(2j * np.pi * np.outer(_ffreq, delays))
    _profile = np.fft.rfft(profile, axis=0)
    profile = np.fft.irfft(_profile * phs, axis=0)
    return profile
