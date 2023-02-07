""" Module for pointing Leuschner Telescope. Copied from ugradio. """

import numpy as np
import socket
import time
from astropy.coordinates import EarthLocation, SkyCoord
import astropy.time as Time
import astropy.units as u
from threading import Thread

# Coordinates of Leuschner Educational Observatory
LAT = 37.9183  # deg
LON = -122.1067  # deg
HEIGHT = 304.0  # m

# Hardware parameters
MAX_SLEW_TIME = 220 # [s]

ALT_MIN, ALT_MAX = 15., 85. # Pointing bounds, [degrees]
AZ_MIN, AZ_MAX  = 5., 350. # Pointing bounds, [degrees]

ALT_STOW, AZ_STOW = 80., 180. # Position for stowing antenna [degrees]
ALT_MAINT, AZ_MAINT = 20., 180. # Position for antenna maintenance [degrees]

ANT_HOSTNAME = '192.168.1.156' # RPI host for antenna
NOISE_SERVER_HOSTNAME = '192.168.1.90' # RPI host for noise diode
PORT = 1420

# Offsets [degrees] to subtract from crd to get encoder value to write
DELTA_ALT_ANT = -0.30  # (true - encoder) offset
DELTA_AZ_ANT  = -0.13  # (true - encoder) offset

CMD_MOVE_AZ = 'moveAz'
CMD_MOVE_ALT = 'moveEl'
CMD_WAIT_AZ = 'waitAz'
CMD_WAIT_ALT = 'waitEl'
CMD_GET_AZ = 'getAz'
CMD_GET_ALT = 'getEl'


# RA and DEC of SGR 1935+2154 (from McGill Online Magnetar Catalog)
SGR_RA, SGR_DEC = '19h34m55.598s', '+21d53m47.79s'

