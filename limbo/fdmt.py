from .utils import DM_delay
from ._fdmt import phs_sum
from numpy.fft import rfft, irfft
import numpy as np

class FDMT:
    def __init__(self, freqs, times, maxDM=500, dtype='float32', cdtype='complex64'):
        self.cache = {}
        self.dtype = dtype
        self.cdtype = cdtype
        self.nfreqs = freqs.size
        self.ntimes = times.size
        _ffreq = np.fft.rfftfreq(self.ntimes, times[1] - times[0]).astype(dtype)
        self.stages = int(np.log2(self.nfreqs))
        chans = np.arange(self.nfreqs, dtype='uint32')
        freqs = freqs.astype(dtype)
        for i in range(1, self.stages):
            delays = DM_delay(maxDM / 2**i, freqs) - DM_delay(maxDM / 2**i, freqs[-1])
            phs = np.exp(2j * np.pi * np.outer(_ffreq, delays))
            freqs = (freqs[0::2] + freqs[1::2]) / 2
            self.cache[i] = phs.astype(cdtype)
            
    def phs_sum(self, d, phs):
        phs_sum(d, phs)
        return [d[:,0::2], d[:,1::2]]
            
    def apply(self, profile):
        self._data = rfft(profile, axis=0).astype(self.cdtype)
        ans = [self._data]
        for i in range(1, self.stages):
            ans = sum([self.phs_sum(d, self.cache[i]) for d in ans], [])
        return np.concatenate([irfft(d, axis=0) for d in ans], axis=1)
