#!/usr/bin/env python

hasnumpy = False
try:
    import numpy
    hasnumpy = True
except ImportError:
    hasnumpy = False


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
