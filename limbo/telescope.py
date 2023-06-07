""" Module for pointing Leuschner Telescope. Copied from ugradio. """

import numpy as np
import socket
import time
import astropy.coordinates
import astropy.time
import astropy.units as u
from threading import Thread
import redis

REDISHOST = 'localhost'
REDIS_KEYS = [
        'Target_RA_Deg', 
        'Target_DEC_Deg',
        'Pointing_EL',
        'Pointing_AZ',
        'Pointing_Updated',
        'Record'
        ]

r = redis.Redis(REDISHOST, decode_responses=True)

# Coordinates of Leuschner Educational Observatory
LAT = 37.9183 # deg
LON = -122.1067 # deg
HEIGHT = 304.0 # m

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
DELTA_ALT_ANT = -0.46 + 0.003814261454927248 # (true - encoder) offset
DELTA_AZ_ANT  = -0.13 + 0.00858691465120387 # (true - encoder) offset

# Server commands
CMD_MOVE_AZ = 'moveAz'
CMD_MOVE_ALT = 'moveEl'
CMD_WAIT_AZ = 'waitAz'
CMD_WAIT_ALT = 'waitEl'
CMD_GET_AZ = 'getAz'
CMD_GET_ALT = 'getEl'

# RA and DEC of SGR 1935+2154 (from McGill Online Magnetar Catalog) - J2000
SGR_RA, SGR_DEC = '19h34m55.598s', '+21d53m47.79s'

# Crab pulsar - J2000
CRAB_RA, CRAB_DEC = '05h34m31.95s', '+22d00m52.2s'

# Cygnus A - J2000
CYGA_RA, CYGA_DEC = '19h59m28.35656837s', '+40d44m02.0972325s'

# Cassiopia A
CASA_RA, CASA_DEC = '23h23m24.000', '+58d48m54.00'

class Telescope:
    """
    Interface for controlling the Leuschner Telescope. Copied from ugradio.
    """
    def __init__(self, host=ANT_HOSTNAME, port=PORT,
                 lat=LAT, lon=LON, hgt=HEIGHT,
                 delta_alt=DELTA_ALT_ANT, delta_az=DELTA_AZ_ANT):
        self.hostport = (host, port)
        self.location = astropy.coordinates.EarthLocation(
                            lat=lat * u.deg,
                            lon=lon * u.deg,
                            height=hgt * u.m,
        )
        self._delta_alt = delta_alt
        self._delta_az = delta_az
        self.observing = False # observation flag

    def _check_pointing(self, alt, az):
        """
        Ensure pointing is within telescope bounds. Raises
        AssertionError if not.
        Inputs:
            - alt: altitude
            - az: azimuth
        """
        assert(ALT_MIN < alt < ALT_MAX)
        assert(AZ_MIN < az < AZ_MAX)

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
        self.point(alt=ALT_STOW, az=AZ_STOW, wait=wait, verbose=verbose)

    def maintenance(self, wait=True, verbose=False):
        """
        Point to maintenance position.
        Inputs:
            - wait (bool): pause until antenna has completed pointing
                Default=True
            - verbose (bool): be verbose
                Default=False
        """
        self.point(ALT_MAINT, AZ_MAINT, wait=wait, verbose=verbose)

    def calc_altaz(self, coord0, coord1, frame='eq', jd=None, equinox='J2000'):
        """
        Convert set of coordinates to (alt, az).
        Inputs:
            - coord0 (str/float)|[hms/deg]: Either ra or l  depending 
               on frame choice. 
               If frame='eq' then coord0 is right ascension in [hours,
               mins, secs]. If frame='ga' then coord0 is galactic
               latitude [deg].
            - coord1 (str/float)|[dms/deg]: Either dec or be depending
               on frame choice.
               If frame='eq' then coord1 is declination in [deg,
               mins, secs]. If frame='ga' then coor10 is galactic
               longitude [deg].
            - frame (str): Coordinate system/frame. Either 'eq' or
               'ga'. Default is 'eq'.
            - jd (float): Julian date. 
            - equinox (str): coordinate frame equinox. Default='J2000'

        Returns:
            - alt, az (float)|[deg]
        """
        assert frame in ['eq', 'ga'], "Invalid coordinate frame provided."
        if jd: t = astropy.time.Time(jd, format='jd')
        else: t = astropy.time.Time(time.time(), format='unix')
        if frame == 'eq':
            c = astropy.coordinates.SkyCoord(coord0, coord1, unit='deg', equinox=equinox)
        if frame == 'ga':
            c = astropy.coordinates.SkyCoord(coord0, coord1, unit='deg', frame='galactic', equinox=equinox)
        altaz = c.transform_to(astropy.coordinates.AltAz(obstime=t, location=self.location))
        return altaz.alt.degree, altaz.az.degree

    def convert_ga_to_eq(self, l, b, jd=None, equinox='J2000'):
        """
        Converts galactic coordinates to ra and dec.

        Inputs:
            - l (float)|[deg]: latitude
            - b (float)|[deg]: longitude
            - jd (float): Julian date. 
            - equinox (str): coordinate frame equinox. Default='J2000'
            
        Returns:
            - ra, dec (str)|[hmsdms]
        """
        if jd: t = astropy.time.Time(jd, format='jd')
        else: t = astropy.time.Time(time.time(), format='unix')
        c = astropy.coordinates.SkyCoord(l, b, unit='deg', frame='galactic', equinox=equinox)
        ra, dec = c.icrs.to_string('hmsdms').split(' ')
        return ra, dec

    def sunpos(self, jd=None):
        """
        Return the ra and dec of the Sun in hmsdms str format.
        """
        if jd: t = astropy.time.Time(jd, format='jd')
        else: t = astropy.time.Time(time.time(), format='unix')
        sun = astropy.coordinates.get_sun(time=t)
        # c = astropy.coordinates.SkyCoord(sun.ra.deg, sun.dec.deg, unit='deg', frame='icrs')
        # coords = c.to_string('hmsdms') # Go back to hmsdms unit + str format
        # ra, dec = coords.split(' ')
        return sun.ra.deg, sun.dec.deg

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
        self.thread = Thread(target=self._track, args=(ra, dec, sleep_time, flag_time, verbose))
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
                try:
                    self.point(alt, az, wait=True, verbose=verbose)
                    t0 = time.time()
                    vals = [ra, dec, alt, az, t0, 1]
                    for key, val in zip(REDIS_KEYS, vals):
                        r.hset('limbo', key, val)
                except(AssertionError):
                    r.hset('limbo', 'Record', 0)
            time.sleep(flag_time)

    def stop(self):
        """
        End observation.
        """
        if self.observing:
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
