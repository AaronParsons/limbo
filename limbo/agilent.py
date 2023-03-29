"""
Module for interacting with the Agilent N9130a Frequency Synthesizer. Copied from ugradio.
"""

import socket
import time

DEVICE = '/dev/usbtmc0' # default mounting point
HOST, PORT = '10.32.92.95', 1341
WAIT = 0.3 # s

FREQ_UNIT = ['GHz','MHz','kHz']
AMP_UNIT = ['dBm','mV','uV']


class Synth:
    """
    Instantiate connection to the Agilent frequency synthesizer.
    """
    def validate(self):
        """
        Make sure this is the device we think it is.
        """
        self._write('*IDN?') # query ID
        resp = self._read().strip()
        resp = resp.split(',')
        assert(resp[0] == 'Agilent Technologies')

    def get_frequency(self):
        """
        Get the current frequency setting for the CW (continuous wave)
        output mode of the synthesizer.
        
        Inputs: None
        Returns:
            - freq (float): Numerical frequency setting
            - unit (str): Units of freq (GHz, MHz, or kHz)
        """
        self._write(':FREQuency:CW?')
        resp = self._read()
        freq, unit = resp.split()
        return float(freq), unit

    def set_frequency(self, freq, unit):
        """ Set the frequency of the CW (continuous wave) output
        mode of the synthesizer.

        Inputs:
            - freq (float): Numerical frequency setting
            - unit (str): Units of freq ('GHz', 'MHz', 'kHz')
        Returns: None
        """
        assert(unit in FREQ_UNIT)
        cmd = ':FREQuency:CW %f %s' % (val, unit)
        sef._write(cmd)

    def get_amplitude(self):
        """
        Get the current amplitude setting for the CW (continuous wave) 
        output mode of the synthesizer.

        Inputs: None
        Returns:
            - amp (float): Numerical amplitide setting
            - unit (str): Units of amp ('dBm', 'mV', 'uV')
        """
        self._write(':AMPLitude:CW?')
        resp = self._read()
        amp, unit = resp.split()
        return float(amp), unit

    def set_amplitude(self, amp, unit):
        """
        Set the amplitude setting for the CW (continuous wave) output 
        mode of the synthesizer.

        Inputs: 
            - amp (float): Numerical amplitide setting
            -unit (str): Units of amp ('dBm', 'mV', 'uV')
        Returns: None
        """
        assert (unit in AMP_UNIT)
        cmd = ':AMPLitude:CW %f %s' % (amp, unit)
        self._write(cmd)

    def get_RFout_status(self):
        """
        Get the RFout status of the synthesizer.
        If RFout is on, a '1' is returned. If the RFout is off,
        a '0' is returned.
        """
        self._write(':RFOutput:STATe?')
        status = self._read()[0] # read first bit
        if status == '1': return 1
        elif status == '0': return 0

    def RFout_on(self):
        """
        Turn RFout on.
        """
        self._write(':RFOutput:STATe ON')

    def RFout_off(self):
        """
        Turn RFout off.
        """
        self._write(':RFOutput:STATe OFF')


class SynthDirect(Synth):
    """
    Implements a direct connection to the synthesizer via a USB
    connection (typically device='/dev/usbtmc0' or similar.)
    """
    def __init__(self, device=DEVICE):
        """
        Inputs:
            - device (str): the file-like object representing the USB
              connection. Default='/dev/usbtmc0'
        """
        self._device = device
        self._open_device()

    def _open_device(self):
        """
        Open low-level device interface. Not intended for direct use.
        """
        try: 
            self.dev.close()
        except(AttributeError):
            pass
        self.dev = open(self._device, 'rb+')
        self.validate()

    def _write(self, cmd):
        """
        Low-level writing interface to device. Not intended for direct
        use.
        """
        self.dev.write(bytes(cmd, encoding='utf-8'))
        self.dev.flush()
        time.sleep(WAIT) # slow down writing to avoid spam attacks

    def _read(self):
        """
        Low-level reading interface to device. Not intended for direct
        use.
        """
        rv = []
        while True:
            try:
                rv.append(self.dev.read(1))
            except(TimeoutError):
                break
        rv = b''.join(rv)
        return rv.decode('utf-8')

