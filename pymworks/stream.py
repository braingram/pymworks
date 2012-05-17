#!/usr/bin/env python

import select
import socket

import LDOBinary
from datafile import Event


class TCPReader(object):
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

    def try_read(self, timeout=1.0):
        r, _, _ = select.select([self.socket], [], [], timeout)
        if len(r):
            return self.read()
        else:
            return None


class FakeReader(object):
    def __init__(self, host, port):
        self.host = host
        self.port = port

    def read(self):
        return None

    def try_read(self):
        return None


class TCPWriter(object):
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


class FakeWriter(object):
    def __init__(self, host, port):
        self.host = host
        self.port = port

    def write_event(self, event):
        pass


class Client(object):
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
        self.writer.write_event(list(event))

    #def read_initial_events(self):
    #    event = self.reader.try_read()
    #    while event is not None:
    #        event = self.reader.try_read()


class CodecClient(Client):
    def __init__(self, **kwargs):
        Client.__init__(self, **kwargs)
        self.codec = {}
        self.find_codec()

    def find_codec(self, max_n=100, timeout=1.0):
        event = self.reader.try_read(timeout)
        n = 0
        while (event is not None) and (n < max_n):
            n += 1
            if event.code == 0:
                self.process_codec_event(event)
                break
            event = self.reader.try_read(timeout)

    def process_codec_event(self, event):
        self.codec = dict([(k, v['tagname']) for k, v in \
                event.value.iteritems()] + \
                [(0, '#codec'), (1, '#systemEvent'), \
                (2, '#components'), (3, '#termination')])

    def get_reverse_codec(self):
        return dict([(v, k) for k, v in self.codec.iteritems()])

    rcodec = property(get_reverse_codec)


class CallbackCodecClient(CodecClient):
    def __init__(self, callbacks=None, **kwargs):
        if callbacks is None:
            self.callbacks = {}
        self.callbacks[0] = self.process_codec_event
        CodecClient.__init__(self, **kwargs)

    def update(self, max_n=100, timeout=1.0):
        event = self.reader.try_read(timeout)
        n = 0
        while (event is not None) and (n < max_n):
            n += 1
            self.process_event(event)
            event = self.reader.try_read(timeout)

    def process_event(self, event):
        if event.code in self.callbacks:
            self.callbacks[event.code](event)

    def register_callback(self, key, func):
        if isinstance(key, str):
            if key not in self.codec.values():
                raise ValueError("String type key[%s] not in codec[%s]" \
                        % (key, self.codec))
            key = self.rcodec[key]
        self.callbacks[key] = func


class FakeClient(object):
    def __init__(self, **kwargs):
        self.codec = {}
        self.rcodec = {}
        self.callbacks = {}
        self.host = kwargs.get('host', 'fake')
        self.port = kwargs.get('port', 19989)
        self.reader = FakeReader(self.host, self.port)
        self.writer = FakeWriter(self.host, self.port)

    def read(self):
        return None

    def write_event(self, event):
        pass

    def update(self, max_n=100, timeout=1.0):
        pass

    def register_callback(self, key, func):
        pass
