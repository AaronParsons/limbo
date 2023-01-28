import numpy as np
cimport numpy as np
import cython

@cython.boundscheck(False)
@cython.wraparound(False)
@cython.cdivision(True) 
def phs_sum(np.ndarray [np.complex64_t, ndim=2] d,
            np.ndarray [np.complex64_t, ndim=2] p):
    cdef int i, j
    cdef float complex buf1, buf2
    for i in range(d.shape[0]):
        for j in range(0, d.shape[1], 2):
            buf1 = d[i, j] + d[i, j + 1]
            buf2 = p[i, j] * d[i, j] + p[i, j + 1] * d[i, j + 1]
            d[i, j] = buf1
            d[i, j + 1] = buf2
    return
