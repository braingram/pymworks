#!/usr/bin/env python
"""
JS <-> Python protocol is:
    READ/WRITE (host, name, time) : read/write a variable
    LISTEN (host, name) : listen for events of name
    STATE (host) : get current known state of all variables
    CONNECT/DISCONNECT (host)

-- datafile api --
to_code(name) : requires codec
to_name(code) : requires codec
next_event : requires nothing
get_all_events/all_events : requires event buffer
get_events/events(key=None, time_range=None) : requires codec & event buffer
get_codec/codec : requires codec
get_reverse_codec/rcodec : requires codec
get_maximum_time : requires event buffer
get_minimum_time : requires event buffer

they differ in the access mode:
    1) stream = sequential('ish') access
    2) file = indexed access
    3) database = search access (same as indexed)

Sink
- write_event
- start/stop/restart
"""


class IODevice(object):
    def __init__(self, autostart=True):
        self._running = False
        if autostart:
            self.start()

    def start(self):
        self._running = True

    def stop(self):
        self._running = False

    def restart(self):
        self.stop()
        self.start()

    def require_running(self):
        if not self._running:
            raise IOError("update called on stopped source")


class Source(IODevice):
    def __init__(self, autostart=True):
        IODevice.__init__(self, autostart=False)
        self._codec = None
        self._rcodec = None
        self._mintime = None
        self._maxtime = None
        self._callbacks = {}
        self.register_callback(0, self.process_codec_event)
        if autostart:
            self.start()
        # for backwards compatibility
        self.next_event = self.read_event

    # ------ codec ------
    def to_code(self, name):
        try:
            return self.rcodec[name]
        except KeyError:
            raise KeyError("Event Name[%s] not found in codec" % name)

    def to_name(self, code):
        try:
            return self.codec[code]
        except KeyError:
            raise KeyError("Event Code[%i] not found in codec" % code)

    def get_codec(self):
        if self._codec is None:
            self.find_codec()
        return self._codec

    def get_reverse_codec(self):
        if self._rcodec is None:
            self._rcodec = dict([(v, k) for k, v in self.codec.iteritems()])
        return self._rcodec

    def process_codec_event(self, event):
        self._codec = dict([(k, v['tagname']) for k, v in \
                event.value.iteritems()] + \
                [(0, '#codec'), (1, '#systemEvent'), \
                (2, '#components'), (3, '#termination')])

    def find_codec(self, **kwargs):
        if self._codec is None:
            self.update(**kwargs)
        if self._codec is None:
            raise LookupError("Failed to find codec")

    # ------ events ------
    def read_event(self):
        pass

    def get_events(self, key=None, time_range=None):
        pass

    def get_minimum_time(self):
        return self._mintime

    def get_maximum_time(self):
        return self._maxtime

    # ------ callback ------
    def register_callback(self, key, func):
        if isinstance(key, str):
            if key not in self.codec.values():
                raise ValueError("String type key[%s] not in codec[%s]" \
                        % (key, self.codec))
            key = self.to_code(key)
        self._callbacks[key] = func

    def process_event(self, event):
        if event.code in self._callbacks:
            self._callbacks[event.code](event)
        self._mintime = event.time if self._mintime is None \
                else min(event.time, self._mintime)
        self._maxtime = max(event.time, self._maxtime)

    def update(self, n=100, **kwargs):
        self.require_running()
        for i in xrange(n):
            e = self.read_event(**kwargs)
            if e is None:
                return
            self.process_event(e)

    minimum_time = property(get_minimum_time)
    maximum_time = property(get_maximum_time)
    codec = property(get_codec)
    rcodec = property(get_reverse_codec)


class Sink(IODevice):
    def __init__(self, autostart=True):
        IODevice.__init__(self, autostart=False)
        if autostart:
            self.start()

    def write_event(self):
        self.require_running()
