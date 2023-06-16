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
    f.seek(0, 0)
    if(s==b'{'):
        header_size = HEADER_SIZE
    else:
        header_size = struct.unpack('I',f.read(4))[0]
    return header_size

def read_start_time(filename, dtype=np.dtype('<u4')):
    '''Read sec, usec from first spectrum in file.'''
    with open(filename, 'rb') as f:
        header_size = _get_header_size(f)
        f.seek(header_size + 4, 0)  # add size of "header_size" 
        # timestamp is 32b zeros, 32b sec, 32b zeros, 32b usec
        _, sec, _, usec = np.frombuffer(f.read(16), dtype=dtype)
    return float(sec) + float(usec) * 1e-6

def read_header(filename, lo_hz=1350e6, nchan=NCHAN_DEFAULT):
    '''Read header from a limbo file.'''
    start_t = read_start_time(filename)
    with open(filename, 'rb') as f:
        header_size = _get_header_size(f)
        h = f.read(header_size)
    h = json.loads(h[:h.find(0x00)])
    h['filename'] = filename
    h['sample_clock'] = h.pop('SampleFreq') * 1e6
    h['freqs'] = utils.calc_freqs(h['sample_clock'], lo_hz, nchan)
    h['inttime'] = utils.calc_inttime(h['sample_clock'], h['AccLen'], nchan)
    h['Time_created'] = h['Time']
    h['Time'] = start_t
    h['filesize'] = os.path.getsize(filename)
    h['data_start'] = header_size + 4  # add 4 for first 4B header_size
    return h

def read_raw_data(filename, hdr, nspec, skip, nchan, infochan, dtype):
    '''Read raw data from a limbo file.'''
    spec_len = dtype.itemsize * (nchan + infochan)
    with open(filename, 'rb') as f:
        start = hdr['data_start']
        start += skip * spec_len
        f.seek(start, 0)
        if nspec < 0:
            data = np.frombuffer(f.read(), dtype=dtype)
        else:
            nbytes = nspec * spec_len
            data = np.frombuffer(f.read(nbytes), dtype=dtype)
    data.shape = (-1, infochan + nchan)
    return data

def read_file(filename, nspec=-1, skip=0, lo_hz=1350e6, nchan=NCHAN_DEFAULT,
              infochan=12, dtype=np.dtype('>u2')):
    '''Read header and data from a limbo file.'''
    hdr = read_header(filename, lo_hz=lo_hz, nchan=nchan)
    hdr['nspec'] = (hdr['filesize'] - hdr['data_start']) // (dtype.itemsize * (nchan + infochan))
    data = read_raw_data(filename, hdr, nspec, skip, nchan, infochan, dtype)
    assert data.shape[0] > 0  # make sure we read some data
    data = data[:, infochan:]
    hdr['times'] = hdr['Time'] + np.arange(skip, skip + data.shape[0]) * hdr['inttime']
    t = Time(hdr['times'], format='unix', scale='utc')
    hdr['jds'] = t.jd
    hdr['date'] = t.strftime('%Y-%m-%d %H:%M:%S')[0]
    return hdr, data

def read_volt_file(filename, nspec=-1, skip=0, lo_hz=1350e6, nchan=NCHAN_DEFAULT,
                   infochan=24, npol=2):
    '''Read header and data from a limbo file.'''
    hdr = read_header(filename, lo_hz=lo_hz, nchan=nchan)
    hdr['nspec'] = (hdr['filesize'] - hdr['data_start']) // (np.dtype('>u1').itemsize * (npol * nchan + infochan))
    # read data as longlong and perform endian swap to fix a missed endian
    # swap when voltage files are written from 64b network words
    data = read_raw_data(filename, hdr, nspec, skip, npol*nchan//8,
                         infochan//8, np.dtype('>u8'))
    assert data.shape[0] > 0  # make sure we read some data
    data = data[:, infochan//8:].byteswap().view('>u1')  # endian swap
    data.shape = (-1, NCHAN_DEFAULT, npol)  # polarization is the fastest array axis
    data_real = (data & 0xf0).view('>i1') >> 4
    data_imag = ((data << 4) & 0xf0).view('>i1') >> 4
    hdr['times'] = hdr['Time'] + np.arange(skip, skip + data.shape[0]) * hdr['inttime'] # VS 'Time' = start time of file
    t = Time(hdr['times'], format='unix', scale='utc')
    hdr['jds'] = t.jd
    hdr['date'] = t.strftime('%Y-%m-%d %H:%M:%S')[0]
    return hdr, data_real, data_imag
