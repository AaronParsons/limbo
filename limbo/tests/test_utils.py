'''Tests for limbo.io'''
import pytest

from limbo import utils

import numpy as np

class TestUtils(object):
    def test_calc_inttime(self):
        inttime = utils.calc_inttime(500e6, 127, 2048)
        assert inttime == 1040384e-9

    def test_calc_freqs(self):
        freqs = utils.calc_freqs(500e6, 1350e6, 2048)
        true_freqs = np.linspace(1350e6, 1600e6, 2048, endpoint=False)
        np.testing.assert_equal(freqs, true_freqs)
