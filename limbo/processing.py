import numpy as np
import os
from .fdmt import FDMT
from .io import read_volt_file, read_volt_header
from .utils import DM_delay, dedisperse
from tqdm import tqdm
from scipy.special import erf

PRECISION = 1

assert PRECISION in (1, 2)
if PRECISION == 1:
    DTYPE = 'float32'
    CDTYPE = 'complex64'
else:
    DTYPE = 'float64'
    CDTYPE = 'complex128'

# Load matrices used to remove baseline structure along time and frequency axes

BANDPASS_FILE = os.path.join(os.path.dirname(__file__),'data', 'bandpass_v002.npz')
BANDPASS_NPZ = np.load(BANDPASS_FILE)
FMDL = BANDPASS_NPZ['mdl']
FMDL = np.roll(FMDL, shift=-2).astype(DTYPE)

CAL_FILE = os.path.join(os.path.dirname(__file__),'data', 'calibration_v001.npz')
CAL_NPZ = np.load(CAL_FILE)
CALGAIN = CAL_NPZ['cnt2jy']
CALGAIN = np.roll(CALGAIN, shift=-2).astype(DTYPE)


FREQMASK_FILE = os.path.join(os.path.dirname(__file__),'data', 'freq_mask_v003.npz')
FREQ_MASK_NPZ = np.load(FREQMASK_FILE)
FREQ_MASK = FREQ_MASK_NPZ['mask']
FREQ_AMAT = FREQ_MASK_NPZ['amat'].astype(CDTYPE)
FREQ_FMAT = FREQ_MASK_NPZ['fmat'].astype(CDTYPE)

# FREQ_MASK = np.roll(FREQ_MASK, shift=-2) # Shift masks by 2 channels
# FREQ_AMAT = np.roll(FREQ_AMAT, shift=-2, axis=[0, 1])
# FREQ_FMAT = np.roll(FREQ_FMAT, shift=-2, axis=[0, 1])

def dpss_filter(y, amat, fmat):
    '''Apply the provided DPSS filter matrices to data.'''
    model = amat @ (fmat @ y)
    return model.real