class Telescope:
    """
    Interface for controlling the Leuschner Telescope. Copied from ugradio.
    """
    def __init__(self, host=ANT_HOSTNAME, port=PORT,
                 lat=LAT, lon=LON, hgt=HEIGHT,
                 delta_alt=DELTA_ALT_ANT, delta_az=DELTA_AZ_ANT):
        self.hostport = (host, port)
        self.location = EarthLocation(
                            lat=lat * u.deg,
                            lon=lon * u.deg,
                            height=hgt * u.m,
        )
        self._delta_alt = delta_alt
        self._delta_az = delta_az
        self.observing = False # observation flag
        self.ALT_STOW, self.AZ_STOW = ALT_STOW, AZ_STOW
        self.ALT_MAINT, self.AZ_MAINT = ALT_MAINT, AZ_MAINT
        self.ALT_MIN, self.ALT_MAX = ALT_MIN, ALT_MAX
        self.AZ_MIN, self.AZ_MAX = AZ_MIN, AZ_MAX

    def _check_pointing(self, alt, az):
        """
        Ensure pointing is within telescope bounds. Raises
        AssertionError if not.
        Inputs:
            - alt: altitude
            - az: azimuth
        """
        assert(self.ALT_MIN < alt < self.ALT_MAX)
        assert(self.AZ_MIN < az < self.AZ_MAX)

    def _command(self, cmd, bufsize=1024, timeout=10, verbose=False):
        """
        Communicate with host server and return response as string.
        """
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout) # [s]
        s.connect(self.hostport)
        if verbose: print('Sending', [cmd])
        s.sendall(bytes(cmd, encoding='utf8'))
        response = []
        while True: # XXX don't like while True
            r = s.recv(bufsize)
            response.append(r)
            if len(r) < bufsize: break
        response = b''.join(response)
        if verbose: print('Got response:', [response])
        return response

    def wait(self, verbose=False):
        """
        Wait until telescope slewing is complete.
        Inputs:
            - verbose (bool): be verbose
                Default=False
        """
        resp1 = self._command(CMD_WAIT_AZ,  timeout=MAX_SLEW_TIME, verbose=verbose)
        resp2 = self._command(CMD_WAIT_ALT, timeout=MAX_SLEW_TIME, verbose=verbose)
        assert((resp1 == b'0') and (resp2 == b'0')) # fails if server is down or rejects command
        if verbose: print('Pointing complete.')

    def point(self, alt, az, wait=True, verbose=False):
        """
        Point to specified (alt, az) coordinates.
        Inputs:
            - alt (float)|[degrees]: altitude angle to point to
            - az (float)|[degrees]: azimuth angle to point to
            - wait (bool): pause until antenna has completed pointing
                Default=True
            - verbose (bool): be verbose
                Default=False
        """
        self._check_pointing(alt, az) # Check coordinates are within bounds
        # Request encoded alt/az with calibrated offset
        resp1 = self._command(CMD_MOVE_AZ+'\n%s\r' % (az - self._delta_az), verbose=verbose)
        resp2 = self._command(CMD_MOVE_ALT+'\n%s\r' % (alt - self._delta_alt), verbose=verbose)
        assert((resp1 == b'ok') and (resp2 == b'ok')) # Fails if server is down or rejects command
        if verbose: print('Pointing initiated.')
        if wait: self.wait(verbose=verbose)

    def get_pointing(self, verbose=False):
        """
        Return current telescope's current pointing coordinate.
        Inputs:
            - verbose (bool): be verbose
                Default=False
        Returns:
            - alt (float)|[degrees]: altitude angle
            - az (float)|[degrees]: azimuth angle
        """
        alt = float(self._command(CMD_GET_ALT, verbose=verbose))
        az = float(self._command(CMD_GET_AZ, verbose=verbose))
        # Return true (alt, az) corresponding to encoded position
        return alt + self._delta_alt, az + self._delta_az

    def stow(self, wait=True, verbose=False):
        """
        Point to stow position.
        Inputs:
            - wait (bool): pause until antenna has completed pointing
                Default=True
            - verbose (bool): be verbose
                Default=False
        """
        self.point(alt=self.ALT_STOW, az=self.AZ_STOW, wait=wait, verbose=verbose)

    def maintenance(self, wait=True, verbose=False):
        """
        Point to maintenance position.
        Inputs:
            - wait (bool): pause until antenna has completed pointing
                Default=True
            - verbose (bool): be verbose
                Default=False
        """
        self.point(self.ALT_MAINT, self.AZ_MAINT, wait=wait, verbose=verbose)

    def calc_altaz(self, ra, dec, jd=None):
        """
        Convert (ra, dec) to (alt, az).
        Inputs:
            - ra (str)|[hms]: Right ascension in [hours, arcmins, arcsecs]
            - dec (str)|[dms]: Declination in [degrees, arcmins, arcsecs]
            - jd (float): Julian date
        """
        if jd: t = Time(jd, format='jd')
        else: t = Time(time.time(), format='unix')
        c = SkyCoord(ra=ra, dec=dec, frame='icrs')
        altaz = c.transform_to(AltAz(obstime=t, location=self.location))
        return altaz.alt.degree, altaz.az.degree

    def sunpos(self, jd=None):
        """
        Returns the ra and dec (in degrees) of the Sun.
        """
        if jd: t = Time(jd, format='jd')
        else: t = Time(time.time(), format='unix')
        sun_coords = astropy.coordinates.get_sun(time=t)
        return sun_coords.ra.deg, sun_coords.dec.deg

    def sgr1935_pos(self):
        """
        Returns the ra and dec (in degrees) of SGR 1935+2154.
        Ra and  dec values taken from the McGill online magnetar
        catalog.
        """
        sgr = SkyCoord(SGR_RA, SGR_DEC, frame='icrs')
        return sgr.ra.deg, sgr.dec.deg

    def track_sun(self, sleep_time=5, flag_time=0.1, verbose=False):
        """
        Track the Sun.
        Inputs:
            - sleep_time (float)|[s]: Time to wait in between telescope points
                Default=5
            - verbose (bool): Be verbose
                Default=False
        Returns: None
        """
        sun_ra, sun_dec = self.sunpos()
        self.track(sun_ra, sun_dec, sleep_time, flag_time, verbose)

    def track_sgr1935(self, sleep_time=5, flag_time=0.1, verbose=False):
        """
        Track SGR 1935+2154.
        Inputs:
            - sleep_time (float)|[s]: Time to wait in between telescope points
                Default=5
            - verbose (bool): Be verbose
                Default=False
        Returns: None
        """
        sgr_ra, sgr_dec = self.sgr1935_pos()
        self.track(sgr_ra, sgr_dec, sleep_time, flag_time, verbose)

    def track(self, ra, dec, sleep_time=5, flag_time=0.1, verbose=False):
        """
        Track an object.
        Inputs:
            - ra (str)|[hms]: Right ascension in [hours, arcmins, arcsecs]
            - dec (str)|[dms]: Declination in [degrees, arcmins, arcsecs]
            - sleep_time (float)|[s]: Time to wait before repointing
                Default=5
            - flag_time (float)|[s]: Time to wait before rechecking if
             observing flag has changed states
                 Default=0.1
            - verbose (bool): Be verbose
                Default=False
        Returns: None
        """
        assert(sleep_time > flag_time)
        self.observing = True
        self.thread = threading.Tread(target=self._track, args=(ra, dec, sleep_time, flag_time, verbose))
        self.thread.start()

    def _track(self, ra, dec, sleep_time, flag_time, verbose):
        """
        Waits to see if observing flag has changed states. If observing
        then compute new alt, az and point.
        Inputs:
            - ra (str)|[hms]: Right ascension in [hours, arcmins, arcsecs]
            - dec (str)|[dms]: Declination in [degrees, arcmins, arcsecs]
            - sleep_time (float)|[s]: Time to wait before repointing
            - flag_time (float)|[s]: Time to wait before rechecking if
             observing flag has changed states
            - verbose (bool): Be verbose
        Returns: None
        """
        t0 = 0
        while self.observing:
            if time.time() - t0 > sleep_time:
                alt, az = self.calc_altaz(ra, dec)
                self.point(alt, az, wait=True, verbose=verbose)
                t0 = time.time()
            time.sleep(flag_time)

    def stop(self):
        """
        End observation.
        """
        self.observing = False
        self.thread.join()


CMD_NOISE_ON = 'on'
CMD_NOISE_OFF = 'off'

class Noise:
    """
    Interface for controlling noise diode on Leuschner dish.
    """
    def __init__(self, host=NOISE_SERVER_HOSTNAME, port=PORT, verbose=False):
        self.hostport = (host, port)
        self.verbose = verbose

    def on(self):
        """
        Turn Leuschner noise diode on.
        """
        self._cmd(CMD_NOISE_ON)

    def off(self):
        """
        Turn Leuschner noise diode off.
        """
        self._cmd(CMD_NOISE_OFF)

    def _cmd(self, cmd):
        """
        Low-level interface for sending commands to LeuschnerNoiseServer.
        """
        assert(cmd in (CMD_NOISE_ON, CMD_NOISE_OFF)) # Check if valid command
        if self.verbose: print('LeuschnerNoise sending command:', [cmd])
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(self.hostport)
        s.sendall(bytes(cmd, encoding='utf8'))
