'''Utility functions for LIMBO'''

import numpy as np
from scipy.fft import rfft, irfft
from scipy.optimize import curve_fit

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

def dedisperse(profile, dm, freqs, inttime, oversample=1, dtype=None):
    if dtype is None:
        dtype = 1
        if profile.dtype.itemsize > 4:
            dtype = 2
    assert dtype in (1, 2)
    if dtype == 1:
        dtype = 'float32'
        cdtype = 'complex64'
    else:
        dtype = 'float64'
        cdtype = 'complex128'
    _ffreq = np.fft.rfftfreq(profile.shape[0], inttime).astype(dtype)
    delays = DM_delay(dm, freqs) - DM_delay(dm, freqs[-1])
    delays = delays.astype(dtype)
    phs = np.exp(np.asarray(2j * np.pi).astype(cdtype) * np.outer(_ffreq, delays))
    _profile = rfft(profile, axis=0)
    profile = irfft(_profile * phs, oversample * profile.shape[0], axis=0) * oversample
    return profile

def _line(x, m, b):
    return m*x + b

def _linear_fit(x, y, m0, b0, return_cov=False):
    pars0 = [m0, b0]
    pars, cov = curve_fit(_line, x, y, p0=pars0)
    if return_cov:
        return pars, cov
    else:
        return pars

def calc_fluence(vts, fluxes, vhdr, sum_int, nbins):
    """
    Compute pulse fluence.
    Inputs:
        - vts [s]: times
        - fluxes [Jy]: flux data (average over frequency and de-dispersed)
        - vhdr: volt header
        - sum_int: how many integrations are summed together
        - nbins: number of time bins to compute fluence over
       
    Returns:
        - Fluence and its error [Jyms]
    """
    noise = np.random.normal(loc=0, scale=np.abs(np.std(fluxes)), size=nbins * 2)
    blanked_profile = fluxes.copy()
    pulse_max = np.argmax(fluxes)
    blanked_profile[pulse_max-nbins:pulse_max+nbins] = noise
    pars, cov = _linear_fit(vts, blanked_profile, 0, 0, return_cov=True)
    m, b = pars
    dm, db = np.sqrt(np.diag(cov))
    fit = _line(vts, m, b)
    fluence = np.sum((fluxes - fit)[pulse_max-nbins:pulse_max+nbins]) * (vhdr['inttime']*sum_int*1e3)
    dFdm = -0.5 * (vhdr['inttime']*sum_int*1e3)**2 * dm * 1e-3
    dFdb = -vhdr['inttime']*sum_int*1e3 * db
    err_noise = np.std(blanked_profile - fit) * vhdr['inttime']*sum_int*1e3
    fluence_err = dFdm + dFdb + err_noise
    return fluence, fluence_err
