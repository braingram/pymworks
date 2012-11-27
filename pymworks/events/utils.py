#!/usr/bin/env python

import time

from event import Event

hasnumpy = False
try:
    import numpy
    hasnumpy = True
except ImportError:
    hasnumpy = False


def now():
    return int(time.time() * 1E6)


def unpack_events(events):
    """
    Unpack events into three tuples (codes, times, values)

    Returns:
        codes, times, values
    """
    return zip(*map(lambda e: (e.code, e.time, e.value), events))
    #return zip(*map(tuple, events))


def to_array(events, value_type=None):
    """
    Convert a list of pymworks events to a numpy array with fields:
        'code' : type = 'u2'
        'time' : type = 'u8'
        'value': type = value_type or type(events[0].value) or 'u1'
    """
    assert hasnumpy, "failed to import numpy"
    if value_type is None:
        vtype = type(events[0].value) if len(events) else 'u1'
    else:
        vtype = value_type
    return numpy.array(map(lambda e: (e.code, e.time, e.value), events), \
            dtype=[('code', 'u2'), \
            ('time', 'u8'), ('value', vtype)])


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
    time = now() if time is None else time
    return Event(0, time, dcodec)
