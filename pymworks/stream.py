#!/usr/bin/env python

import socket

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
        """
            shared_ptr<NetworkReturn> rc;
            if(prepareForConnecting() < 0) {
                rc = shared_ptr<NetworkReturn>(new NetworkReturn());
                rc->setMWorksCode(NR_FAILED);
                rc->setInformation("Host or Reader or Writer is NULL");
                return rc;
            }
            rc = reader->connect();
            if(!rc->wasSuccessful()) {
                mnetwork("mScarabClient::connect() failed on read connection");
                return rc;
            }
            shared_ptr<NetworkReturn> writeRc;
            writeRc = writer->connect();
            rc->appendInformation(writeRc->getInformation());
            if(!writeRc->wasSuccessful()) {
                    mnetwork("mScarabClient::connect() failed
                    on write connection");
                    mnetwork("Closing read connection");
                    reader->disconnect();
                    return rc;
            }
            mnetwork("Incoming network session connected");
            outgoing_event_buffer->putEvent(
                SystemEventFactory::clientConnectedToServerResponse());
            return rc;
        """
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
