""" Tests for limbo.telescope """

import pytest
from limbo.telescope import Telescope


JD = 2458500.3

telescope = Telescope()

class TestTelescope:

    def test_check_pointing(self):
        with pytest.raises(AssertionError):
            telescope._check_pointing(10, 50)
        with pytest.raises(AssertionError):
            telescope._check_pointing(90, 50)
        with pytest.raises(AssertionError):
            telescope._check_pointing(50, 0)
        with pytest.raises(AssertionError):
            telescope._check_pointing(50, 355)

    # pointing tests:
    def test_alt20(self):
        ALT = 20.
        AZ = telescope.AZ_STOW
        telescope.point(ALT, AZ, wait=True)
        alt, az = telescope.get_pointing()
        assert alt == pytest.approx(ALT, 1)

    def test_alt50(self):
        ALT = 50.
        AZ = telescope.AZ_STOW
        telescope.point(ALT, AZ, wait=True)
        alt, az = telescope.get_pointing()
        assert alt == pytest.approx(ALT, 1)

    def test_alt75(self):
        ALT = 75.
        AZ = telescope.AZ_STOW
        telescope.point(ALT, AZ, wait=True)
        alt, az = telescope.get_pointing()
        assert alt == pytest.approx(ALT, 1)

    def test_az300(self):
        ALT = telescope.ALT_STOW
        AZ = 300.
        telescope.point(ALT, AZ, wait=True)
        alt, az = telescope.get_pointing()
        assert az == pytest.approx(AZ, 1)

    def test_alt225(self):
        ALT = telescope.ALT_STOW
        AZ = 225.
        telescope.point(ALT, AZ, wait=True)
        alt, az = telescope.get_pointing()
        assert az == pytest.approx(AZ, 1)

    def test_alt35(self):
        ALT = telescope.ALT_STOW
        AZ = 35.
        telescope.point(ALT, AZ, wait=True)
        alt, az = telescope.get_pointing()
        assert az == pytest.approx(AZ, 1)

    def test_sunpos(self):
        ra, dec = telescope.sunpos(jd=JD)
        assert ra == pytest.approx(298.099, 0.01)
        assert dec == pytest.approx(-20.927, 0.01)
