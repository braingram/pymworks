#!/usr/bin/env python

import json
import os
import sys

import pymworks
import tables

import numpy

try:
    import mworks.data
    MWORKS_AVAILABLE = True
except ImportError:
    MWORKS_AVAILABLE = False


class MworksFile(object):
    def __init__(self, filename):
        if not MWORKS_AVAILABLE:
            raise Exception("mworks.data not available")
        self._filename = filename
        self._file = mworks.data.MWKFile(filename)
        self._file.open()

    def get_codec(self):
        return self._file.codec

    codec = property(get_codec)

    def get_events(self, code):
        return sorted(self._file.get_events(codes=[code]), \
                key=lambda e: e.time)


class TableFile(object):
    def __init__(self, filename):
        self._filename = filename
        self._file = tables.openFile(filename, 'r')
        if len(self._file.root.__members__) != 1:
            raise ValueError(\
                    "Invalid h5 file structure: root.__members__ == %s" \
                    % str(self._file.root.__members__))
        self._group = self._file.getNode('/' + self._file.root.__members__[0])
        self._codec = None

    def get_codec(self):
        if self._codec is None:
            self._codec = dict([(r['code'], r['name']) for r \
                    in self._group.codec])
        return self._codec

    codec = property(get_codec)

    def get_events(self, code):
        events = []
        for r in self._group.events.where('code == %i' % code):
            events.append(pymworks.Event([code, r['time'], \
                    json.loads(self._group.values[r['index']])]))
        return sorted(events, key=lambda e: e.time)


def compare_codecs(c1, c2):
    codes1 = [k for (k, v) in c1.iteritems() if k >= 4]
    codes2 = [k for (k, v) in c2.iteritems() if k >= 4]
    if codes1 != codes2:
        print "Codes differ"
        print codes1
        print "-----"
        print codes2
        return False
    return True


def get_bad_events(f1, f2, key1=lambda f, c: f.get_events(c), \
        key2=lambda f, c: f.get_events(c)):
    codes = [c for c in f1.codec.keys() if c >= 4]
    for c in codes:
        events1 = key1(f1, c)
        events2 = key2(f2, c)
        tv1 = [(e.time, e.value) for e in events1]
        tv2 = [(e.time, e.value) for e in events2]
        if tv1 != tv2:
            for e1, e2 in zip(events1, events2):
                if (e1.time != e2.time):
                    yield e1, e2
                elif (numpy.isnan(e1.value) and numpy.isnan(e2.value)):
                    pass
                elif (e1.value != e2.value):
                    yield e1, e2
                elif (e1.code != e2.code):
                    yield e1, e2


def compare_events(f1, f2, key1=lambda f, c: f.get_events(c), \
        key2=lambda f, c: f.get_events(c)):
    codec = f1.codec  # assumes codes are the same
    bad_names = {}
    for e1, e2 in get_bad_events(f1, f2, key1, key2):
        name = codec[e1.code]
        if name not in bad_names.keys():
            bad_names[name] = {'codes': 0, 'times': 0, 'values': 0, 'n': 0}
        dn = 0
        if (e1.time != e2.time):
            bad_names[name]['times'] += 1
            dn = 1
        if (e1.code != e2.code):
            bad_names[name]['codes'] += 1
            dn = 1
        if (e1.value != e2.value):
            bad_names[name]['values'] += 1
            dn = 1
        bad_names[name]['n'] += dn

    if len(bad_names):
        print
        print "Bad Event Names:"
        for k, v in bad_names.iteritems():
            print "  Name:", k
            print "    N    Events:", v['n']
            print "    Code Errors:", v['codes']
            print "    Time Errors:", v['times']
            print "    Val  Errors:", v['values']
        return False
    return True


def load_h5(filename):
    h5filename = os.path.splitext(filename)[0] + '.h5'

    mf = TableFile(h5filename)
    pf = pymworks.open_file(filename)
    return mf, pf


def load_mworks(filename):
    pyfilename = "%s/%s" % (filename, os.path.basename(filename))

    mf = MworksFile(filename)
    pf = pymworks.open_file(pyfilename)
    return mf, pf


def compare_files(f1, f2):
    if not compare_codecs(f1.codec, f2.codec):
        return False
    if not compare_events(f1, f2):
        return False
    print "All passed"
    return True


if __name__ == '__main__':
    f1, f2 = load_h5(os.path.realpath(sys.argv[1]))
    #f1, f2 = load_mworks()
    if not compare_files(f1, f2):
        sys.exit(1)
    sys.exit(0)
