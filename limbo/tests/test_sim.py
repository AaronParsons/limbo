import pytest

from limbo import sim

import numpy as np

NTIMES = 8192
NFREQ = 2048
DM = 350

class TestSim(object):
    def test_mk_frb(self):
        times = np.linspace(0, 1, NTIMES)
        freqs = np.linspace(1.150e9, 1.650e9, NFREQ)
        profile = sim.make_frb(times, freqs, DM=DM, pulse_width=0.12e-3,
                               pulse_amp=4.5, t0=10*80e-4)
        assert profile.shape == (times.size, freqs.size)
