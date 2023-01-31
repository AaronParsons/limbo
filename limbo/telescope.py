import numpy as np
import socket
import sys
import thread
import serial
import time
import RPi.GPIO as GPIO # Necessary for LeuschnerNoiseServer


MAX_SLEW_TIME = 220 # [s]

ALT_MIN, ALT_MAX = 15., 85. # Pointing bounds, [degrees]
AZ_MIN, AZ_MAX  = 5., 350. # Pointing bounds, [degrees]

ALT_STOW, AZ_STOW = 80., 180. # Position for stowing antenna [degrees]
ALT_MAINT, AZ_MAINT = 20., 180. # Position for antenna maintenance [degrees]

ANT_HOSTNAME = '192.168.1.156' # RPI host for antenna
NOISE_SERVER_HOSTNAME = '192.168.1.90' # RPI host for noise diode
PORT = 1420
SPECTROMETER_HOSTNAME = '10.0.1.2' # IP address of ROACH spectrometer

# Offsets [degrees] to subtract from crd to get encoder value to write
DELTA_ALT_ANT = -0.30  # (true - encoder) offset
DELTA_AZ_ANT  = -0.13  # (true - encoder) offset

CMD_MOVE_AZ = 'moveAz'
CMD_MOVE_ALT = 'moveAlt'
CMD_WAIT_AZ = 'waitAz'
CMD_WAIT_ALT = 'waitAlt'
CMD_GET_AZ = 'getAz'
CMD_GET_ALT = 'getAlt'


class LeuschnerTelescope:
    """
    Interface for controlling the Leuschner Telescope.
    """
    def __init__(self, host=ANT_HOSTNAME, port=PORT, 
                 delta_alt=DELTA_ALT_ANT, delta_az=DELTA_AZ_ANT):
        self.hostport = (host, port)
        self._delta_alt = delta_alt
        self._delta_az = delta_az
        
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
        # Retunr true (alt, az) corresponding to encoded position
        return alt + self._delta_alt, az + self.delta_az
    
    def stow(self, wait=True, verbose=False):
        """
        Point to stow position.
        Inputs:
            - wait (bool): pause until antenna has completed pointing
                Default=True
            - verbose (bool): be verbose
                Default=False
        """
        self.point(ALT_STOW, AZ_STOW, wait=wait, verbose=verbose)
        
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
    
    
###################################################################
########################## NOISE SERVER ##########################
###################################################################
    
CMD_NOISE_ON = 'on'
CMD_NOISE_OFF = 'off'
    
