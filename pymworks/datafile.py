#!/usr/bin/env python

import collections
import logging
import os
#import pickle
import cPickle as pickle

import LDOBinary

import numpy


Event = collections.namedtuple('Event', 'code time value')


class DataFile:
    """
    Pure python, non-indexed data file reader

    To use:
        f = DataFile(filename)
        events = f.events('foo')
        events[0].time
    """
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
            return Event(*self.ldo.load())
        except EOFError:
            return None
        except TypeError:
            logging.warning("Event before %i was missing required code, "
                "time, and/or value" % self.file.tell())
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
        elif isinstance(key, (int, numpy.integer, numpy.long)):
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

    def get_time_filtered_events(self, time_range):
        return filter(self.time_range_to_test(time_range), self.all_events)

    def get_key_filtered_events(self, key):
        return filter(self.key_to_test(key), self.all_events)

    def get_key_and_time_filtered_events(self, key, time_range):
        kt = self.key_to_test(key)
        tt = self.time_range_to_test(time_range)
        return filter(lambda e: (kt(e) and tt(e)), self.all_events)

    def get_events(self, key=None, time_range=None):
        """
        Get all events where:
            key_to_test(key)(event) == True
            and
            time_range_to_test(time_range)(event) == True

        key can any of these types:
            int, numpy.integer
            str, numpy.str
            list, tuple, ndarray of str or int or mix of str & int

        time_range (2 length tuple/list/ndarray) of times
        """
        if key is None:
            if time_range is None:
                events = self.all_events
            else:
                events = self.get_time_filtered_events(time_range)
        else:  # key is not None
            if time_range is None:
                events = self.get_key_filtered_events(key)
            else:
                events = self.get_key_and_time_filtered_events(key, time_range)
        return sorted(events, key=lambda e: e.time)

    def events(self, *args, **kwargs):
        """
        shortcut to get_events
        """
        return self.get_events(*args, **kwargs)

    # ------  codec handling ------
    def find_codec(self):
        """
        Search the file for the codec.
        Codec is a dictionary with:
            key : event code [int]
            val : event name [str]
        """
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
        Return the codec
        If not previously found this function will call find_codec
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
        """
        Return a reversed codec where:
            key : event name [str]
            val : event code [int]
        """
        return dict([(v, k) for k, v in self.codec.iteritems()])

    rcodec = property(get_reverse_codec)

    # ------  time handling ------
    def get_maximum_time(self):
        """
        Return the (potentially cached) maximum event time
        """
        if self._maxtime is None:
            self._mintime, self._maxtime = self.find_time_range()
        return self._maxtime

    def get_minimum_time(self):
        """
        Return the (potentially cached) minimum event time
        """
        if self._mintime is None:
            self._mintime, self._maxtime = self.find_time_range()
        return self._mintime

    def find_time_range(self):
        """
        Find minimum and maximum event times

        Returns
        -------
            min_time, max_time
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
                    self._index = pickle.load(index_file)
                    if type(self._index) != dict:
                        wrong_type = type(self._index)
                        raise TypeError("loaded index(%s) was "
                                "wrong type: %s" % \
                                        (index_filename, str(wrong_type)))
                    self.parse_index()
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
        self._index = collections.defaultdict(list)
        # need to do this manually (rather than calling all_events)
        # to keep track of the file position
        self.restart()
        position = self.file.tell()
        event = self.next_event()
        while event is not None:
            self._index[event.code].append(position)
            position = self.file.tell()
            event = self.next_event()

        self._index = dict(self._index)
        for code in self.codec.keys():
            if code not in self._index:
                self._index[code] = []

        # get codec and time ranges
        self._index.update({'_codec': self.codec, \
                '_mintime': self.minimum_time, '_maxtime': self.maximum_time})

        self.parse_index()

        # save index to file
        with open(index_filename, 'wb') as index_file:
            pickle.dump(self._index, index_file, 2)

    def parse_index(self):
        self._codec = self._index['_codec']
        self._mintime = self._index['_mintime']
        self._maxtime = self._index['_maxtime']

    def event_at(self, position):
        """
        Return an event at a file position
        """
        self.file.seek(position)
        return self.next_event()

    # overload event fetching to use index
    def get_key_filtered_events(self, key):
        if isinstance(key, str):
            codes = [self.to_code(key)]
        elif isinstance(key, (int, numpy.integer, numpy.long)):
            codes = [key]
        elif isinstance(key, (tuple, list, numpy.ndarray)):
            codes = map(lambda k: self.to_code(k) if isinstance(k, str) \
                    else k, key)
        else:
            raise ValueError('Invalid key: %s' % key)
        return reduce(lambda x, y: x + y, [\
                [self.event_at(p) for p in self._index[code]] \
                for code in codes])

    def get_key_and_time_filtered_events(self, key, time_range):
        tt = self.time_range_to_test(time_range)
        return [e for e in self.get_key_filtered_events(key) if tt(e)]


class DataFileWriter(object):
    def __init__(self, filename):
        self.file = open(filename, 'w')
        self.ldo = LDOBinary.LDOBinaryMarshaler(self.file)
        self.ldo.m_init()

    def write_event(self, event):
        self.ldo._marshal(list(event))

    def close(self):
        del self.ldo
        self.file.close()


def unpack_events(events):
    """
    Unpack events into three tuples (codes, times, values)

    Returns:
        codes, times, values
    """
    return zip(*map(tuple, events))


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
