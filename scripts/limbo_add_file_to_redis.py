#! /usr/bin/env python

import redis
import sys
import os

r = redis.Redis('localhost', decode_responses=True)

for f in sys.argv[1:]:
    f = os.path.basename(f)
    if not f.endswith('dat'):
        print(f'Skipping {f}')
    else:
        print(f'Adding {f} to queue')
        r.rpush('limbo:raw_pspec_files', f)
