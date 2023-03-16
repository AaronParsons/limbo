import numpy as np
import os
from .fdmt import FDMT

# Load matrices used to remove baseline structure along time and frequency axes

BANDPASS_FILE = os.path.join(os.path.dirname(__file__),'data', 'bandpass_v002.npz')
BANDPASS_NPZ = np.load(BANDPASS_FILE)
FMDL = BANDPASS_NPZ['mdl']

FREQMASK_FILE = os.path.join(os.path.dirname(__file__),'data', 'freq_mask_v001.npz')
FREQ_MASK_NPZ = np.load(FREQMASK_FILE)
FREQ_MASK = FREQ_MASK_NPZ['mask']
FREQ_AMAT = FREQ_MASK_NPZ['amat']
FREQ_FMAT = FREQ_MASK_NPZ['fmat']

TIMEFILT_FILE = os.path.join(os.path.dirname(__file__),'data', 'time_filt_v001.npz')
TIME_FILT_NPZ = np.load(TIMEFILT_FILE)
TIME_AMAT = FREQ_MASK_NPZ['amat']
TIME_FMAT = FREQ_MASK_NPZ['fmat']

def dpss_filter(y, amat, fmat):
    '''Apply the provided DPSS filter matrices to data.'''
    model = amat @ (fmat @ y)
    return model.real

def process_data(hdr, data, ch0=400, ch1=400+1024, nsig=4, maxdm=500,
                 fmask=FREQ_MASK, freq_amat=FREQ_AMAT, freq_fmat=FREQ_FMAT,
                 time_amat=TIME_AMAT, time_fmat=TIME_FMAT):
    spec = np.mean(data, axis=0)
    fmdl = dpss_filter(spec * fmask.astype('float'), freq_amat, freq_fmat)
    tgain = np.sum(data[:,fmask], axis=1, keepdims=False) / np.sum(fmdl[fmask])
    #tnos = np.sqrt(np.median(np.abs(tgain - 1)**2))  # XXX not realy std
    tnos = np.median(np.abs(tgain - 1))  # not really std, just rough estimate
    tmask = (tgain - 1) / tnos < nsig  # not really std, just rough estimate
    tgain[~tmask] = 1
    #tmdl = dpss_filter(tgain, time_amat, time_fmat)  # XXX too much work for payoff?
    tmdl = tgain  # shortcut
    mdl = np.outer(tmdl, fmdl)
    diff_data = data - mdl
    #nos = mdl / hdr['AccLen']**0.5  # compute noise from power spectrum level
    #full_mask = np.where(diff_data > nsig * nos, False, True)
    full_mask = np.ones_like(diff_data).astype(bool)
    full_mask[:, ~fmask] = False
    full_mask[~tmask] = False
    diff_data *= full_mask
    fdmt = FDMT(hdr['freqs'][ch0:ch1], hdr['times'], maxDM=maxdm)
    dm_vs_t = fdmt.apply(diff_data[:, ch0:ch1])
    rv = {'dmt': dm_vs_t, 'dms': fdmt.dms, 'fmdl': fmdl, 'tmdl': tmdl, 'diff': diff_data}
    return rv