def process_data(hdr, data, ch0=400, ch1=1424, gsig=4, maxdm=500, hch0=1171, hch1=1308,
    hsig=3, dtype='float32', fmask=FREQ_MASK, freq_amat=FREQ_AMAT,
    freq_fmat=FREQ_FMAT, nsig=3,
    do_dmt=True, inpaint=True):
    '''Process LIMBO data by detrending, flagging, and performing a DM transform.
    Arguments:
        hdr: Header from LIMBO file
        data: Data from LIMBO file.
        ch0: Lower channel of window for performing DM transform.
        ch1: Upper channel of window for performing DM transform.
        gsig: Number of sigma for flagging gain variations
        maxdm: Max DM in DM transform
        hch0: Lower channel of "hot" RFI zone
        hch1: Upper channel of "hot" RFI zone
        hsig: Number of sigma for flagging "hot" zone excess power.
        fmask: Frequency channel mask, derived from data/freq_mask_v002.npz
        freq_amat: Frequency filtering design matrix, derived from data/freq_mask_v002.npz
        freq_fmat: Frequency filtering matrix mask, derived from data/freq_mask_v002.npz
    Returns:
        dmt: Dictionary with keys 'dmt', 'dms', 'fmdl', 'tmdl', 'diff', 'tmask', 'fmask'.
    '''
    data = data.astype(dtype)  # prevent datatype promotion
    # compute smooth, time-averaged fmdl: our model of stable spectrum
    spec = np.mean(data, axis=0)
    fmdl = dpss_filter(spec * fmask.astype(dtype), freq_amat, freq_fmat)
    fmdl = fmdl.astype(dtype)  # prevent datatype promotion
    # estimate thermal (rms) noise level for each chan from fmdl
    # assumes same gain for all t in file
    nos = fmdl / hdr['AccLen']**0.5
    # estimate power level vs time tmdl, assuming fmdl spectral shape
    # moves # up and down with each integration
    tmdl = np.sum(data[:,ch0:ch1][:,fmask[ch0:ch1]], axis=1) / np.sum(fmdl[ch0:ch1][fmask[ch0:ch1]])
    tmdl = tmdl.astype(dtype)  # prevent datatype promotion
    mdl = np.outer(tmdl, fmdl)  # 1st smoothed, time-variable power model
    # iterate tmdl fit once to reject outliers that skew power level est
    zscore = (data - mdl) / nos
    reject = np.where(zscore > nsig, 0, fmask[np.newaxis,:])
    tmdl = np.sum(data[:,ch0:ch1] * reject[:,ch0:ch1], axis=1) / np.sum(reject[:,ch0:ch1] * fmdl[ch0:ch1], axis=1)
    tmdl = tmdl.astype(dtype)  # prevent datatype promotion
    mdl = np.outer(tmdl, fmdl)  # 2nd smoothed, time-variable power model
    # compute a signed zscore**2 (tzsq) proportional to log likelihood of 
    # high outliers
    diff_data = data - mdl
    zscore = diff_data / nos
    zsq = np.abs(zscore) * zscore
    tmask = np.ones(tmdl.size, dtype=fmask.dtype)
    full_mask = np.outer(tmask, fmask)
    # compute power in 'hot' region and flag separately
    hzsq = np.mean(zsq[:,hch0:hch1], axis=1)
    full_mask[hzsq > hsig**2, hch0:hch1] = 0
    # remove outlying times by flagging for gsig outliers from in
    # median log likelihood
    tzsq = np.sum(full_mask[:,ch0:ch1] * zsq[:,ch0:ch1], axis=1) / np.sum(full_mask[:,ch0:ch1], axis=1)
    tzsq -= np.median(tzsq)
    tmask[tzsq > gsig * np.median(np.abs(tzsq))] = 0
    full_mask[~tmask, :] = 0
    # finally, remove any remaining freqs that are persistently bad
    fzsq = np.sum(full_mask * zsq, axis=0) / np.sum(full_mask, axis=0)
    fmask[np.abs(fzsq) > 0.5] = 0
    full_mask[:, ~fmask] = 0
    
    if inpaint:  # inpaint diff data with gaussian noise
        noise = np.random.normal(loc=0, scale=np.abs(nos), size=diff_data.shape).astype(dtype)  # XXX this is a bit slow
        diff_data = np.where(full_mask, diff_data, noise)
    else: 
        diff_data *= full_mask
    
    dmt = {'fmdl': fmdl, 'tmdl': tmdl,
           'diff': diff_data, 'zscore': zscore, 'mask': full_mask,
           'tmask': tmask, 'fmask': fmask}
    if do_dmt:
        fdmt = FDMT(hdr['freqs'][ch0:ch1], hdr['times'], maxDM=maxdm)
        dm_vs_t = fdmt.apply(diff_data[:,ch0:ch1])
        dmt['dmt'] = dm_vs_t
        dmt['dms'] = fdmt.dms
    return dmt


