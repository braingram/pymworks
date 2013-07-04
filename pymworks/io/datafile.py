#!/usr/bin/env python

import collections
import hashlib
import logging
import os
#import pickle
import cPickle as pickle

from ..events.event import Event
from base import Source, Sink
from raw import LDOBinary


def key_to_code(key, to_code):
    if isinstance(key, (tuple, list)):
        return [key_to_code(k, to_code) for k in key]
    if isinstance(key, str):
        return to_code(key)
    return key


def make_key_test(key, to_code):
    if key is None:
        return lambda e: True
    elif isinstance(key, (tuple, list)):
        codes = [key_to_code(k, to_code) for k in key]
        return lambda e: e.code in codes
    code = key_to_code(key, to_code)
    return lambda e: e.code == code


def make_time_test(time_range, to_code):
    if time_range is None:
        return lambda e: True
    else:
        if not isinstance(time_range, (tuple, list)):
            raise ValueError("time_range must be tuple or list: %s"
                             % time_range)
        if len(time_range) != 2:
            raise ValueError("time_range must be len == 2: %s" %
                             len(time_range))
        return lambda e: time_range[0] < e.time < time_range[1]


def make_tests(key, time_range, to_code):
    return make_key_test(key, to_code), \
        make_time_test(time_range, to_code)


def resolve_filename(filename):
    """
    Helper function to deal with datafiles opened by the
    old python mworks module

    With the old module, when opening a file for the first time
    an index would be created and a directory with the same name and path
    as the file would be created. The original datafile would be placed
    inside this directory for example

    /home/user/foo.mwk

    would become

    /home/user/foo.mwk/foo.mwk

    If autoresolve is True, pymworks will try to work around this by
    resolving filenames that point to directories to filenames inside that
    directory
    """
    if not isinstance(filename, (str, unicode)):
        return filename
    if os.path.isdir(filename):
        d, n = os.path.split(filename)
        return os.path.join(d, n, n)
    return filename


def open_filename(fn, *args):
    if hasattr(fn, 'read'):
        return fn
    return open(fn, *args)


def filename_name(fn):
    if hasattr(fn, 'name'):
        return fn.name
    return fn


class DataFile(Source):
    def __init__(self, filename, autoconnect=True, autoresolve=True):
        Source.__init__(self, autoconnect=False)
        self.filename = resolve_filename(filename) if autoresolve \
            else filename
        if autoconnect:
            self.connect()
        # for backwards compatibility
        self.close = self.disconnect

    def connect(self):
        if self._connected:
            return
        self.file = open_filename(self.filename, 'rb')
        self.ldo = LDOBinary.LDOBinaryUnmarshaler(self.file)
        #self.file.seek(0)
        #self.ldo.read_stream_handler = 0
        #self.ldo.um_init()
        Source.connect(self)
        self.restart_file()

    def restart_file(self):
        self.require_connected()
        self.file.seek(0)
        self.ldo.read_stream_header = 0
        self.ldo.um_init()

    def disconnect(self):
        if not self._connected:
            return
        del self.ldo
        self.file.close()
        Source.disconnect(self)

    # to_code
    # to_name
    # get_codec
    # get_reverse_codec
    # process_codec_event
    # find_codec

    def _find_time_range(self):
        self.restart_file()
        e = self.read_event()
        if e is None:
            raise ValueError("Failed to read first event[%s]" % e)
        self._mintime = e.time
        self._maxtime = e.time
        while e is not None:
            self._mintime = min(e.time, self._mintime)
            self._maxtime = max(e.time, self._maxtime)
            e = self.read_event()
        return self._mintime, self._maxtime

    #def get_minimum_time(self):
    #    if self._mintime is None:
    #        self._find_time_range()
    #    return self._mintime

    #def get_maximum_time(self):
    #    if self._maxtime is None:
    #        self._find_time_range()
    #    return self._maxtime

    def find_codec(self):
        if self._codec is None:
            cevs = self.get_events(0)
            if len(cevs) == 0:
                raise LookupError("Failed to find codec")
            self.process_codec_event(cevs[-1])
        if self._codec is None:
            raise LookupError("Failed to find codec")

    def read_event(self):
        self.require_connected()
        try:
            e = Event(*self.ldo.load())
            if (self._codec is not None) and (e.code in self._codec):
                e.name = self._codec[e.code]
            return e
        except EOFError:
            return None
        except TypeError:
            logging.warning("Event before %i was missing required code, "
                            "time, and/or value" % self.file.tell())
            return None

    def __iter__(self):
        self.restart_file()
        for e in Source.__iter__(self):
            yield e

    def write_event(self, event):
        raise NotImplementedError("Datafile does not allow writing")

    def get_events(self, key=None, time_range=None):
        kt, tt = make_tests(key, time_range, self.to_code)
        #kt, tt
        events = []
        self.restart_file()
        e = self.read_event()
        if e is None:
            raise ValueError("Failed to read first event[%s]" % e)
        andtime = ((self._mintime is None) or (self._maxtime is None))
        if andtime:
            self._mintime = e.time
            self._maxtime = e.time
        while e is not None:
            if kt(e) and tt(e):
                events.append(e)
            if andtime:
                self._mintime = min(e.time, self._mintime)
                self._maxtime = max(e.time, self._maxtime)
            e = self.read_event()
        return sorted(events, key=lambda e: e.time)


