import RPi.GPIO as GPIO
import numpy as np
import time as Time
import os

# GPIO pins
GPIO_DATA_PIN = 23 # data pin
GPIO_SCLK_PIN = 22 # serial clock pin
GPIO_PCLK_PIN = 24 # parallel clock pin
GPIO_TIMER_PIN = 26 # pin used for sleep timer/clock
GPIO_LOOP_PIN = 16 # pin used for easy testing and debugging
# GPIO_PINS = [GPIO_DATA_PIN, GPIO_SCLK_PIN, GPIO_PCLK_PIN, GPIO_TIMER_PIN, GPIO_LOOP_PIN]

# PTS model
MODEL = 'PTS3200'

# Rather than zeroing the signal (0 Hz) when a sweep is not occuring,
# we choose a random but easily recognizable frequency for the purpose
# of debugging and ensuring the system is performing as expected. This
# frequency will later be filtered out via a 250 MHz high-pass filter.
NO_SIGNAL = 7.2e6 # Hz

# Dispersion measure constant
CONST = 4140e12 # s Hz^2 / (pc cm^3)

# Set GPIO drive strength
DRIVE_STRENGTH = 4 # mA

class WaveGen():

    def __init__(self, 
                 drive_strength=DRIVE_STRENGTH, 
                 gpio_data_pin=GPIO_DATA_PIN, 
                 gpio_sclk_pin=GPIO_SCLK_PIN, 
                 gpio_pclk_pin=GPIO_PCLK_PIN, 
                 gpio_timer_pin=GPIO_TIMER_PIN, 
                 gpio_loop_pin=GPIO_LOOP_PIN, 
                 model=MODEL, 
                 no_signal=NO_SIGNAL):
        """
        Instantiate use of PTS and RPi GPIO pins.
        """
        # Set drive strength 
        self.drive_strength = drive_strength 
        # os.system('sudo pigpiod') #run pigpio demon
        os.system('pigs pads 0 ' + str(self.drive_strength)) # set strength

        self.model = model
        self.gpio_data_pin = gpio_data_pin
        self.gpio_sclk_pin = gpio_sclk_pin
        self.gpio_pclk_pin = gpio_pclk_pin
        self.gpio_timer_pin = gpio_timer_pin
        self.gpio_loop_pin = gpio_loop_pin
        self.gpio_pins = [self.gpio_data_pin, self.gpio_sclk_pin, self.gpio_pclk_pin, self.gpio_timer_pin, self.gpio_loop_pin]
        self.no_signal = no_signal

        GPIO.setwarnings(False) # ignore RPi.GPIO internal messaging
        GPIO.setmode(GPIO.BCM) # use GPIO numbers rather than pin numbers
        # define GPIO pins as outputs
        GPIO.setup(self.gpio_pins, GPIO.OUT)
        # set initial level of GPIO pins
        GPIO.output(self.gpio_data_pin, GPIO.LOW)
        GPIO.output(self.gpio_sclk_pin, GPIO.HIGH)
        GPIO.output(self.gpio_pclk_pin, GPIO.HIGH)
        GPIO.output(self.gpio_timer_pin, GPIO.LOW)
        GPIO.output(self.gpio_loop_pin, GPIO.LOW)


    def _convert_to_bins(self, frequency, model='PTS3200'):
        """
        Convert a given input into its binary counterpart.

        Inputs:
            - frequency (int)|[Hz]: Input frequency
            - model (str): PTS model used. Default is PTS3200.
              Accepts PTS3200, PTS500, PTS300.
        Returns:
            - A list of len 10 (for 10 decimal places from GHz to Hz),
              with each element in the list containing a binary nibble.
              This corresponds to a 40-bit total. The nibbles read from
              most to least significant bit.
        """
        min_freq = 1e6
        if self.model == 'PTS3200':
            max_freq = 3199999999
        elif self.model == 'PTS500': 
            max_freq = 500e6
        else: # assume PTS300
            max_freq = 300e6
        rounded_frequency = int(np.round(frequency)) # fractions not allowed
        if rounded_frequency > max_freq or rounded_frequency < min_freq: # upper and lower frequency bounds 
            print('WARNING: Input frequency {0} is out of range for model {1} ({2} - {3} Hz).'.format(frequency, model, max_freq, min_freq))
            if rounded_frequency > max_freq:
                rounded_frequency = max_freq # set to upper limit
            elif rounded_frequency < min_freq:
                rounded_frequency = min_freq # set to lower limit
        Frequency = str(rounded_frequency).zfill(10)
        freq = [int(n) for n in Frequency]
        binary_numbers = []
        for i, n in enumerate(freq):
            bin_num = np.binary_repr(n, width=4)
            binary_numbers.append(bin_num)
        return binary_numbers


    def _load_frequency(self, binary_numbers):
        """
        Reads a set of binary converted frequency values and 
        loads the data into the appropriate GPIO pin.

        Inputs:
            - binary_numbers: list of 10 nibbles containing
              frequency information
        """
        split_binary_numbers = []
        for num in binary_numbers:
            split = [int(n) for n in num]
            split_binary_numbers.append(split)
        GPIO.output(self.gpio_sclk_pin, GPIO.HIGH) # set serial clk to off state
        GPIO.output(self.gpio_pclk_pin, GPIO.HIGH) # set parallel clk to off state
        bit_cnt = 0
        for i in range(9, -1, -1): # count from most to least significant bit
            for j in range(len(split_binary_numbers[i])-1, -1, -1):
                if split_binary_numbers[i][j] == 0:
                    GPIO.output(self.gpio_data_pin, GPIO.LOW)
                elif split_binary_numbers[i][j] == 1:
                    GPIO.output(self.gpio_data_pin, GPIO.HIGH)
                self._usleep(3) # let the data settle before pulsing clk

                GPIO.output(self.gpio_sclk_pin, GPIO.LOW)
                self._usleep(5) # stretch out clk pulse to be conservative
                GPIO.output(self.gpio_sclk_pin, GPIO.HIGH) 
                bit_cnt += 1
        

    def _send_command(self):
        """
        Triggers send of frequency from RPi to PTS.
        """
        GPIO.output(self.gpio_pclk_pin, GPIO.LOW) # triggers send to PTS
        GPIO.output(self.gpio_pclk_pin, GPIO.HIGH) # return parallel clock to off state


    def continuous_wave(self, freq):
        """
        Generates a continuous wave of a specified frequency.
        
        Inputs:
            - freq (int)|[Hz]: Desired frequency in decimal representation
        """
        self._make_wave(freq, decimal=True)


    def _convert_freq_list(self, freqs, model='PTS3200'):
        """
        Convert an entire list of frequencies into binary
        in preparation for sweep functions.

        Inputs:
            - freqs [Hz]: list of frequencies (in decimal form)
            - model (str): PTS model used. Default is PTS3200.
              Accepts PTS3200, PTS500, PTS300.
        """
        bin_freqs = [self._convert_to_bins(f, model) for f in freqs]
        return bin_freqs


    def _make_wave(self, freq, decimal=False):
        """
        Load and generate a wave at the specified frequency.

        Inputs:
            - freq [Hz]: Desired frequency
            - decimal (bool): is input freq given in decimal 
              or binary form?
        """
        if decimal: # if frequency is given in decimal form:
            binary_list = self._convert_to_bins(freq) # convert freq from decimal to binary
        else:
            binary_list = freq # already in binary form
        self._load_frequency(binary_list) # load binary data to GPIO
        self._usleep(3) # conservative wait after data has been serially shifted before doing parallel load
        self._send_command() # send data to PTS


    def cleanup_gpio(self):
        """
        GPIO reset/cleanup.
        """
        GPIO.cleanup()


    def _usleep(self, time, cal_cnt=445):
        """
        Sleep for a given number of microseconds.

        WARNING: Needs to be calibrated according to used hardware.
        (Current estimate for RPi4B + PTS3200: 445 cnts = 1 ms.
         NOTE: /boot/config.txt file altered s.t. arm_freq fixed at 700MHz
         and core_freq_min=500MHz [core_freq set to value misc websites
         suggested to improve timing stability]. OS interups are NOT
         disabled so timing/delays can be off by [measured] ~200us. This 
         "works" for sleeps of >= 12us.)

        Inputs:
            - time [us]: time of delay
            - cal_cnt (float/int): calibrated number of cnts needed
              in order to equal 1 ms
        """
        min_time = 4 # [us] -- offset value for misc Python comp. time
        if time <= 2:
            return
        bit_val = GPIO.LOW
        GPIO.output(self.gpio_timer_pin, bit_val)
        # any time greater than minimum:
        ms_time = np.trunc(time/1e3) - 1 # subtract 1ms because OS take a bit of time
        if ms_time <= 0:
            ms_time = 0
            us_time = time
        elif ms_time > 0:
            us_time = time - (ms_time*1e3) - 190 # subtract 190us OS time
        const = cal_cnt/1e3 # conversion from ms to us
        N = int(np.round(const*(us_time-min_time)))
        if ms_time != 0: # for delays larger than or equal to 2ms 
            GPIO.output(self.gpio_timer_pin, GPIO.HIGH)
            Time.sleep(ms_time/1e3) # Time.sleep wants seconds
            GPIO.output(self.gpio_timer_pin, GPIO.LOW)
        for i in range(N): # for delays 10-2000us and fractional ms delays 
            if bit_val == GPIO.HIGH:
                bit_val = GPIO.LOW
            else:
                bit_val = GPIO.HIGH
            GPIO.output(self.gpio_timer_pin, bit_val)
        GPIO.output(self.gpio_timer_pin, GPIO.LOW) # return to safe value
        # GPIO.output(self.gpio_loop_pin, GPIO.HIGH)
        # GPIO.output(self.gpio_loop_pin, GPIO.LOW) # return to safe value


    def blank(self):
        """
        Clear signal and reset clocks.
        """
        N = 50
        GPIO.output(self.gpio_sclk_pin, GPIO.HIGH) # set off
        for j in range(2):
            for i in range(N):
                GPIO.output(self.gpio_sclk_pin, GPIO.LOW)
                GPIO.output(self.gpio_sclk_pin, GPIO.HIGH)
            self._send_command()
       


    def linear_sweep(self, f_min=1150e6, f_max=1650e6, nchans= 2048, dt=1e-3, model='PTS3200', continuous=False):
        """
        Generate a continuous linear (simple) sweep.

        Inputs:
            - f_min (float)|[Hz]: minimum frequency of sweep
            - f_max (float)|[Hz]: maximum frequency of sweep
            - nchans (int): number of frequency channels
            - dt (float)|[s]: time until next frequncy change
            - continuous (bool): single or repeating sweep?
        """
        dt_us = dt*1e6 # convert from s to us
        freqs = np.linspace(f_min, f_max, nchans)
        bin_freqs = self._convert_freq_list(freqs, model)
        while continuous:
            for f in bin_freqs:
                self._make_wave(f)
                self._usleep(dt_us)
        for f in bin_freqs:
            self._make_wave(f)
            self._usleep(dt_us)


    def _dm_delay(self, DM, freq):
        """
        Computes the frequency-dependent dispersion measure
        time delay.
        
        Inputs:
            - DM (float)|[pc*cm^-3]: dispersion measure
            - freq (float)|[Hz]: frequency
        Returns: pulse time delay in [s]
        """
        A = CONST*DM
        return A / freq**2

    def dm_sweep(self, DM=332.72, f_min=1150e6, f_max=1650e6, dt=1e-3, model='PTS3200', continuous=False):
        """
        Generates a frequency sweep that mirrors that caused
        by dispersion measure influence.

        Inputs:
            - DM (float)|[pc*cm^-3]: dispersion measure (default 
              is DM for SGR1935+2154)
            - f_min (float)|[Hz]: minimum frequency of sweep
            - f_max (float)|[Hz]: maximum frequency of sweep
            - dt (float)|[s]: sweep update interval
            - model (str): PTS model used. Default is PTS3200.
              Accepts PTS3200, PTS500, PTS300.
            - continuous (bool): single or repeating sweep?
        """
        dt_us = dt*1e6 # convert from s to us
        A = CONST*DM
        t0 = self._dm_delay(DM, f_max)
        tf = self._dm_delay(DM, f_min)
        ts = np.arange(t0, tf+dt, dt)
        freqs = np.sqrt(A/ts) # these frequencies will be sent to the PTS
        bin_freqs = self._convert_freq_list(freqs, model) # convert frequencies into binary form
        while continuous:
            for f in bin_freqs:
                self._make_wave(f)
                self._usleep(dt_us)
        for f in bin_freqs:
            self._make_wave(f)
            self._usleep(dt_us)


    def mock_dm_obs(self, wait_time, DM=332.72, f_min=1150e6, f_max=1650e6, dt=1e-3, model='PTS3200'):
        """
        Simulate an FRB observation in collected time-dependent voltage data.

        Inputs:
            - wait_time (float)|[s]: time until FRB pulse/sweep begins
            - DM (float)|[pc*cm^-3]: dispersion measure (default 
              is DM for SGR1935+2154)
            - f_min (float)|[Hz]: minimum frequency of sweep
            - f_max (float)|[Hz]: maximum frequency of sweep
            - dt (float)|[s]: sweep update interval
            - model (str): PTS model used. Default is PTS3200.
              Accepts PTS3200, PTS500, PTS300.
        """
        wait_time_us = wait_time*1e6 # convert to microseconds
        self.continuous_wave(self.no_signal) # "no signal" signal
        self._usleep(wait_time_us)
        self.dm_sweep(DM, f_min, f_max, dt, model, continuous=False) # FRB sweep
        self.continuous_wave(self.no_signal) # go back to "no signal" signal
      

    def mock_linear_obs(self, wait_time, f_min=1150e6, f_max=1650e6, nchans=2048, dt=1e-3, model='PTS3200'):
        """
        Simulate a linear sweep of frequencies collected in time-dependent voltage data.

        Inputs:
            - wait_time (float)|[s]: time until sweep begins
            - f_min (float)|[Hz]: minimum frequency of sweep
            - f_max (float)|[Hz]: maximum frequency of sweep
            - nchans (int): number of frequency channels (i.e. number of sweep steps)
            - dt (float)|[s]: sweep update interval
            - model (str): PTS model used. Default is PTS3200.
              Accepts PTS3200, PTS500, PTS300.
        """
        wait_time_us = wait_time*1e6 # convert to microseconds
        self.continuous_wave(self.no_signal) # "no signal" signal
        self._usleep(wait_time_us)
        self.linear_sweep(f_min, f_max, nchans, dt, model, continuous=False) # sweep
        self.continuous_wave(self.no_signal) # go back to "no signal" signal






        