class LeuschnerNoise:
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
        Low-level interface for sending command to LeuschnerNoiseServer.
        """
        assert(cmd in (CMD_NOISE_ON, CMD_NOISE_OFF)) # Check if valid command
        if self.verbose: print('LeuschnerNoise sending command:', [cmd])
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(self.hostport)
        s.sendall(bytes(cmd, encoding='utf8'))
        

class LeuschnerNoiseServer:
    """
    Class for providin remote control over the noise diode on
    the Leuschner dish. Runs on an RPi with a direct connection
    to the noise diode via GPIO pins.
    """
    def __init__(self, verbose=True):
        self.verbose = verbose
        self.prev_cmd = None
    
    def log(self. *args):
        if self.verbose:
            print(*args)
            sys.stdout.flush()
    
    def run(self, host='', port=PORT, timeout=10):
        """
        Begin hosting server that allows remote control of noise diode on
        specified port."""
        self.log('Initializing noise server...')
         try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind((host,port))
            s.listen(10)
            while True:
                conn, addr = s.accept()
                conn.settimeout(timeout)
                self.log('Request from', (conn, addr))
                thread.start_new_thread(self._handle_request, (conn, ))
        finally:
            s.close()
            
    def _handle_request(self, conn):
        """
        Private thread for handling an individual connection. Will execute
        at most one write and one read before terminating connection.
        """
        cmd = conn.recv(1024)
        if not cmd:
            return
        self.log('Enacting:', [cmd], 'from', conn)
        cmd = cmd.decode('ascii')
        # Only execute digital I/O write code if a change of state
        # command is received over the socket.  I will avoid multiple
        # overwrite commands to the Raspberry
        pin = 5 # This was originally 05
        if self.prev_cmd != cmd:
            self.prev_cmd = cmd
            GPIO.setmode(GPIO.BCM) # Errors out if import RPi.GPIO failed
            GPIO.setwarnings(False)
            GPIO.setup(pin, GPIO.OUT) # pin 29
            # Switch pin 29 of Raspberry Pi to TTL level low
            if cmd == CMD_NOISE_OFF:
                self.log('write digital I/O low')
                GPIO.output(pin, False) # pin 29
            # switch pin 29 of Raspberry Pi to TTL level high
            elif cmd == CMD_NOISE_ON:
                self.log('write digital I/O high')
                GPIO.output(pin, True) # pin 29
    
    
###################################################################
######################## TELESCOPE SERVER #########################
###################################################################

AZ_ENC_OFFSET = -3035.0 # -4901
AZ_ENC_SCALE = 1800.342065
ALT_ENC_OFFSET = -0.02181661564 #-0.3774466558186913
DISH_ALT_OFFSET = -0.3556300401687622
DRIVE_ENCODER_STATES = float(2**14)
DRIVE_DEG_PER_CNT = 360. / DRIVE_ENCODER_STATES
DRIVE_RAD_PER_CNT = (2*np.pi) / DRIVE_ENCODER_STATES
DEG2RAD = np.pi / 180.
DRIVE_STUB_LEN = 1.487911343574524
DRIVE_ENC_SCALE = 6.173610955784170e-8
DRIVE_CLENGTH = 9.587619900703430e-1    

class TelescopeDirect():
    def __init__(self, serialPort='/dev/ttyUSB0', baudRate=9600,
                 timeout=1, verbose=True, 
                 az_enc_offset=AZ_ENC_OFFSET, az_enc_scale=AZ_ENC_SCALE,
                 alt_enc_offset=ALT_ENC_OFFSET, dish_alt_offset=DISH_ALT_OFFSET,
                 stub_len=DRIVE_STUB_LEN, drive_enc_scale=DRIVE_ENC_SCALE,
                 drive_clength=DRIVE_CLENGTH):
        self._serial = serial.Serial(serialPort, baudRate, timeout=timeout)
        self._lock = thread.allocate_lock()
        self.verbose = verbose
        self.az_enc_offset = az_enc_offset
        self.az_enc_scale = az_enc_scale
        self.alt_enc_offset = alt_enc_offset
        self.dish_alt_offset = dish_alt_offset
        self.stub_len = stub_len
        self.drive_enc_scale = drive_enc_scale
        self.drive_clength = self.drive_clength
        
        self.init_dish()
        
    def log(self, *args):
        if self.verbose:
            print(*args)
            sys.stdout.flush()
    
    def _read(self, flush=False, bufsize=1024):
        resp = []
        while len(resp) < bufsize:
            c = self._serial.read(1)
            c = c.decode('ascii')
            if len(c) == 0: break
            if c == '\r' and not flush: break
            resp.append(c)
        resp = ''.join(resp)
        self.log('Read:', [resp])
        return resp
    
    def _write(self, cmd, bufsize=1024):
        self.log('Writing', [cmd])
        self._lock.acquire()
        self._serial.write(cmd) # Receiving from client
        time.sleep(0.1) # Allow the config command to make the change it needs
        rv = self._read(bufsize=bufsize)
        self._lock.release()
        return rv
    
    def init_dish(self):
        self._read(flush=True)
        # The following definitions are specific to the Copley BE2 model
        self._write(b'.a s r0xc8 257\r')
        self._write(b'.a s r0xcb 1500000\r')
        self._write(b'.a s r0xcc 2500\r')
        self._write(b'.a s r0xcd 2500\r')
        self._write(b'.a s r0x24 21\r')
        self._write(b'.b s r0xc8 257\r')
        self._write(b'.b s r0xcb 1500000\r')
        self._write(b'.b s r0xcc 2500\r')
        self._write(b'.b s r0xcd 2500\r')
        self._write(b'.b s r0x24 21\r')
        
    def reset_dish(self, sleep=10):
        self._write(b'r\r')
        time.sleep(sleep)
        self.init_dish()
        
    def wait_alt(self, max_wait=220):
        status = '-1'
        for i in range(max_wait):
            status = self._write(b'.b g r0xc9\r').split()[1]
            self.log('wait_alt status=', status)
            # Sometimes status = 16384: set when move is aborted.
            # See Copley Parameter Dictionary pg 45.
            if int(status) >= 0: break
            time.sleep(1)
        return status

    def wait_az(self, max_wait=220):
        status = '-1'
        for i in range(max_wait):
            status = self._write(b'.a g r0xc9\r').split()[1]
            self.log('wait_az status=', status)
            # Sometimes status = 16384: set when move is aborted.
            # See Copley Parameter Dictionary pg 45.
            if int(status) >= 0: break
            time.sleep(1)
        return status
    
    
    def get_alt(self):
        alt_cnts = float(self._write(b'.b g r0x112\r').split()[1])
        alt_cnts %= DRIVE_ENCODER_STATES
        alt = 90 - alt_cnts*DRIVE_DEG_PER_CNT - self.alt_enc_offset/DEG2RAD
        return alt
    
    def get_az(self):
        az_cnts = float(self._write(b'.a g r0x112\r').split()[1])
        az_cnts %= DRIVE_ENCODER_STATES
        az = (az_cnts - self.az_enc_offset) * DRIVE_DEG_PER_CNT
        az %= 360 # Necessary because encoder wraps at az = 65 degrees
        return az
    
    def _alt_to_drive_enc(self, alt_rad):
        drive_len = np.sqrt(1 + self.drive_clength**2 - 2*self.drive_clength*np.cos(alt_rad))
        enc = (drive_len - self.stub_len) / self.drive_enc_scale
        return enc
    
    def move_alt(self, dishAlt):
        altResponse = self.wait_alt()
        if altResponse != '0':
            return 'e 1'
        # Enfore absolute bounds. Comment out to override.
        if (dishAlt < ALT_MIN) or (dishAlt > ALT_MAX):
            return 'e 1'
        
        dishAlt_rad = dishAlt * DEG2RAD
        # Get current elevation
        curAlt = float(self._write(b'.b g r0x112\r').split()[1])
        # Correct for offset and convert to radians
        dish_alt_offset_cnts = self.dish_alt_offset/DRIVE_RAD_PER_CNT
        curAlt = (curAlt-dish_alt_offset_cnts)%DRIVE_ENCODER_STATES
        curAlt_rad = curAlt*DRIVE_RAD_PER_CNT
        
        curAltVal = self._alt_to_drive_enc(curAlt_rad)
        nextAltVal = self._alt_to_drive_enc(np.pi/2 - dishAlt_rad - self.alt_enc_offset - self.dish_alt_offset)
        altMoveCmd =  '.b s r0xca ' + str(int(nextAltVal-curAltVal)) + '\r'
        self._write(altMoveCmd.encode('ascii'))
        dishResponse = self._write(b'.b t 1\r')
        return dishResponse
    
    def move_az(self, dishAz):
        azResponse = self.wait_az()
        if azResponse != '0':
            return 'e 1'
        dishAz = (dishAz + 360.) % 360 # Necessary because encoder wraps at az = 65 degrees
        # Enforce absolute bounds. (Comment out to override.)
        if (dishAz < AZ_MIN) or (dishAz > AZ_MAX):
            return 'e 1'
        az_cnts = int(self.get_az() / DRIVE_DEG_PER_CNT)
        # Commands are sent as a delta from current position
        azMoveCmd =  '.a s r0xca ' + str(int((dishAz / DRIVE_DEG_PER_CNT - az_cnts) * self.az_enc_scale)) + '\r'
        self._write(azMoveCmd.encode('ascii'))
        dishResponse = self._write(b'.a t 1\r')
        return dishResponse
    
class TelescopeServer(TelescopeDirect):
    def run(self, host='', port=PORT, verbose=True, timeout=10):
        self.verbose = verbose
        self.log('Initializing dish...')
        self.reset_dish()
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind((host,port))
            s.listen(10)
            while True:
                conn, addr = s.accept()
                conn.settimeout(timeout)
                self.log('Request from', (conn, addr))
                thread.start_new_thread(self._handle_request, (conn, ))
        finally:
            s.close()
            
    def _handle_request(self, conn):
        """
        Private thread for handling an individual connection.  Will execute
        at most one write and one read before terminating connection.
        """
        cmd = conn.recv(1024)
        if not cmd:
            return
        self.log('Enacting:', [cmd], 'from', conn)
        cmd = cmd.decode('ascii')
        cmd = cmd.split('\n')
        self.log("the cmd is: ", cmd)
        if cmd[0] == 'simple':
            resp = self._write(cmd[1].encode('ascii'))
        elif cmd[0] == CMD_MOVE_AZ:
            resp = self.move_az(float(cmd[1]))
        elif cmd[0] == CMD_MOVE_ALT:
            resp = self.move_alt(float(cmd[1]))
        elif cmd[0] == CMD_WAIT_AZ:
            resp = self.wait_az()
        elif cmd[0] == CMD_WAIT_ALT:
            resp = self.wait_alt()
        elif cmd[0] == CMD_GET_AZ:
            resp = str(self.get_az())
        elif cmd[0] == CMD_GET_ALT:
            resp = str(self.get_alt())
        elif cmd[0] == 'reset':
            resp = self.reset_dish()
        else:
            resp = ''
        self.log('Returning:', [resp])
        conn.sendall(resp.encode('ascii'))