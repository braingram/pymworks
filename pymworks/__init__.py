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

    def restart(self):
        """ Restart reading the file from the beginning """
        self.file.seek(0)
        self.ldo.read_stream_header = 0
        self.ldo.um_init()
        #del self.ldo
        #self.ldo = LDOBinary.LDOBinaryUnmarshaler(self.file)

    def get_next_event(self):
        """ Get the next event in the file"""
        try:
            return Event(self.ldo.load())
        except EOFError:
            return None

    def lookup_event_code(self, name):
        """ Lookup code for an event name """
        # search dictionary by values
        try:
            return [k for k, v in self.get_codec().iteritems() if v == name][0]
        except IndexError:
            raise ValueError("Event[%s] not found in codec" % name)

    def lookup_event_name(self, code):
        """ Lookup name for a event code """
        return self.get_codec()[code]

    def get_events_by_code(self, code, time_range=[-1, numpy.inf]):
        """
        Search the file for all events with:
            code == code
            time in time_range (exclusive)
        """
        self.restart()
        event = self.get_next_event()
        events = []
        while not (event is None):
            if (event.code == code) and (event.time > time_range[0]) \
                    and (event.time < time_range[1]):
                events.append(event)
            event = self.get_next_event()
        return events

    def get_events_by_name(self, name, time_range=[-1, numpy.inf]):
        return self.get_events_by_code(\
                self.lookup_event_code(name), time_range)

    def find_codec(self):
        """ Search the file for the codec """
        codecs = self.get_events_by_code(0)  # codec code is 0
        if len(codecs) == 0:
            raise ValueError("Unable to find codec")
        elif len(codecs) > 1:
            #logging.warning("File contains more than one codec")
            for other_codec in codecs[1:]:
                if codecs[0][2] != other_codec[2]:
                    logging.error("File contains two codecs that differ")
                    raise Exception("File contains two codecs that differ")

        # parse codec event into codec
        # TODO: sort out what to do with multiple codecs
        raw_codec = codecs[-1][2]
        codec = {}
        for k, v in raw_codec.iteritems():
            codec[k] = v['tagname']

        # add missing items, codec[0], codec[1], codec[2]
        codec[0] = '#codec'
        codec[1] = '#systemEvent'
        codec[2] = '#components'
        codec[3] = '#termination'
        return codec

    def get_codec(self):
        """
        Return the files codec
        If not previously found this function will search for the codec
        """
        if self._codec is None:
            self._codec = self.find_codec()
        return self._codec

    codec = property(get_codec)

    def events(self, name, time_range=[-1, numpy.inf]):
        return self.get_events_by_name(name, time_range)

    def get_maximum_time(self):
        if self._maxtime is None:
            self._maxtime = self.find_maximum_time()
        return self._maxtime

    def get_minimum_time(self):
        if self._mintime is None:
            self._mintime = self.find_minimum_time()
        return self._mintime

    def find_minimum_time(self):
        self.restart()
        event = self.get_next_event()
        if event is None:
            raise ValueError('File[%s] contains no events' % self.filename)
        return event.time

    def find_maximum_time(self):
        self.restart()
        maxtime = None
        event = self.get_next_event()
        while event is not None:
            maxtime = event.time
            event = self.get_next_event()
        if maxtime is None:
            raise ValueError('File[%s] contains no events' % self.filename)
        return maxtime

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
        event = self.get_next_event()
        while not (event is None):
            # record file position of event
            self.event_index[event.code].append(position)
            # get next event
            position = self.file.tell()
            event = self.get_next_event()

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
            event = self.get_next_event()
            if (event.time > time_range[0]) and \
                    (event.time < time_range[1]):
                events.append(event)
        return events

    def find_maximum_time(self):
        max_position = max([max(p) for p in self.event_index.values()])
        self.file.seek(max_position)
        return self.get_next_event().time


def events_to_code_time_values(events):
    """
    Returns three tuples: codes, times, values
    """
    raise Exception("Doesn't work")
    return zip(*events)


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
