'''Tools for file I/O.'''

import numpy as np
import json
import os
from astropy.time import Time
import struct

from . import utils

HEADER_SIZE = 1024
NCHAN_DEFAULT = 2048

def _get_header_size(f):
    s = f.read(1)
    f.seek(0,0)
    if(s==b'{'):
        header_size = HEADER_SIZE
    else:
        header_size = struct.unpack('I',f.read(4))[0]
    return header_size

def read_header(filename, lo_hz=1350e6, header_size=HEADER_SIZE,
              nchan=NCHAN_DEFAULT, infochan=12, dtype=np.dtype('>u2')):
    '''Read header from a limbo file.'''
    with open(filename, 'rb') as f:
        header_size = _get_header_size(f)
        h = f.read(header_size)
        h = json.loads(h[:h.find(0x00)])
        h['filename'] = filename
        h['sample_clock'] = h.pop('SampleFreq') * 1e6
        h['freqs'] = utils.calc_freqs(h['sample_clock'], lo_hz, nchan)
        h['inttime'] = utils.calc_inttime(h['sample_clock'], h['AccLen'], nchan)
    size = os.path.getsize(filename)
    h['nspec'] = (size - header_size) // (dtype.itemsize * (nchan + infochan))
    return h


def read_raw_data(filename, nspec=-1, skip=0, header_size=HEADER_SIZE,
              nchan=NCHAN_DEFAULT, infochan=12, dtype=np.dtype('>u2')):
    '''Read raw data from a limbo file.'''
    with open(filename, 'rb') as f:
        header_size = _get_header_size(f)
        start = header_size + skip * dtype.itemsize * (nchan + infochan)
        header = f.seek(start,1)
        if nspec < 0:
            data = np.frombuffer(f.read(), dtype=dtype)
        else:
            nbytes = nspec * dtype.itemsize * (nchan + infochan)
            data = np.frombuffer(f.read(nbytes), dtype=dtype)
    data.shape = (-1, infochan + nchan)
    return data

def read_file(filename, nspec=-1, skip=0, lo_hz=1350e6, nchan=NCHAN_DEFAULT,
              header_size=HEADER_SIZE, infochan=12, dtype=np.dtype('>u2')):
    '''Read header and data from a limbo file.'''
    hdr = read_header(filename, lo_hz=lo_hz, nchan=nchan,
                      header_size=header_size)
    data = read_raw_data(filename, nspec=nspec, skip=skip, header_size=header_size,
                         nchan=nchan, infochan=infochan, dtype=dtype)
    assert data.shape[0] > 0  # make sure we read some data
    data = data[:, infochan:]
    hdr['times'] = hdr['Time'] + np.arange(data.shape[0]) * hdr['inttime']
    t = Time(hdr['times'], format='unix', scale='utc')
    hdr['jds'] = t.jd
    hdr['date'] = t.strftime('%Y-%m-%d %H:%M:%S')[0]
    return hdr, data
