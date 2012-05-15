#!/usr/bin/env python

import math

import pymworks.datafile

infilename = 'M2_120302.mwk'
outfilename = 'test.mwk'

df = pymworks.datafile.DataFile(infilename)

dfw = pymworks.datafile.DataFileWriter(outfilename)

print "writing events to new file"
for e in df.all_events:
    dfw.write_event(e)

dfw.close()

ndf = pymworks.datafile.DataFile(outfilename)

df.restart()

print "comparing old and new events"
for oe, ne in zip(df.all_events, ndf.all_events):
    if (oe == ne) or (math.isnan(oe.value) and math.isnan(ne.value)):
        pass
    else:
        raise ValueError("events don't match: %s, %s" % (oe, ne))

df.close()
ndf.close()
