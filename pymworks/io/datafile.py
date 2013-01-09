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
        if isinstance(time_range, (tuple, list)):
            raise ValueError("time_range must be tuple or list: %s" \
                    % time_range)
        if len(time_range) != 2:
            raise ValueError("time_range must be len == 2: %s" % \
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
    if os.path.isdir(filename):
        d, n = os.path.split(filename)
        return os.path.join(d, n, n)
    return filename


class DataFile(Source):
    def __init__(self, filename, autostart=True, autoresolve=True):
        Source.__init__(self, autostart=False)
        self.filename = resolve_filename(filename) if autoresolve else filename
        if autostart:
            self.start()
        # for backwards compatibility
        self.close = self.stop

    def start(self):
        if self._running:
            return
        self.file = open(self.filename, 'rb')
        self.ldo = LDOBinary.LDOBinaryUnmarshaler(self.file)
        #self.file.seek(0)
        #self.ldo.read_stream_handler = 0
        #self.ldo.um_init()
        Source.start(self)
        self.restart_file()

    def restart_file(self):
        self.require_running()
        self.file.seek(0)
        self.ldo.read_stream_header = 0
        self.ldo.um_init()

    def stop(self):
        if not self._running:
            return
        del self.ldo
        self.file.close()
        Source.stop(self)

    # to_code
    # to_name
    # get_codec
    # get_reverse_codec
    # process_codec_event
    # find_codec
    def find_codec(self):
        if self._codec is None:
            cevs = self.get_events(0)
            if len(cevs) == 0:
                raise LookupError("Failed to find codec")
            self.process_codec_event(cevs[-1])
        if self._codec is None:
            raise LookupError("Failed to find codec")

    def read_event(self):
        self.require_running()
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

    def write_event(self):
        raise NotImplementedError("Datafile does not allow writing")

    def get_events(self, key=None, time_range=None):
        kt, tt = make_tests(key, time_range, self.to_code)
        #kt, tt
        events = []
        self.restart_file()
        e = self.read_event()
        while e is not None:
            if kt(e) and tt(e):
                events.append(e)
            e = self.read_event()
        return sorted(events, key=lambda e: e.time)


class IndexedDataFile(DataFile):
    """
    Indexed data file reader class

    Index is a collections.defaultdict with:
        key = event code
        value = file locations of events
    """
    def __init__(self, filename, autostart=True, autoresolve=True):
        DataFile.__init__(self, filename, autostart=False, \
                autoresolve=autoresolve)
        if autostart:
            self.start()

    def start(self):
        if self._running:
            return
        DataFile.start(self)
        self._load_index()

    def _load_index(self):
        """ Load index from files """
        index_filename = '%s/.%s.index' % \
                os.path.split(os.path.realpath(self.filename))
        if os.path.exists(index_filename):
            try:
                with open(index_filename, 'rb') as index_file:
                    self._index = pickle.load(index_file)
                    if type(self._index) != dict:
                        wrong_type = type(self._index)
                        raise TypeError("loaded index(%s) was "
                                "wrong type: %s" % \
                                        (index_filename, str(wrong_type)))
                    self._parse_index()
                    file_hash = self._hash_file()
                    if self._hash != file_hash:
                        logging.debug("File hashes did not match")
                        raise Exception("File hash[%s] != stored hash[%s]" % \
                                (self._hash, file_hash))
            except Exception as E:
                logging.warning("Failed to load index file(%s): %s" % \
                        (index_filename, str(E)))
                self._index_file(index_filename)
        else:
            logging.debug("Index file(%s) did not exist" % index_filename)
            self._index_file(index_filename)

    def _index_file(self, index_filename):
        """ Create an index of the file """
        self.require_running()
        logging.info("indexing file: %s" % self.filename)
        self._index = collections.defaultdict(list)
        # need to do this manually (rather than calling all_events)
        # to keep track of the file position
        self.restart_file()
        position = self.file.tell()
        event = self.read_event()
        while event is not None:
            self._index[event.code].append(position)
            position = self.file.tell()
            event = self.read_event()

        self._index = dict(self._index)
        for code in self.codec.keys():
            if code not in self._index:
                self._index[code] = []

        # get codec and time ranges
        self._index.update({ \
                '_codec': self.codec, \
                '_mintime': self.minimum_time, \
                '_maxtime': self.maximum_time, \
                '_hash': self._hash_file(), \
                })

        self._parse_index()
        self._index['_hash'] = self._hash

        # save index to file
        with open(index_filename, 'wb') as index_file:
            pickle.dump(self._index, index_file, 2)

    def _parse_index(self):
        self._hash = self._index['_hash']
        self._codec = self._index['_codec']
        self._mintime = self._index['_mintime']
        self._maxtime = self._index['_maxtime']

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
        self.require_running()
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
        for code in codes:
            for p in self._index[code]:
                e = self._event_at(p)
                if tt(e):
                    events.append(e)
        return events


class DataFileWriter(Sink):
    def __init__(self, filename, autostart=True):
        Sink.__init__(self, autostart=False)
        self.filename = filename
        if autostart:
            self.start()

    def start(self):
        self.file = open(self.filename, 'wb')
        self.ldo = LDOBinary.LDOBinaryMarshaler(self.file)
        self.ldo.m_init()
        Sink.start(self)

    def stop(self):
        del self.ldo
        self.file.close()
        Sink.stop(self)

    def write_event(self, event):
        self.require_running()
        self.ldo._marshal([event.code, event.time, event.value])


def open_file(fn, indexed=True):
    if indexed:
        return IndexedDataFile(fn)
    return DataFile(fn)
