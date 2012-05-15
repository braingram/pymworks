#!/usr/bin/env python

import socket
import time

import LDOBinary
from datafile import Event

import numpy


class StreamReader:
    def __init__(self, stream):
        self.stream = stream
        self.ldo = LDOBinary.LDOBinaryUnmarshaler(self.stream)
        self.restart()
        self._codec = None
        self._maxtime = None
        self._mintime = None

    def restart(self):
        self.ldo.read_stream_header = 0
        self.ldo.um_init()

    def close(self):
        del self.ldo
        del self.stream

    def next_event(self):
        return Event(*self.ldo.load())


class TCPReader:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.ldo = None
        self.connect()
        #self.socket.connect((self.host, self.port))
        #self.socket.listen(1)

    def connect(self):
        self.socket.connect((self.host, self.port))
        self.ldo = LDOBinary.LDOBinaryUnmarshaler(self.socket.makefile('rb'))

    def read(self):
        return Event(*self.ldo.load())


class TCPWriter:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.ldo = None
        self.connect()

    def connect(self):
        self.socket.connect((self.host, self.port))
        self.ldo = LDOBinary.LDOBinaryMarshaler(self.socket.makefile('wb'))

    def write_event(self, event):
        self.ldo._marshal(list(event))


class Client:
    """
    Fake mworks client
    """
    def __init__(self, host='127.0.0.1', port=19989):
        """
        Look in mw_core/core/events/eventconstants.h for more info on
                system events
        """
        self.host = host
        self.port = port
        # must connect in this order
        self.reader = TCPReader(self.host, self.port)
        self.writer = TCPWriter(self.host, self.port)

        # wrie client connected to server response
        #self.write_event([1, int(time.time() * 1E6), \
        #        {'payload': {}, 'payload_type': 4009, \
        #        'event_type': 1002}])

    def read(self):
        return self.reader.read()

    def write_event(self, event):
        """
        at the moment this doesn't seem to work
        """
        self.writer.write_event(list(event))
