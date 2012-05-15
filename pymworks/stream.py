#!/usr/bin/env python

import socket

import LDOBinary
from datafile import Event


class TCPReader:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.ldo = None
        self.connect()

    def connect(self):
        self.socket.connect((self.host, self.port))
        self.ldo = LDOBinary.LDOBinaryUnmarshaler(self.socket.makefile('rb'))
        #self.ldo.um_init()

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
        #self.ldo.m_init()

    def write_event(self, event):
        self.ldo._marshal(list(event))
        self.ldo.flush()


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

        # write client connected to server response
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
