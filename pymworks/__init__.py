#!/usr/bin/env python

import collections
import logging
import os
import pickle

import LDOBinary

import numpy


class Event(list):
    @property
    def code(self):
        return self[0]

    @property
    def time(self):
        return self[1]

    @property
    def value(self):
        return self[2]


class DataFile:
    def __init__(self, filename):
        self.filename = filename
        self.file = open(self.filename, 'rb')
        self.ldo = LDOBinary.LDOBinaryUnmarshaler(self.file)
        self.restart()  # call this to properly run um_init
        self._codec = None
        self._maxtime = None
        self._mintime = None

    # ------  file handling  ------
    def restart(self):
        """ Restart reading the file from the beginning """
        self.file.seek(0)
        self.ldo.read_stream_header = 0
        self.ldo.um_init()

    def close(self):
        del self.ldo
        self.file.close()

    # ------  event handling  ------
    def next_event(self):
        """ Get the next event in the file"""
        try:
            return Event(self.ldo.load())
        except EOFError:
            return None

    def to_code(self, name):
        """ Lookup code for an event name """
        try:
            return self.rcodec[name]
        except IndexError:
            raise ValueError("Event Name[%s] not found in codec" % name)

    def to_name(self, code):
        """ Lookup name for a event code """
        try:
            return self.codec[code]
        except IndexError:
            raise ValueError("Event Code[%i] not found in codec" % code)

    def get_all_events(self):
        self.restart()
        event = self.next_event()
        while event is not None:
            yield event
            event = self.next_event()

    all_events = property(get_all_events)

    def key_to_test(self, key):
        """
        Convert an event key (either code[int] or name[str]) to a test function
        that returns True if a passed in event matches the key

        key can any of these types:
            int, numpy.integer
            str, numpy.str
            list, tuple, ndarray of str or int or mix of str & int
        """
        if key is None:
            return lambda e: True
        elif isinstance(key, str):
            return self.key_to_test(self.to_code(key))
        elif isinstance(key, (int, numpy.integer)):
            return lambda e: e.code == key
        elif isinstance(key, (tuple, list, numpy.ndarray)):
            codes = map(lambda k: self.to_code(k) if isinstance(k, str) \
                    else k, key)
            return lambda e: e.code in codes

    def time_range_to_test(self, time_range):
        """
        Convert a time_range (2 length tuple/list/ndarray) to a test function
        that returns True if a passed in event falls within the time range:
            time_range[0] < time < time_range[1]
        """
        if time_range is None:
            return lambda e: True
        elif isinstance(time_range, (tuple, list, numpy.ndarray)):
            if len(time_range) != 2:
                raise ValueError("Time range [len:%i] must be length 2" % \
                        len(time_range))
            return lambda e: time_range[0] < e.time < time_range[1]

    def get_events(self, key=None, time_range=None):
        if key is None:
            if time_range is None:
                events = self.all_events
            else:
                events = filter(self.time_range_to_test(time_range), \
                        self.all_events)
        else:  # key is not None
            if time_range is None:
                events = filter(self.key_to_test(key), \
                        self.all_events)
            else:
                kt = self.key_to_test(key)
                tt = self.time_range_to_test(time_range)
                events = filter(lambda e: (kt(e) and tt(e)), \
                        self.all_events)
        return sorted(events, key=lambda e: e.time)

    def events(self, *args, **kwargs):
        return self.get_events(*args, **kwargs)

    # ------  codec handling ------
    def find_codec(self):
        """ Search the file for the codec """
        codecs = self.get_events(0)
        #codecs = self.get_events_by_code(0)  # codec code is 0
        if len(codecs) == 0:
            raise ValueError("Unable to find codec")
        elif len(codecs) > 1:
            logging.warning("File contains more than one codec")
            for other_codec in codecs[1:]:
                if codecs[0][2] != other_codec[2]:
                    logging.error("File contains two codecs that differ")
                    raise Exception("File contains two codecs that differ")

        # parse codec event into codec and add missing values
        return dict([(k, v['tagname']) for k, v in \
                codecs[-1].value.iteritems()] + \
                [(0, '#codec'), (1, '#systemEvent'), \
                (2, '#components'), (3, '#termination')])

    def get_codec(self):
        """
        Return the files codec
        If not previously found this function will search for the codec
        """
        if self._codec is None:
            position = self.file.tell()
            try:
                self._codec = self.find_codec()
            except Exception as E:
                self.file.seek(position)
                raise E
        return self._codec

    codec = property(get_codec)

    def get_reverse_codec(self):
        return dict([(v, k) for k, v in self.codec.iteritems()])

    rcodec = property(get_reverse_codec)

    # ------  time handling ------
    def get_maximum_time(self):
        if self._maxtime is None:
            self._mintime, self._maxtime = self.find_time_range()
        return self._maxtime

    def get_minimum_time(self):
        if self._mintime is None:
            self._mintime, self._maxtime = self.find_time_range()
        return self._mintime

    def find_time_range(self):
        """
        Find minimum and maximum event times
        """
        position = self.file.tell()
        try:
            mintime = numpy.inf
            maxtime = 0
            for event in self.all_events:
                mintime = min(event.time, mintime)
                maxtime = max(event.time, maxtime)
        except Exception as E:
            self.file.seek(position)
            raise E
        self.file.seek(position)
        return mintime, maxtime

    minimum_time = property(get_minimum_time)
    maximum_time = property(get_maximum_time)


