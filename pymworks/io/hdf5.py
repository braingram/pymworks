#!/usr/bin/env python


import cPickle as pickle

import tables

from ..events.event import Event
import datafile


def validate_path(p):
    if (len(p) == 0) or (p[0] != '/'):
        raise ValueError('Invalid HDF5 Path: %s' % p)
    if len(p) == 1:
        return True
    tokens = p.split('/')
    if len(tokens) > 3:
        raise NotImplementedError('HDF5 Path cannot have > 1 group: %s' % p)
    return True


def parse_path(p):
    tokens = p.split('/')
    if len(tokens) == 2:
        return '/', tokens[1]
    if len(tokens) == 3:
        return '/' + tokens[1], tokens[2]
    raise ValueError('Invalid path: %s' % p)


def make_match_string(key, to_code):
    codes = datafile.key_to_code(key, to_code)
    if codes is None:
        codes = []
    if not isinstance(codes, (tuple, list)):
        codes = [codes, ]
    return ' | '.join(['code == %i' % c for c in codes])


class HDF5Event(tables.IsDescription):
    code = tables.UInt32Col()
    time = tables.UInt64Col()
    index = tables.UInt64Col()  # points to index in values VLArray


class HDF5DataFile(datafile.DataFile):
    def __init__(self, filename, autoconnect=True, autoresolve=True,
                 events_path='/mwk/events', values_path='/mwk/values',
                 vsize=1.0):
        datafile.DataFile.__init__(self, filename,
                                   autoconnect=False, autoresolve=False)
        self._events_path = events_path
        self._values_path = values_path
        self._vsize = 1.0
        # test if filename is actually a file
        if isinstance(filename, tables.file.File):
            self.file = filename
            self.filename = filename.filename
        else:
            self.filename = datafile.resolve_filename(filename) if \
                autoresolve else filename
            self.file = None
        self._event_index = 0
        if autoconnect:
            self.connect()

    def connect(self):
        if self._connected:
            return
        if self.file is None:
            self.file = tables.openFile(self.filename, 'r')
        datafile.Source.connect(self)

    def disconnect(self):
        if not self._connected:
            return
        self.file.flush()
        self.file.close()
        datafile.Source.disconnect(self)

    def restart_file(self):
        self.require_connected()
        self._event_index = 0

    #def find_codec(self):
    #    pass

    def _setup_file(self):
        validate_path(self._events_path)
        if self._events_path not in self.file:
            g, n = parse_path(self._events_path)
            if g not in self.file:
                r, gn = parse_path(g)
                self.file.createGroup(r, gn)
            self.file.createTable(g, n, HDF5Event)
        validate_path(self._values_path)
        if self._values_path not in self.file:
            g, n = parse_path(self._values_path)
            if g not in self.file:
                r, gn = parse_path(g)
                self.file.createGroup(r, gn)
            self.file.createVLArray(g, n, tables.VLStringAtom(),
                                    expectedsizeinMB=self._vsize)

    def _parse_event_row(self, er, vn=None):
        vn = self.file.getNode(self._values_path) if vn is None else vn
        name = self._codec.get(er['code'], None) if \
            (self._codec is not None) else None
        return Event(er['code'], er['time'],
                     pickle.loads(vn[er['index']]), name, 2)

    def read_event(self):
        self.require_connected()
        # get next event, or None
        en = self.file.getNode(self._events_path)
        if (self._event_index >= en.nrows):
            return None
        i = self._event_index
        self._event_index += 1
        return self._parse_event_row(en[i])

    def write_event(self, event, flush_every_n=100):
        """
        Can accepts tuples and lists of events
        """
        if not (('w' in self.file.mode) or ('a' in self.file.mode)):
            raise IOError('HDF5DataFile.file is not writable: %s'
                          % self.file.mode)
        self._setup_file()
        if not isinstance(event, (tuple, list)):
            event = (event, )
        en = self.file.getNode(self._events_path)
        row = en.row
        va = self.file.getNode(self._values_path)
        for (i, e) in enumerate(event):
            row['code'] = e.code
            row['time'] = e.time
            vs = pickle.dumps(e.value, 2)
            row['index'] = len(va)
            va.append(vs)
            row.append()
            if (i % flush_every_n == 0):
                va.flush()
                en.flush()
        va.flush()
        en.flush()

    def get_events(self, key=None, time_range=None):
        ms = make_match_string(key, self.to_code)
        en = self.file.getNode(self._events_path)
        vn = self.file.getNode(self._values_path)
        if ms == '':
            evs = lambda: en
        else:
            evs = lambda: en.where(ms)
        if time_range is not None:
            ttest = datafile.make_time_test(time_range, self.to_code)
            return [self._parse_event_row(e, vn) for e in evs()
                    if ttest(e)]
        else:
            return [self._parse_event_row(e, vn) for e in evs()]