class ProcessVoltage:
    def __init__(self, DM, volt_files, vhdr, hdr):
        self.DM = DM
        self.volt_files = volt_files
        self.vhdr = vhdr
        self.hdr = hdr
    
    def _get_volt_analysis_params(self, t_events, pad=2000):
        """
        Get nessecary volt file params to be able to view relavent parts of pulse.
        XXX Only works for events that are sequential. Will need to be revised to include
            possibility of multiple events in one file. XXX
        Arguments:
            t_events: time of events in power spectra
            pad: amount to pad data by
        Returns:
            window: window containing length of pulse
            skip: how many spectra to skip in voltage file glob
        """
        skip = np.floor((t_events - self.vhdr['Time']) / self.vhdr['inttime']).astype(int) - pad
        max_delay = DM_delay(self.DM, self.vhdr['freqs'][0]) - DM_delay(self.DM, self.vhdr['freqs'][-1])
        nspec_delay = max_delay / self.vhdr['inttime']
        nspec_read = int(np.ceil(skip[-1] + nspec_delay) + 2*pad) # XXX
        window = nspec_read - skip[0] # XXX
        return window, skip[0]
    
    def find_volt_window(self, t_events, vhdr, pad=2000):
        """
        Return the complex spectra that contains the length of the pulse.
        """
        window, skip = self._get_volt_analysis_params(t_events=t_events, pad=pad)
        vnspec = self.vhdr['nspec']
        volt_files = sorted(self.volt_files)
        for i, file in enumerate(volt_files):
            if skip > vnspec * (i+1):
                continue
            else:
                _skip = skip - (vnspec * i)
                if window < vnspec - _skip: # read to end of window
                    _, data_real, data_imag = read_volt_file(file, skip=_skip, nspec=window)
                elif window > vnspec - _skip: # if pulse stradles two files
                    _, dr0, di0 = read_volt_file(file, skip=_skip, nspec=-1) # read to end of file
                    _, dr1, di1 = read_volt_file(volt_files[i+1], skip=0, nspec=window - dr0.shape[0]) # read remaining amount from next file
                    data_real = np.concatenate((dr0, dr1), axis=0)
                    data_imag = np.concatenate((di0, di1), axis=0)
                break
        return data_real, data_imag, window, skip
    
    def sum_pols(self, data_real, data_imag):
        """ Sum polarizations """
        p0 = data_real[:, :, 0]**2 + data_imag[:, :, 0]**2
        p1 = data_real[:, :, 1]**2 + data_imag[:, :, 1]**2
        return p0 + p1

    def get_volt_streams(self, data_real, data_imag, dtype='complex64'):
        """ Get indiviual voltage streams """
        v0 = data_real[:, :, 0] + np.asarray(1j).astype(dtype) * data_imag[:, :, 0]
        v1 = data_real[:, :, 1] + np.asarray(1j).astype(dtype) * data_imag[:, :, 1]
        return v0, v1
    
    def sum_down(self, vdata, sum_int=128):
        """ Sum voltage data along time axis. """
        if vdata.shape[0] % sum_int != 0:
            vdata = vdata[:-(vdata.shape[0] % sum_int)]
        vdata.shape = (-1, sum_int, vdata.shape[1])
        vdata = np.mean(vdata, axis=1)
        return vdata
    
    def get_volt_times(self, lo_hz=1350e6, nchan=2048, infochan=24, dtype=np.dtype('>u1'), npol=2):
        """ Get Unix times of all voltage files. """
        times = []
        for file in self.volt_files:
            hdr = read_volt_header(file, lo_hz=lo_hz, nchan=nchan, infochan=infochan, dtype=dtype, npol=npol)
            ts = hdr['Time'] + np.arange(0, hdr['nspec']) * hdr['inttime']
            times.append(ts)
        return np.concatenate(times, axis=0)
    
    def snr_dedispersion(self, vdmt, pmDM=10, ntrials=128, sum_int=1, resamp_factor=1, ch0=398, ch1=398+1024):
        """ Dedisperse in a way that maximizes the SNR. Returns zscore and DM. """
        dms = np.linspace(self.DM - pmDM, self.DM + pmDM, ntrials, endpoint=False)
        vcal_data = vdmt['diff'] * CALGAIN * np.sqrt(self.hdr['inttime'] / self.vhdr['inttime'])
        vdata_summed = self.sum_down(vcal_data, sum_int=sum_int)
        maxz = 0
        maxz_dm = 0
        for dm in tqdm(dms):
            vprofile = dedisperse(vdata_summed, dm, self.vhdr['freqs'], sum_int * self.vhdr['inttime'], resamp_factor)
            avg_vprofile = np.mean(vprofile[:, ch0:ch1], axis=-1)
            vzscore = (avg_vprofile - np.mean(avg_vprofile)) / np.std(avg_vprofile)
            maxz0 = np.max(vzscore)
            if maxz0 > maxz:
                maxz = maxz0
                maxz_dm = dm
            else:
                continue
        return maxz, maxz_dm

    # XXX Figure out best way to compute Stoke params:
    # def compute_stokes_params(volt0, volt1):
    #     I = np.abs(volt0)**2 + np.abs(volt1)**2
    #     Q = np.abs(volt0)**2 - np.abs(volt1)**2
    #     U = volt0 * volt1.conj() + volt1 * volt0.conj()
    #     V = volt0 * volt1.conj() - volt1 * volt0.conj()
    #     return {'I':I, 'Q':Q, 'U':U, 'V':V}
