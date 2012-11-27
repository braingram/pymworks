#!/usr/bin/env python
"""
See core/Core/Events/EventConstants.h in mworks repo for event info
"""

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


SystemEventType = {'control': 1000, 'data': 1001, 'response': 1002}
SystemPayloadType = {
        'experiment': 2000,
        'protocol': 2001,
        'datafile': 2004,

        # control events (no payload except protocol_selection)
        'protocol_selection': 3001,
        'start_experiment': 3002,
        'stop_experiment': 3003,
        'pause_experiment': 3004,
        'open_datafile': 3005,
        'close_datafile': 3006,
        'close_experiment': 3007,
        'save_variables': 3008,
        'load_variables': 3009,
        'request_codec': 3010,
        'set_event_forwarding': 3011,
        'request_variables': 3012,

        # response messages
        'datafile_opened': 4007,
        'datafile_closed': 4008,
        'client_connected': 4009,
        'client_disconnected': 4010,
        'server_connected': 4011,
        'server_disconnected': 4012,
        'experiment_state': 4013,

        # payload contains anything
        'user_defined': 6000,
        }

SystemResponseCode = {'success': 5001, 'failure': 5002}
