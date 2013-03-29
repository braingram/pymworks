#!/usr/bin/env python
"""
I don't know what these are:
    - componentCodec
See core/Core/Events/EventConstants.h in mworks repo for event info
See core/Core/InterfaceHooks/ServerSide/Products/
    StandardSystemEventHandler.cpp for how events are handled by the server
"""

import logging

from event import Event
from utils import now

import experimentpacker

RESPONSE_CODE = {'success': 5001, 'failure': 5002}
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
        'clock_offset': 3013,
        'connected': 3014,
        'resume_experiment': 3015,

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
def load_experiment(filename):
    return system_event('control', 'experiment', \
            experimentpacker.make_payload(filename))


start_experiment = system_event_macro('control', 'start_experiment')
stop_experiment = system_event_macro('control', 'stop_experiment')
pause_experiment = system_event_macro('control', 'pause_experiment')
resume_experiment = system_event_macro('control', 'resume_experiment')
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


server_connected = system_event_macro('response', 'server_connected')
server_disconnected = system_event_macro('response', 'disserver_connected')


def experiment_loaded(result=0):
    return system_event('response', 'experiment_state', dict(loaded=0))


# states
#   server : connected/disconnected
#   experiment : loaded, paused, running, path, name, saved variables
#   protocol : current/available/experiment_name...
#       some of these events are weird, no event_type, no payload_type... :(
#       others are ok (et: 1001, pt: 2001
#   datafile : opened/closed
#   variables : many
def parse_warning(message, event):
    logging.warning('%s: %s' % (message, event))


def parse_protocol_payload(payload, state):
    for k in ('current protocol', 'protocols', 'experiment name'):
        if k in payload:
            state[k] = payload[k]
        else:
            if k in state:
                del state[k]
    return state


def parse_experiment_state_payload(payload, state):
    for k in ('experiment name', 'experiment path', 'loaded', \
            'paused', 'running', 'saved variables'):
        if k in payload:
            state[k] = payload[k]
        else:
            if k in state:
                del state[k]
    return state


def parse_datafile_opened_payload(payload, state):
    if not (isinstance(payload, (tuple, list)) and \
            len(payload) == 2 and \
            payload[0] in RESPONSE_CODE.values()):
        parse_warning('Invalid datafile_opened payload', payload)
        return state
    code, filename = payload
    if code == RESPONSE_CODE['success']:
        state['datafile'] = filename
        state['datafile error'] = False
        state['datafile saving'] = True
    elif code == RESPONSE_CODE['failure']:
        state['datafile'] = ''
        state['datafile error'] = True
        state['datafile saving'] = False
    else:
        parse_warning('Invalid resopnse code', payload)
    return state


def parse_datafile_closed_payload(payload, state):
    if not (isinstance(payload, (tuple, list)) and \
            len(payload) == 2 and \
            payload[0] in RESPONSE_CODE.values()):
        parse_warning('Invalid datafile_opened payload', payload)
        return state
    code, filename = payload
    if code == RESPONSE_CODE['success']:
        state['datafile'] = ''
        state['datafile error'] = False
        state['datafile saving'] = False
    elif code == RESPONSE_CODE['success']:
        state['datafile'] = ''
        state['datafile error'] = True
        #state['datafile saving']  # not sure what to do here
    else:
        parse_warning('Invalid resopnse code', payload)
    return state


def parse_state(event, state=None):
    state = {} if state is None else state
    if 'event_type' not in event.value:  # probably a protocol event
        return parse_protocol_payload(event.value, state)
    et = event.value['event_type']
    if 'payload_type' not in event.value:
        parse_warning('Missing payload_type', event)
        return state
    pt = event.value['payload_type']
    payload = event.value.get('payload', None)
    if (et == EVENT_TYPE['data']):
        if (pt == PAYLOAD_TYPE['protocol']):  # probably a protocol event
            if 'payload' not in event.value:
                parse_warning('Missing payload', event)
                return state
            return parse_protocol_payload(event.value['payload'], state)
        else:
            parse_warning('Unknown payload_type', event)
            return state
    if (et == EVENT_TYPE['response']):
        if pt == PAYLOAD_TYPE['experiment_state']:
            if payload is None:
                parse_warning('Missing payload', event)
                return state
            return parse_experiment_state_payload(payload, state)
        elif pt == PAYLOAD_TYPE['datafile_opened']:
            if payload is None:
                parse_warning('Missing payload', event)
                return state
            return parse_datafile_opened_payload(payload, state)
        elif pt == PAYLOAD_TYPE['datafile_closed']:
            if payload is None:
                parse_warning('Missing payload', event)
                return state
            return parse_datafile_closed_payload(payload, state)
        elif pt == PAYLOAD_TYPE['client_connected']:
            state['client connected'] = True
            return state
        elif pt == PAYLOAD_TYPE['client_disconnected']:
            state['client connected'] = False
        elif pt == PAYLOAD_TYPE['server_connected']:
            state['server connected'] = True
            return state
        elif pt == PAYLOAD_TYPE['server_disconnected']:
            state['server connected'] = False
            return state
        parse_warning('Unknown payload_type', event)
        return state
    parse_warning('Failed to parse event', event)
    return state
