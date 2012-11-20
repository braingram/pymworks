#!/usr/bin/env python

import json
import logging
import os

import tables


codecNameLen = 32  # maximum length of variable name


class Event(tables.IsDescription):
    code = tables.UInt32Col()
    time = tables.UInt64Col()
    index = tables.UInt64Col()


class CodecEntry(tables.IsDescription):
    code = tables.UInt32Col()
    name = tables.StringCol(codecNameLen)


class HDF5Sink(object):
    """
    Generic datafile conversion sink.

    Implement at least two functions:

    __init__(self, filename)
    convert(self, datafile)
    """
    def __init__(self, filename):
        self._file = tables.openFile(filename, mode="w", \
                title="Pymworks converted datafile")
        self._filename = filename
        pass

    def convert(self, datafile):
        self.setup(datafile)
        self.write_codec(datafile.codec)
        self.write_events(datafile.get_events())

    def setup(self, datafile):
        logging.debug("Setting up HDF5 file %s" % self._filename)
        session = os.path.splitext(os.path.basename(datafile.filename))[0]
        logging.debug("Found session for datafile: %s" % session)
        self._group = self._file.createGroup("/", session, \
                "Data for session %s" % session)
        self._events = self._file.createTable(self._group, "events", \
                Event, "Events")
        self._codec = self._file.createTable(self._group, "codec", \
                CodecEntry, "Codec")
        self._values = self._file.createVLArray(self._group, "values", \
                tables.VLStringAtom(), "Values", expectedsizeinMB=0.0001)

    def write_codec(self, codec):
        logging.debug("Writing codec[%i keys] to file %s" % \
                (len(codec.keys()), self._filename))
        maxLen = 0
        maxStr = ""
        row = self._codec.row
        for (code, name) in codec.iteritems():
            row['name'] = name
            row['code'] = code
            if len(name) > maxLen:
                maxLen = len(name)
                maxStr = name
            row.append()
        logging.debug("len(longest_codec_name) = %i: %s" % (maxLen, maxStr))
        if maxLen > codecNameLen:
            logging.error("Codec name %s was too long %i > %i" % \
                    (maxStr, maxLen, codecNameLen))
        self._file.flush()

    def write_events(self, events):
        logging.debug("Writing events to file %s" % self._filename)
        row = self._events.row
        for e in events:
            # TODO blacklist here
            row['code'] = e.code
            row['time'] = e.time
            vs = json.dumps(e.value)
            row['index'] = len(self._values)
            self._values.append(vs)
            row.append()
        self._file.flush()

    def close(self):
        self._file.flush()
        self._file.close()

    def __del__(self):
        self.close()
        del self._file


def datafile_to_hdf5(datafile, filename):
    """
    Convert a pymworks datafile to a hdf5 file
    """
    h = HDF5Sink(filename)
    h.convert(datafile)
    h.close()
