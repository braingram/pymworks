#!/usr/bin/env python
"""
I don't know what these are:
    - componentCodec
See core/Core/Events/EventConstants.h in mworks repo for event info
See core/Core/InterfaceHooks/ServerSide/Products/
    StandardSystemEventHandler.cpp for how events are handled by the server
"""

from event import Event
from utils import now

import experimentpacker

EVENT_TYPE = {'control': 1000, 'data': 1001, 'response': 1002}
PAYLOAD_TYPE = {
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

RESPONSE_CODE = {'success': 5001, 'failure': 5002}


def system_event(etype, ptype, payload=None, time=None):
    d = dict(event_type=EVENT_TYPE[etype], \
            payload_type=PAYLOAD_TYPE[ptype])
    if payload is not None:
        d['payload'] = payload
    time = now() if time is None else time
    return Event(1, time, d)


def system_event_macro(etype, ptype):
    def f(time=None):
        return system_event(etype, ptype, time=time)
    return f


# ------ system event creation ------ core/Core/Events/SystemEventFactory.cpp
# TODO componentCodecPackage : ln 73-78
# TODO protocolPackage : ln 82-138
def protocol_selection(protocol_name, time=None):
    return system_event('control', 'protocol_selection', \
            protocol_name, time=time)


# sendExperiment
#   core/Core/InterfaceHooks/ClientSide/Products/Client.cpp ln 131-152
#   core/Core/ExperimentDataLoading/ExperimentPackager.cpp
def send_experiment(filename):
    return system_event('control', 'experiment', \
            experimentpacker.make_payload(filename))


start_experiment = system_event_macro('control', 'start_experiment')
stop_experiment = system_event_macro('control', 'stop_experiment')
pause_experiment = system_event_macro('control', 'pause_experiment')
request_codec = system_event_macro('control', 'request_codec')
request_variables = system_event_macro('control', 'request_variables')
# TODO setEventForwarding : ln 202-218


def open_datafile(filename, overwrite=False, time=None):
    options = 1000 if overwrite else 1001
    return system_event('control', 'open_datafile', \
            dict(file=filename, options=options), time=time)


def close_datafile(filename=None, time=None):
    # FIXME see ln 191 in StandardSystemEventHandler.cpp
    # in core/Core/InterfaceHooks/ServerSide/Products/
    # filename does not appear to be used
    return system_event('control', 'close_datafile', \
            filename, time=time)


def close_experiment(experiment_name, time=None):
    return system_event('control', 'close_experiment', \
            experiment_name, time=time)


def save_variables(filename, overwrite=False, full_path=False, time=None):
    """
    filename : string
        full or relative path of file

    overwrite : bool
        should the file be overwritten?

    full_path : bool
        is the filename a full_path (or relative to ...)
    """
    overwrite = 1 if overwrite else 0
    full_path = 1 if full_path else 0
    p = dict(file=filename, overwrite=overwrite)
    p['full path'] = full_path
    return system_event('control', 'save_variables', p, time=time)


def load_variables(filename, full_path=False, time=None):
    """
    filename : string
        full or relative path of file

    full_path : bool
        is the filename a full_path (or relative to ...)
    """
    full_path = 1 if full_path else 0
    p = dict(file=filename)
    p['full path'] = full_path
    return system_event('control', 'load_variables', p, time=time)


# TODO Responses? ln 304 - 449
server_connected = system_event_macro('response', 'server_connected')
server_disconnected = system_event_macro('response', 'disserver_connected')


def experiment_loaded(result=0):
    return system_event('response', 'experiment_state', dict(loaded=0))


# TODO response parsing
