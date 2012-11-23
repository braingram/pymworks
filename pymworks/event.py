#!/usr/bin/env python

import collections
import time as pytime


class Event(collections.Mapping):
    def __init__(self, code, time, value, name=None):
        collections.Mapping.__init__(self)
        self.code = code
        self.time = time
        self.value = value
        self.name = name

    def __getitem__(self, key):
        if key not in ('code', 'name', 'time', 'value'):
            raise KeyError("%r not found" % repr(key))
        return getattr(self, key)

    def __iter__(self):
        yield 'code'
        yield 'name'
        yield 'time'
        yield 'value'

    def __len__(self):
        return 3

    def __repr__(self):
        return "%s[code=%r, name=%s, time=%r, value=%r]" % \
                (self.__class__.__name__, self.code, self.name, \
                self.time, self.value)


def fake_codec_event(codec=None, time=None):
    dcodec = { \
            0: '#codec',
            1: '#systemEvent',
            2: '#components',
            3: '#termination',
            }
    if codec is not None:
        dcodec.update(codec)
    for k in dcodec:
        dcodec[k] = dict(tagname=dcodec[k])
    time = int(pytime.time() * 1E6) if time is None else time
    return Event(0, time, dcodec)
