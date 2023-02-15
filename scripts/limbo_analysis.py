import limbo
import numpy as np

NSIG = 10

freq_mask = np.load('freq_mask_v001.npz') # XXX
fmask = freq_mask['mask']
freq_amat = freq_mask['amat']
freq_fmat = freq_mask['fmat']

bandpass = np.load('bandpass_v002.npz') # XXX

time_filt = np.load('time_filt_v001.npz')
time_amat = time_filt['amat']
time_fmat = time_filt['fmat']


def dpss_filter(y, amat, fmat):
    """
    Apply the provided DPSS filter matrices to data.
    """
    model = amat @ (fmat @ y)
    return model.real

hdr, data = limbo.io.read_file(filename, nspec=4096) # XXX filename undef
spec = np.mean(data, axis=0)
fmdl = dpss_filter(spec * fmask.astype('float'), freq_amat, freq_fmat)
tgain = np.sum(data[:, fmask], axis=1, keepdims=False) / np.sum(fmdl[fmask])
tnos = np.sqrt(np.median(np.abs(tgain - 1)**2)) # XXX not really std
tmask = (tgain - 1) / tnos < NSIG # XXX
tgain[~tmask] = 1
tmdl = dpss_filter(tgain, time_amat, time_fmat)
mdl = np.outer(tmdl, fmdl)
nos = mdl / hdr['AccLen']**0.5
diff_dat = data - mdl
fill_mask = np.where(diff_dat > NSIG * nos, 0, 1) # XXX
full_mask[:, ~fmask] = 0
full_mask[~tmask] = 0 
diff_dat *= full_mask

hi_dms = []
fdmt = limbo.fdmt.FDMT(hdr['freqs'], hdr['times'])
dm_vs_t = fdmt.apply(diff_dat)
hi_dms.append(np.max(dms_vs_t[:, np.logical_and(400 > fdmt.dms, fdmt.dms >= 300)], axis=1))

