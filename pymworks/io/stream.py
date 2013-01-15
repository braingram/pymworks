#!/usr/bin/env python

import collections
import logging
import getpass
import select
import socket
import subprocess
import sys
import time as pytime

from base import Stream
from datafile import key_to_code, make_tests
from ..events.event import Event
from ..events import system
from raw import LDOBinary

defaultport = 19989


class EventStream(Stream):
    def __init__(self, host, port=defaultport, autostart=True, timeout=None):
        Stream.__init__(self, autostart=False)
        self.host = host
        self.port = port
        self.timeout = timeout
        self.safe = True
        if autostart:
            self.start()

    def start(self):
        if self._running:
            return
        try:
            self.rsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            #self.rsocket.settimeout(self.timeout)
            self.rsocket.connect((self.host, self.port))
        except socket.error as E:
            logging.error("StreamReader.start failed with: %s" % E)
            if hasattr(self, 'rsocket'):
                del self.rsocket
            return
        try:
            self.wsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            #self.wsocket.settimeout(self.timeout)
            self.wsocket.connect((self.host, self.port))
        except socket.error as E:
            logging.error("StreamReader.start failed with: %s" % E)
            if hasattr(self, 'wsocket'):
                del self.wsocket
            self.rsocket.shutdown(socket.SHUT_RD)
            self.rsocket.close()
            del self.rsocket
            return
        self.rldo = LDOBinary.LDOBinaryUnmarshaler( \
                self.rsocket.makefile('rb', 0))
        self.rldo.um_init()
        logging.debug("Client: built unmarshaler %s" % self.rldo)
        self.wldo = LDOBinary.LDOBinaryMarshaler( \
                self.wsocket.makefile('wb', 0))
        self.wldo.written_stream_header = 1  # don't write the stream header
        self.wldo.m_init()
        logging.debug("Client: built marshaler %s" % self.wldo)
        Stream.start(self)

    def stop(self):
        if not self._running:
            return
        if hasattr(self, 'rsocket'):
            self.rsocket.shutdown(socket.SHUT_RD)
            self.rsocket.close()
            del self.rsocket
        if hasattr(self, 'wsocket'):
            self.wsocket.shutdown(socket.SHUT_WR)
            self.wsocket.close()
            del self.wsocket
        Stream.stop(self)

    def read_event(self, safe=None):
        safe = self.safe if safe is None else safe
        self.require_running()
        if safe is False:
            e = Event(*self.rldo.load())
            if (self._codec is not None) and (e.code in self._codec):
                e.name = self._codec[e.code]
            return e
        r, _, _ = select.select([self.rsocket], [], [], self.timeout)
        if len(r):
            return self.read_event(safe=False)
        else:
            return None

    # overload methods that will not work (get_events...)
    def get_events(self, **kwargs):
        raise NotImplementedError("StreamReader.get_events not possible, "
                "use BufferedStreamReader")

    def write_event(self, event, flush=True):
        self.require_running()
        self.wldo.dump([event.code, event.time, event.value])
        if flush:
            self.wldo.flush()

    def update(self, n=100, **kwargs):
        try:
            Stream.update(self, n, **kwargs)
        except socket.timeout:
            logging.debug("Update timed out")
            return


class Server(Stream):
    def __init__(self, host, port=defaultport, autostart=True, timeout=None):
        Stream.__init__(self, autostart=False)
        self.host = host
        self.port = port
        self.timeout = timeout
        self.safe = True
        if autostart:
            self.start()

    def start(self):
        if self._running:
            return
        logging.debug("Server: listening for client write connnection")
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            #self.socket.settimeout(self.timeout)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind((self.host, self.port))
            self.socket.listen(1)
            self.wconn, self.waddr = self.socket.accept()
            #self.wconn.settimeout(self.timeout)
        except socket.error as E:
            logging.error("Server.start failed with: %s" % E)
            del self.socket
            return

        logging.debug("Server: building marshaler")
        self.wldo = LDOBinary.LDOBinaryMarshaler( \
                self.wconn.makefile('wb', 0))
        logging.debug("Server: init marshaler %s" % self.wldo)
        self.wldo.m_init()
        logging.debug("Server: flushing")
        self.wldo.flush()
        logging.debug("Server: built marshaler: %s" % self.wldo)

        logging.debug("Server: listening for client read connnection")
        try:
            self.rconn, self.raddr = self.socket.accept()
            #self.rconn.settimeout(self.timeout)
        except socket.error as E:
            self.wconn.close()
            del self.wconn, self.waddr, self.socket, self.wldo
            return

        logging.debug("Server: building unmarshaler")
        # strangly, the native server writes a stream header here
        self.rconn.sendall(LDOBinary.MAGIC + LDOBinary.VERSION + \
                chr(LDOBinary.MAJOR) + chr(LDOBinary.MINOR))
        self.rldo = LDOBinary.LDOBinaryUnmarshaler( \
                self.rconn.makefile('rb', 0))
        logging.debug("Server: built unmarshaler: %s" % self.rldo)
        self.rldo.read_stream_header = 1  # don't read the stream header
        self.rldo.um_init()
        Stream.start(self)

    def stop(self):
        if not self._running:
            return
        if hasattr(self, 'rconn'):
            self.rconn.shutdown(socket.SHUT_RD)
            self.rconn.close()
            del self.rconn
        if hasattr(self, 'wconn'):
            self.wconn.shutdown(socket.SHUT_RD)
            self.wconn.close()
            del self.wconn
        if hasattr(self, 'socket'):
            self.socket.shutdown(socket.SHUT_RD)
            self.socket.close()
            del self.socket
        Stream.stop(self)

    def read_event(self, safe=None):
        safe = self.safe if safe is None else safe
        self.require_running()
        if safe is False:
            e = Event(*self.rldo.load())
            if (self._codec is not None) and (e.code in self._codec):
                e.name = self._codec[e.code]
            logging.debug(e)
            return e
        r, _, _ = select.select([self.rconn], [], [], self.timeout)
        if len(r):
            return self.read_event(safe=False)
        else:
            return None

    # overload methods that will not work (get_events...)
    def get_events(self, **kwargs):
        raise NotImplementedError("Server.get_events not possible")

    def write_event(self, event, flush=True):
        self.require_running()
        self.wldo.dump([event.code, event.time, event.value])
        if flush:
            self.wldo.flush()

    def update(self, n=100, **kwargs):
        try:
            Stream.update(self, n, **kwargs)
        except socket.timeout:
            logging.debug("Update timed out")
            return


