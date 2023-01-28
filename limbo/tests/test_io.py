'''Tests for limbo.io'''
import pytest
import os
import numpy as np

from limbo import io
from limbo.data import DATA_PATH

class TestFileIO(object):
    def setup_method(self):
        self.filename = os.path.join(DATA_PATH, 'test.dat')

    def test_read_header(self):
        header = io.read_header(self.filename)
        assert header['filename'] == self.filename
        assert header['fpg'] == 'limbo_500_2022-12-03_1749.fpg'
        assert header['inttime'] == 2e-9 * 127 * 4096
        assert header['freqs'].size == 2048
        assert header['freqs'][0] == 1350e6

    def test_read_raw_data(self):
        data = io.read_raw_data(self.filename)
        assert data.shape == (4, 2048 + 12)
        assert data.dtype == np.dtype('>u2')
        data = io.read_raw_data(self.filename, nspec=2)
        assert data.shape == (2, 2048 + 12)

    def test_read_file(self):
        hdr, data = io.read_file(self.filename)
        assert data.shape == (4, 2048)
        assert hdr['times'].size == 4
        assert hdr['times'][0] == hdr['Time']
        np.testing.assert_almost_equal(np.diff(hdr['times']), hdr['inttime'], 6)
        assert hdr['jds'].size == 4
        hdr, data = io.read_file(self.filename, nspec=2)
        assert data.shape == (2, 2048)
        assert hdr['times'].size == 2
        assert hdr['jds'].size == 2
