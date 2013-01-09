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


def sync(slave, master, direction=-1, skey=None, mkey=None):
    """
    Find closest matching slave event for each master event.

    direction : int, -1, 0 or 1
        if -1, slave events occur before master events
        if  1, slave events occur after master events
        if  0, slave and master events occur simultaneously
    """
    if skey is None:
        skey = lambda s: s.time
    if mkey is None:
        mkey = lambda m: m.time
    if not (direction in (-1, 0, 1)):
        raise ValueError("direction [%s] must be -1, 0, or 1" % direction)
    if direction is -1:
        end = lambda s, m: s > m  # stop when slave time > master
        ttest = lambda s, m: s < m
        sslaves = sorted(slave, key=skey)
    if direction is 1:
        end = lambda s, m: s < m  # stop when slave time < master
        ttest = lambda s, m: s > m
        sslaves = sorted(slave, key=skey, reverse=True)
    if direction is 0:
        end = lambda s, m: s > m
        ttest = lambda s, m: s == m
        sslaves = sorted(slave, key=skey)

    matches = []
    for m in master:
        last = None
        for s in sslaves:
            if end(skey(s), mkey(m)):
                if (last is not None) and ttest(skey(last), mkey(m)):
                    matches.append(last)
                else:
                    matches.append(None)
                break
            last = s
    while len(matches) < len(master):
        matches.append(None)
    return matches
