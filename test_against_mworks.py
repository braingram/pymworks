#!/usr/bin/env python

import os
import sys

import pymworks
import mworks.data

filename = os.path.realpath(sys.argv[1])

mf = mworks.data.MWKFile(filename)
mf.open()

pf = pymworks.IndexedDataFile("%s/%s" % (filename, os.path.basename(filename)))

mcodec = mf.codec
pcodec = pf.get_codec()

mcodes = [k for (k,v) in mcodec.iteritems() if k >=4]
pcodes = [k for (k,v) in pcodec.iteritems() if k >=4]

if mcodes != pcodes:
    print "Mcodes and Pcodes differed"
    print mcodes
    print "------------------"
    print pcodes
    sys.exit(1)

bad_codes = []

for c in mcodes:
    me = mf.get_events(codes=[c])
    pe = pf.get_events_by_code(c)
    mtv = [(e.time, e.value) for e in me]
    ptv = [(p[1], p[2]) for p in pe]
    if mtv != ptv:
        bad_codes.append((c, me[0], pe[0]))
        print "Events for code %i did not match" % c
    else:
        print "Code %i passed" % c

print bad_codes
if len(bad_codes) > 0:
    sys.exit(1)
else:
    print "All passed"
    sys.exit(0)
