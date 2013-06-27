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
- connect/disconnect/reconnect
"""


class IODevice(object):
    def __init__(self, autoconnect=True):
        self._connected = False
        if autoconnect:
            self.connect()

    def connect(self):
        self._connected = True

    def disconnect(self):
        self._connected = False

    def reconnect(self):
        self.disconnect()
        self.connect()

    def require_connected(self):
        if not self._connected:
            raise IOError("update called on unconnected source")


class Source(IODevice):
    def __init__(self, autoconnect=True):
        IODevice.__init__(self, autoconnect=False)
        self._codec = None
        self._rcodec = None
        self._mintime = None
        self._maxtime = None
        self._callbacks = []
        self.variables = []
        self.variable_groups = {}
        self.register_callback(0, self.process_codec_event)
        if autoconnect:
            self.connect()
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
        self._codec = dict(
            [(k, v['tagname']) for k, v in
             event.value.iteritems()] +
            [(0, '#codec'), (1, '#systemEvent'),
             (2, '#components'), (3, '#termination')])
        self.variables = event.value
        self.variable_groups = {}
        for (_, v) in self.variables.iteritems():
            for vg in v['groups']:
                self.variable_groups[vg] = \
                    self.variable_groups.get(vg, []) + [v['tagname'], ]

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

    def __iter__(self):
        e = self.read_event()
        while e is not None:
            yield e
            e = self.read_event()

    def get_minimum_time(self):
        if self._mintime is None:
            self._find_time_range()
        return self._mintime

    def get_maximum_time(self):
        if self._maxtime is None:
            self._find_time_range()
        return self._maxtime

    # ------ callback ------
    def register_callback(self, key, func):
        if isinstance(key, (str, unicode)):
            if key not in self.codec.values():
                raise ValueError("String type key[%s] not in codec[%s]"
                                 % (key, self.codec))
            key = self.to_code(key)
        #if key in self._callbacks:
        #    raise ValueError("Only one callback[%s] is allowed per key[%s]" \
        #            % (self._callbacks[key], key))
        cid = len(self._callbacks)
        self._callbacks.append((key, func))
        return cid
        #self._callbacks[key] = func

    def remove_callback(self, cid):
        if (cid < 0) or (cid >= len(self._callbacks)):
            raise ValueError("Invalid callback id %s, must be >=0 and <%s" %
                             (cid, len(self._callbacks)))
        del self._callbacks[cid]

    def process_event(self, event):
        for (k, cb) in self._callbacks:
            if (event.code == k) or (k == -1):
                cb(event)
        #if event.code in self._callbacks:
        #    self._callbacks[event.code](event)
        self._mintime = event.time if self._mintime is None \
            else min(event.time, self._mintime)
        self._maxtime = max(event.time, self._maxtime)

    def update(self, n=100, **kwargs):
        self.require_connected()
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
    def __init__(self, autoconnect=True):
        IODevice.__init__(self, autoconnect=False)
        if autoconnect:
            self.connect()

    def write_event(self, event):
        self.require_connected()


class Stream(Source, Sink):
    def __init__(self, autoconnect=True):
        Source.__init__(self, autoconnect=False)
        Sink.__init__(self, autoconnect=False)
        if autoconnect:
            self.connect()
