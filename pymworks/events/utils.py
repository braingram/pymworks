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
    return numpy.array(
        map(lambda e: (e.code, e.time, e.value), events),
        dtype=[('code', 'u2'), ('time', 'u8'), ('value', vtype)])


def fake_codec_event(codec=None, time=None):
    dcodec = {
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
        match = None
        mt = mkey(m)
        for s in sslaves:
            if end(skey(s), mt):
                break
            if ttest(skey(s), mt):
                match = s
        matches.append(match)
    while len(matches) < len(master):
        matches.append(None)
    return matches


def test_sync():
    s = [5, 15, 17, 25]
    m = [0, 10, 20, 30]
    ks = (lambda s: s, lambda m: m)

    t = sync(s, m, 1, *ks)
    assert t == [5, 15, 25, None]

    t = sync(s, m, -1, *ks)
    assert t == [None, 5, 17, 25]

    t = sync(s, m, 0, *ks)
    assert t == [None, None, None, None]

    s = [0, 11, 20, 31]
    t = sync(s, m, 0, *ks)
    assert t == [0, None, 20, None]
