import numpy as np
import os
from .fdmt import FDMT

# Load matrices used to remove baseline structure along time and frequency axes

BANDPASS_FILE = os.path.join(os.path.dirname(__file__),'data', 'bandpass_v002.npz')
BANDPASS_NPZ = np.load(BANDPASS_FILE)
FMDL = BANDPASS_NPZ['mdl']
FMDL = np.roll(FMDL, shift=-2)

CAL_FILE = os.path.join(os.path.dirname(__file__),'data', 'calibration_v001.npz')
CAL_NPZ = np.load(CAL_FILE)
CALGAIN = CAL_NPZ['cnt2jy']
CALGAIN = np.roll(CALGAIN, shift=-2)


FREQMASK_FILE = os.path.join(os.path.dirname(__file__),'data', 'freq_mask_v003.npz')
FREQ_MASK_NPZ = np.load(FREQMASK_FILE)
FREQ_MASK = FREQ_MASK_NPZ['mask']
FREQ_AMAT = FREQ_MASK_NPZ['amat']
FREQ_FMAT = FREQ_MASK_NPZ['fmat']

# FREQ_MASK = np.roll(FREQ_MASK, shift=-2) # Shift masks by 2 channels
# FREQ_AMAT = np.roll(FREQ_AMAT, shift=-2, axis=[0, 1])
# FREQ_FMAT = np.roll(FREQ_FMAT, shift=-2, axis=[0, 1])

def dpss_filter(y, amat, fmat):
    '''Apply the provided DPSS filter matrices to data.'''
    model = amat @ (fmat @ y)
    return model.real

def process_data(hdr, data, ch0=400, ch1=400+1024, gsig=4, maxdm=500,
                 hch0=1171, hch1=1308, hsig=3,
                 fmask=FREQ_MASK, freq_amat=FREQ_AMAT, freq_fmat=FREQ_FMAT, inpaint=True):
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
    spec = np.mean(data, axis=0)
    fmdl = dpss_filter(spec * fmask.astype('float'), freq_amat, freq_fmat)
    # compute noise from smoothed spectrum; assumes same gain for all t in file
    nos = fmdl / hdr['AccLen']**0.5
    tnos = 1 / hdr['AccLen']**0.5 / (ch1-ch0)**0.5
    tmdl = np.sum(data[:,ch0:ch1][:,fmask[ch0:ch1]], axis=1, keepdims=False) / np.sum(fmdl[ch0:ch1][fmask[ch0:ch1]])
    tmask = np.zeros(tmdl.shape, dtype=bool)
    tmask[1:-1] = np.abs(tmdl[1:-1] - 0.5*(tmdl[2:] + tmdl[:-2])) < gsig * (tnos * np.sqrt(1+2*0.5**2))
    mdl = np.outer(tmdl, fmdl)
    diff_data = data - mdl
    full_mask = np.outer(tmask, fmask)
    if inpaint:
        noise = np.random.normal(loc=0, scale=np.abs(nos), size=diff_data.shape) # Gaussian inpainting
    else: 
        noise = 0
    diff_data = np.where(full_mask, diff_data, noise)
    hot = np.sum(diff_data[:,hch0:hch1], axis=1)
    hnos = np.sqrt(np.sum(nos[hch0:hch1][fmask[hch0:hch1]]**2))
    thot = np.where(hot > hsig * hnos)
    diff_data[thot,hch0:hch1] = 0
    full_mask[thot,hch0:hch1] = 0
    fdmt = FDMT(hdr['freqs'][ch0:ch1], hdr['times'], maxDM=maxdm)
    dm_vs_t = fdmt.apply(diff_data[:,ch0:ch1])
    dmt = {'dmt': dm_vs_t, 'dms': fdmt.dms, 'fmdl': fmdl, 'tmdl': tmdl, 'diff': diff_data, 'tmask': tmask, 'fmask': fmask}
    return dmt
