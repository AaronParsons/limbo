import numpy as np
from .utils import DM_delay

def make_frb(times, freqs, DM=332.72, pulse_width=2.12e-3, pulse_amp=0.5, t0=2e-3,
             dtype='float32', cdtype='complex64'):
    """
    Simulates a fast radio burst (FRB) observation given a 
    certain set of parameters.
    Inputs:
        - times [s]: integration times
        - freqs [Hz]: spectral frequencies
        - DM [pc*cm^-3]: dispersion measure
        - pulse_width [s]: width of FRB pulse
        - pulse_amp: amplitude of FRB pulse
        - t0 [s]: offset the pulse start time
    Returns:
        - Power matrix of shape (ntimes, nfreqs)
    """
    dt = times[1] - times[0]
    tmid = times[times.size // 2]
    delays = DM_delay(DM, freqs)
    delays -= tmid + delays[-1] - t0  # center lowest delay at t0

    # assume same inherent profile for all freqs
    pulse = pulse_amp * np.exp(-(times - tmid)**2 / (2 * pulse_width**2))
    _pulse = np.fft.rfft(pulse).astype(cdtype)
    _ffreq = np.fft.rfftfreq(pulse.size, dt)
    phs = np.exp(-2j * np.pi * np.outer(_ffreq.astype(dtype), delays.astype(dtype)))
    _pulse_dly = np.einsum('i,ij->ij', _pulse, phs)
    return np.fft.irfft(_pulse_dly, axis=0).astype(dtype)
