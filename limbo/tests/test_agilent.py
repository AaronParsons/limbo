""" Tests for limbo.agilent """

import pytest
from limbo.agilent import Synth 

lo = Synth()

def TestAgilent:
    def test_RFout_on(self):
        lo.RFout_on()
        assert(lo._read()[0] == '1')
    
    def test_RFout_off(self):
        lo.RFout_off()
        assert(lo._read()[0] == '0')
        
    def test_get_RFout_status(self):
        lo.RFout_on()
        assert(lo.get_RFout_status() == '1')
        lo.RFout_off()
        assert(lo.get_RFout_status() == '0')
