import pytest

from limbo.fdmt import FDMT
from limbo import sim

import numpy as np

NTIMES = 8192
NFREQ = 2048
DM = 350

class TestFDMT(object):
    def test_fdmt(self):
        times = np.linspace(0, 1, NTIMES)
        freqs = np.linspace(1.150e9, 1.650e9, NFREQ)
        profile = sim.make_frb(times, freqs, DM=DM, pulse_width=0.12e-3,
                               pulse_amp=4.5, t0=10*80e-4)
        fdmt = FDMT(freqs, times)
        data = fdmt.apply(profile)
        assert data.shape == (NTIMES, NFREQ)
        maxDM = 500
        t0, dm0 = inds = np.unravel_index(np.argmax(data, axis=None), data.shape)
        assert np.abs(times[t0] - 10 * 80e-4) < 1/NTIMES + 0.12e-3
        assert np.abs(DM - np.linspace(0, maxDM, NFREQ)[dm0]) < 2.2 * maxDM / NFREQ
