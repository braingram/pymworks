#!/usr/bin/env python

import logging

import LDOBinary

class DataFile:
    def __init__(self, filename):
        self.filename = filename
        self.file = open(self.filename, 'rb')
        self.ldo = LDOBinary.LDOBinaryUnmarshaler(self.file)
        self.codec = None

    def restart(self):
        """ Restart reading the file from the beginning """
        self.file.seek(0)
        del self.ldo
        self.ldo = LDOBinary.LDOBinaryUnmarshaler(self.file)

    def get_next_event(self):
        """ Get the next event in the file"""
        try:
            return self.ldo.load()
        except EOFError as E:
            return None
    
    def find_events_by_code(self, code):
        """ Search the file for all events with code == code """
        self.restart()
        event = self.get_next_event()
        events = []
        while not (event is None):
            if event[0] == code:
                events.append(event)
            event = self.get_next_event()
        return events

    def find_events_by_name(self, name):
        codec = self.get_codec()
        code = [k for k, v in codec.iteritems() if v == name][0] # search dictionary by values
        return self.find_events_by_code(code)

    def find_codec(self):
        """ Search the file for the codec """
        codecs = self.find_events_by_code(0) # codec code is 0
        if len(codecs) == 0:
            raise ValueError("Unable to find codec")
        elif len(codecs) > 1:
            logging.warning("File contains more than one codec")

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
