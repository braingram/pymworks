#!/usr/bin/env python

import collections
import logging
import os
import pickle

import LDOBinary

class DataFile:
    def __init__(self, filename):
        self.filename = filename
        self.file = open(self.filename, 'rb')
        self.ldo = LDOBinary.LDOBinaryUnmarshaler(self.file)
        self.restart() # call this to properly run um_init
        self.codec = None

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
            return self.ldo.load()
        except EOFError as E:
            return None
    
    def lookup_event_code(self, name):
        """ Lookup code for an event name """
        # search dictionary by values
        return [k for k, v in self.get_codec().iteritems() if v == name][0]

    def lookup_event_name(self, code):
        """ Lookup name for a event code """
        return self.get_codec()[code]

    def get_events_by_code(self, code):
        """ Search the file for all events with code == code """
        self.restart()
        event = self.get_next_event()
        events = []
        while not (event is None):
            if event[0] == code:
                events.append(event)
            event = self.get_next_event()
        return events

    def get_events_by_name(self, name):
        return self.get_events_by_code(self.lookup_event_code(name))

    def find_codec(self):
        """ Search the file for the codec """
        codecs = self.get_events_by_code(0) # codec code is 0
        if len(codecs) == 0:
            raise ValueError("Unable to find codec")
        elif len(codecs) > 1:
            logging.warning("File contains more than one codec")
            for other_codec in codecs[1:]:
                if codecs[0][2] != other_codec[2]:
                    logging.warning("codecs differed")

        # parse codec event into codec
        raw_codec = codecs[-1][2] # TODO: sort out what to do with multiple codecs
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
        if self.codec is None:
            self.codec = self.find_codec()
        return self.codec

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
        index_filename = '%s/.%s.index' % os.path.split(os.path.realpath(self.filename))
        if os.path.exists(index_filename):
            try:
                with open(index_filename, 'rb') as index_file:
                    self.event_index = pickle.load(index_file)
                    if type(self.event_index) != collections.defaultdict:
                        wrong_type = type(self.event_index)
                        raise TypeError("loaded event_index(%s) was wrong type: %s" % \
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
            self.event_index[event[0]].append(position)
            # get next event
            position = self.file.tell()
            event = self.get_next_event()

        # save index to file
        with open(index_filename, 'wb') as index_file:
            pickle.dump(self.event_index, index_file, 2)

    # overload event fetching to use index
    def get_events_by_code(self, code):
        """ Search the file for all events with code == code """
        events = []
        for file_position in self.event_index[code]:
            self.file.seek(file_position)
            events.append(self.get_next_event())
        return events