class IndexedDataFile(DataFile):
    """
    Indexed data file reader class

    Index is a collections.defaultdict with:
        key = event code
        value = file locations of events
    """
    def __init__(self, filename, autoconnect=True, autoresolve=True,
                 index_filename=None, check_hash=True):
        DataFile.__init__(self, filename, autoconnect=False,
                          autoresolve=autoresolve)
        self._check_hash = check_hash
        self.index_filename = '%s/.%s.index' % \
            os.path.split(os.path.realpath(filename_name(
                self.filename))) if index_filename \
            is None else index_filename
        if autoconnect:
            self.connect()

    def connect(self):
        if self._connected:
            return
        DataFile.connect(self)
        self._load_index()

    def _load_index(self):
        """ Load index from files """
        if hasattr(self.index_filename, 'read') or \
                os.path.exists(self.index_filename):
            try:
                self._index = pickle.load(open_filename(
                    self.index_filename, 'rb'))
                if type(self._index) != dict:
                    raise TypeError("loaded index(%s) was wrong type: %s" %
                                    (self.index_filename, type(self._index)))
                self._parse_index()
                if self._mintime is None:
                    raise Exception(
                        "Found bad index [_mintime is None], reindexing")
                if self._check_hash:
                    file_hash = self._hash_file()
                    if self._hash != file_hash:
                        raise Exception("File hash[%s] != stored hash[%s]" %
                                        (self._hash, file_hash))
            except Exception as E:
                logging.warning("Failed to load index file[%s]: %s" %
                                (self.index_filename, E))
                self._index_file()
        else:
            logging.debug("Index does not exist: %s" % self.index_filename)
            self._index_file()

    def _index_file(self):
        """ Create an index of the file """
        self.require_connected()
        logging.info("indexing file: %s" % self.filename)
        self._index = collections.defaultdict(list)
        # need to do this manually (rather than calling all_events)
        # to keep track of the file position
        self.restart_file()
        position = self.file.tell()
        event = self.read_event()
        if event is None:
            raise ValueError("Failed to read first event[%s]" % event)
        self._mintime = event.time
        self._maxtime = event.time
        while event is not None:
            self._index[event.code].append(position)
            position = self.file.tell()
            self._mintime = min(event.time, self._mintime)
            self._maxtime = max(event.time, self._maxtime)
            event = self.read_event()

        self._index = dict(self._index)
        for code in self.codec.keys():
            if code not in self._index:
                self._index[code] = []

        # get codec and time ranges
        self._index.update({
            #'_codec': self.codec,
            '_mintime': self._mintime,
            '_maxtime': self._maxtime,
            '_hash': self._hash_file(),
        })

        self._parse_index()
        self._index['_hash'] = self._hash
        self._save_index(open_filename(self.index_filename, 'wb'))

    def _save_index(self, f):
        if not hasattr(f, 'write'):
            with open(f, 'wb') as f:
                # save index to file
                pickle.dump(self._index, f, 2)
        else:
            pickle.dump(self._index, f, 2)

    def _parse_index(self):
        self._hash = self._index['_hash']
        #self._codec = self._index['_codec']
        self._mintime = self._index['_mintime']
        self._maxtime = self._index['_maxtime']
        self.find_codec()

    def _hash_file(self):
        md5 = hashlib.md5()
        with open(self.filename, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                md5.update(chunk)
        return md5.digest()

    def _event_at(self, position):
        """
        Return an event at a file position
        """
        self.require_connected()
        self.file.seek(position)
        return self.read_event()

    # overload event fetching to use index
    def get_events(self, key=None, time_range=None):
        if key is None:
            return DataFile.get_events(self, key, time_range)
        tt = make_time_test(time_range, self.to_code)
        codes = key_to_code(key, self.to_code)
        if not isinstance(codes, (tuple, list)):
            codes = [codes, ]
        events = []
        indices = reduce(lambda x, y: x + y,
                         [self._index[code] for code in codes])
        for i in sorted(indices):
            e = self._event_at(i)
            if tt(e):
                events.append(e)
        return events


class DataFileWriter(Sink):
    def __init__(self, filename, autoconnect=True):
        Sink.__init__(self, autoconnect=False)
        if hasattr(filename, 'write'):
            self.file = filename
            self.filename = None
        else:
            self.filename = filename
            self.file = open(self.filename, 'wb')
        if autoconnect:
            self.connect()

    def connect(self):
        self.ldo = LDOBinary.LDOBinaryMarshaler(self.file)
        self.ldo.m_init()
        Sink.connect(self)

    def disconnect(self):
        del self.ldo
        self.file.close()
        Sink.disconnect(self)

    def write_event(self, event):
        """
        Can accepts tuples and lists of events
        or mwk event sources (see Source.__iter__)
        """
        self.require_connected()
        if isinstance(event, Event):
            event = (event, )
        for e in event:
            self.ldo._marshal([e.code, e.time, e.value])


def open_file(fn, indexed=True):
    if indexed:
        return IndexedDataFile(fn)
    return DataFile(fn)


def save_file(mwks, filename, index=None):
    w = DataFileWriter(filename)
    w.write_event(mwks)
    if (index is not None) and hasattr(mwks, '_save_index'):
        mwks._save_index(index)
    w.disconnect()
