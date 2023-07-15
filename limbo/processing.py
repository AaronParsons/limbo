import numpy as np
import os
from .fdmt import FDMT
from .io import read_volt_file
from .utils import DM_delay

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

def process_data(hdr, data, ch0=400, ch1=400+1024, gsig=4, maxdm=500,
                 hch0=1171, hch1=1308, hsig=3, dtype=DTYPE,
                 fmask=FREQ_MASK, freq_amat=FREQ_AMAT, freq_fmat=FREQ_FMAT,
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
    spec = np.mean(data, axis=0).astype(dtype)
    fmdl = dpss_filter(spec * fmask.astype(dtype), freq_amat, freq_fmat)
    # compute noise from smoothed spectrum; assumes same gain for all t in file
    nos = fmdl / hdr['AccLen']**0.5
    tnos = 1 / hdr['AccLen']**0.5 / (ch1-ch0)**0.5
    tmdl = np.sum(data[:,ch0:ch1][:,fmask[ch0:ch1]], axis=1, keepdims=False) / np.sum(fmdl[ch0:ch1][fmask[ch0:ch1]])
    tmdl = tmdl.astype(dtype)
    tmask = np.zeros(tmdl.shape, dtype=bool)
    tmask[1:-1] = np.abs(tmdl[1:-1] - 0.5*(tmdl[2:] + tmdl[:-2])) < gsig * (tnos * np.sqrt(1+2*0.5**2))
    mdl = np.outer(tmdl, fmdl)
    diff_data = data.astype(dtype) - mdl
    full_mask = np.outer(tmask, fmask)
    if inpaint:
        noise = np.random.normal(loc=0, scale=np.abs(nos), size=diff_data.shape).astype(dtype) # Gaussian inpainting
    else: 
        noise = 0
    diff_data = np.where(full_mask, diff_data, noise)
    hot = np.sum(diff_data[:,hch0:hch1], axis=1)
    hnos = np.sqrt(np.sum(nos[hch0:hch1][fmask[hch0:hch1]]**2))
    thot = np.where(hot > hsig * hnos)
    diff_data[thot,hch0:hch1] = 0
    full_mask[thot,hch0:hch1] = 0
    dmt = {'fmdl': fmdl, 'tmdl': tmdl, 'diff': diff_data, 'tmask': tmask, 'fmask': fmask}
    if do_dmt:
        fdmt = FDMT(hdr['freqs'][ch0:ch1], hdr['times'], maxDM=maxdm)
        dm_vs_t = fdmt.apply(diff_data[:,ch0:ch1])
        dmt['dmt'] = dm_vs_t
        dmt['dms'] = fdmt.dms
    return dmt

class ProcessVoltage:
    def __init__(self, DM):
        self.DM = DM
    
    def _get_volt_analysis_params(self, t_events, vhdr, pad=2000):
        """
        Get nessecary volt file params to be able to view relavent parts of pulse.
        XXX Only works for events that are sequential. Will need to be revised to include
            possibility of multiple events in one file. XXX
        Arguments:
            t_events: time of events in power spectra
            vhdr: voltage file header
            pad: amount to pad data by
        Returns:
            window: window containing length of pulse
            skip: how many spectra to skip in voltage file glob
        """
        skip = np.floor((t_events - vhdr['Time']) / vhdr['inttime']).astype(int) - pad
        max_delay = DM_delay(self.DM, vhdr['freqs'][0]) - DM_delay(self.DM, vhdr['freqs'][-1])
        nspec_delay = max_delay / vhdr['inttime']
        nspec_read = int(np.ceil(skip[-1] + nspec_delay) + 2*pad) # XXX
        window = nspec_read - skip[0] # XXX
        return window, skip[0]
    
    def find_volt_window(self, volt_files, t_events, vhdr, pad=2000):
        """
        Return the complex spectra that contains the length of the pulse.
        """
        window, skip = self._get_volt_analysis_params(t_events=t_events, vhdr=vhdr, pad=pad)
        vnspec = vhdr['nspec']
        volt_files = sorted(volt_files)
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
        return data_real, data_imag
    
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

    # XXX Figure out best way to compute Stoke params:
    # def compute_stokes_params(volt0, volt1):
    #     I = np.abs(volt0)**2 + np.abs(volt1)**2
    #     Q = np.abs(volt0)**2 - np.abs(volt1)**2
    #     U = volt0 * volt1.conj() + volt1 * volt0.conj()
    #     V = volt0 * volt1.conj() - volt1 * volt0.conj()
    #     return {'I':I, 'Q':Q, 'U':U, 'V':V}