class BufferedEventStream(EventStream):
    def __init__(self, host, port=defaultport, autostart=True, timeout=None, \
            bufferlength=1):
        EventStream.__init__(self, host, port=port, \
                autostart=False, timeout=timeout)
        self.bufferlength = bufferlength
        self.eventbuffer = collections.defaultdict(list)
        if autostart:
            self.start()

    def read_event(self, safe=None):
        e = EventStream.read_event(self, safe=safe)
        if e is None:
            return e
        b = self.eventbuffer[e.code]
        b.append(e)
        self.eventbuffer[e.code] = b[-self.bufferlength:]
        return e

    def find_codec(self, **kwargs):
        if self._codec is None:
            if 0 in self.eventbuffer.keys():
                self.process_codec_event(self.eventbuffer[0][-1])
        if self._codec is None:
            raise LookupError("Failed to find codec")

    def get_codec(self):
        if self._codec is None:
            self.find_codec()
        else:
            if len(self._codec) != len(self.eventbuffer[0][-1].value):
                self.process_codec_event(self.eventbuffer[0][-1])
        return self._codec

    def get_events(self, key=None, time_range=None):
        kt, tt = make_tests(key, time_range, self.to_code)
        if key is None:
            codes = self.eventbuffer.keys()
        else:
            codes = key_to_code(key, self.to_code)
            if not isinstance(codes, (tuple, list)):
                codes = [codes, ]
        events = []
        for code in codes:
            for e in self.eventbuffer[code]:
                if tt(e):
                    events.append(e)
        return events


class Client(BufferedEventStream):
    def __init__(self, host, port=defaultport, autostart=True, timeout=None, \
            bufferlength=1):
        BufferedEventStream.__init__(self, host, port=port, autostart=False, \
                bufferlength=bufferlength, timeout=timeout)
        self.tdelay = 0
        self.state = {}
        self.register_callback(1, self.update_state)
        if autostart:
            self.start()

    def now(self):
        return int(pytime.time() * 1E6 + self.tdelay)

    def make_event(self, key, time, value):
        if isinstance(key, str):
            key = self.to_code(key)
        time = self.now() if time is None else time
        return Event(key, time, value, name=self.to_name(key))

    # experiment : load(fn), start, stop, pause
    def load_experiment(self, filename):
        self.write_event(system.load_experiment(filename))

    def start_experiment(self):
        self.write_event(system.start_experiment())

    def stop_experiment(self):
        self.write_event(system.stop_experiment())

    def pause_experiment(self):
        self.write_event(system.pause_experiment())

    # datafile : open(fn, overwrite=False), close(fn)
    def open_datafile(self, filename, overwrite=False):
        self.write_event(system.open_datafile(filename, overwrite))

    def close_datafile(self):
        self.write_event(system.close_datafile())

    # variables : save(fn, overwrite=False), load(fn)
    def load_variables(self, filename):
        self.write_event(system.load_variables(filename))

    def save_variables(self, filename, overwrite=False):
        self.write_event(system.save_variables(filename, overwrite))

    # protocol : select_protocol
    def select_protocol(self, protocol):
        self.write_event(system.protocol_selection(protocol))

    # ... : request_codec, request_variables
    def update_state(self, event):
        try:
            self.state = system.parse_state(event, self.state)
        except Exception as E:
            system.parse_warning('Failed to parse event with %s' % E, event)

    def start_server(self):
        if self.host in ('127.0.0.1', 'localhost'):
            cmd = '/usr/bin/open /Applications/MWServer.app'
        else:
            # -f puts ssh in background
            # BatchMode=yes disable password prompt
            cmd = 'ssh -f -o BatchMode=yes -l %s %s /usr/bin/open ' \
                    '/Applications/MWServer.app' % \
                    (getpass.getuser(), self.host)
        logging.debug("Launching: %s" % cmd)
        if logging.root.level <= logging.DEBUG:
            kwargs = dict(stderr=sys.stderr, stdout=sys.stdout)
        else:
            kwargs = {}
        ret = subprocess.call(cmd.split(), **kwargs)
        if ret != 0:
            logging.warning("Failed to start server, return code: %s" % ret)
            return False
        return True