class IndexedDataFile(DataFile):
    """
    Indexed data file reader class

    Index is a collections.defaultdict with:
        key = event code
        value = file locations of events
    """
    def __init__(self, filename):
        DataFile.__init__(self, filename)
        self.load_index()
        #self.index_file()

    def load_index(self):
        """ Load index from files """
        index_filename = '%s/.%s.index' % \
                os.path.split(os.path.realpath(self.filename))
        if os.path.exists(index_filename):
            try:
                with open(index_filename, 'rb') as index_file:
                    self.event_index = pickle.load(index_file)
                    if type(self.event_index) != collections.defaultdict:
                        wrong_type = type(self.event_index)
                        raise TypeError("loaded event_index(%s) was "
                                "wrong type: %s" % \
                                        (index_filename, str(wrong_type)))
            except Exception as E:
                logging.warning("Failed to load index file(%s): %s" % \
                        (index_filename, str(E)))
                self.index_file(index_filename)
        else:
            logging.debug("Index file(%s) did not exist" % index_filename)
            self.index_file(index_filename)

    def index_file(self, index_filename):
        """ Create an index of the file """
        logging.info("indexing file: %s" % self.filename)
        self.event_index = collections.defaultdict(list)
        self.restart()
        position = self.file.tell()
        event = self.next_event()
        while not (event is None):
            # record file position of event
            self.event_index[event.code].append(position)
            # get next event
            position = self.file.tell()
            event = self.next_event()

        # save index to file
        with open(index_filename, 'wb') as index_file:
            pickle.dump(self.event_index, index_file, 2)

    # overload event fetching to use index
    def get_events_by_code(self, code, time_range=[-1, numpy.inf]):
        """
        Search the file for all events with:
            code == code
            time in time_range (exclusive)
        """
        events = []
        for file_position in self.event_index[code]:
            self.file.seek(file_position)
            event = self.next_event()
            if (event.time > time_range[0]) and \
                    (event.time < time_range[1]):
                events.append(event)
        return sorted(events, key=lambda e: e.time)

    def ievents(self, name, time_range=[-1, numpy.inf]):
        code = self.to_code(name)
        for file_position in self.event_index[code]:
            self.file.seek(file_position)
            event = self.next_event()
            if (event.time > time_range[0]) and \
                    (event.time < time_range[1]):
                        yield event


def to_array(events, value_type=None):
    """
    Convert a list of pymworks events to a numpy array with fields:
        'code' : type = 'u2'
        'time' : type = 'u8'
        'value': type = value_type or type(events[0].value) or 'u1'
    """
    if value_type is None:
        vtype = type(events[0].value) if len(events) else 'u1'
    else:
        vtype = value_type
    return numpy.array(map(tuple, events), dtype=[('code', 'u2'), \
            ('time', 'u8'), ('value', vtype)])


def open_file(filename, indexed=True):
    if indexed:
        return IndexedDataFile(filename)
    else:
        return DataFile(filename)
