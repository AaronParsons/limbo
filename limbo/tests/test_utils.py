'''Tests for limbo.io'''
import pytest

from limbo import utils, sim

import numpy as np

class TestUtils(object):
    def test_calc_inttime(self):
        inttime = utils.calc_inttime(500e6, 127, 2048)
        assert inttime == 1040384e-9

    def test_calc_freqs(self):
        freqs = utils.calc_freqs(500e6, 1350e6, 2048)
        true_freqs = np.linspace(1350e6, 1600e6, 2048, endpoint=False)
        np.testing.assert_equal(freqs, true_freqs)

    def test_DM_delay(self):
        freqs = np.linspace(1350e6, 1600e6, 2048, endpoint=False)
        DM = 0
        np.testing.assert_equal(utils.DM_delay(DM, freqs), 0)

    def test_dedisperse(self):
        times = np.linspace(0, 1, 512)
        freqs = np.linspace(1350e6, 1600e6, 2048, endpoint=False)
        DM = 350
        profile = sim.make_frb(times, freqs, DM=DM, t0=times[10])
        ans = utils.dedisperse(profile, DM, times, freqs)
        assert np.sqrt(np.sum(np.abs(ans - ans[:,-1:])**2)) < 2e-2
        
