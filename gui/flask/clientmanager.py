#!/usr/bin/env python
"""
Serve up mworks events to some sort of web ui.
Listen to one/many server(s) for certain events (NOT ALL)

EventServer (ONLY 1)
    ClientListener (1/Many)

Assume clients are buggy POSs that will fail... often

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




Example:
    1) start server
    2) receive CONNECT(host)
    3) receive LISTEN(host, name)
    4) receive STATE(host)
"""

import time

from pymworks.event import Event
import pymworks.stream
#pymworks.stream.NamedCallbackCodecClient(host='', port=0)


class StatefulClient(pymworks.stream.NamedCallbackCodecClient):
    def __init__(self, **kwargs):
        pymworks.stream.NamedCallbackCodecClient.__init__(self, **kwargs)
        self.state = {}

    def listen(self, name):
        if name not in self.state:
            self.register_callback(name, self.update_state)

    def update_state(self, event):
        self.state[event.name] = event


def fail(s):
    return (False, "ERROR: %s" % s)


def success(r=None):
    return (True, r)


class ClientManager(object):
    def __init__(self, hosts=None, names=None, tdelay=0):
        self.clients = {}
        self.tdelay = tdelay

    def now(self):
        return int(time.time() * 1E6 + self.tdelay)

    def update(self, **kwargs):
        for c in self.clients.values():
            c.update(**kwargs)

    def read(self, host='', name='', time=None):
        if host not in self.clients:
            raise ValueError('Unknown host[%s]' % host)
        c = self.clients[host]
        if name not in c.state:
            raise ValueError('Variable state unknown[%s]' % name)
        e = c.state[name]
        if (time is not None) and (time >= e.time):
            return None
        return e

    def write(self, host='', name='', value=None):
        if host not in self.clients:
            raise ValueError('Unknown host[%s]' % host)
        c = self.clients[host]
        code = c.rcodec[name]
        c.write_event(Event(code, self.now(), value))

    def listen(self, host='', name=''):
        if host not in self.clients:
            raise ValueError('Unknown host[%s]' % host)
        self.clients[host].listen(name)

    def state(self, host=''):
        if host not in self.clients:
            raise ValueError('Unknown host[%s]' % host)
        return self.clients[host].state

    def connect(self, host='fake', port=19989):
        c = StatefulClient(host, port)
        self.clients[c.host] = c

    def disconnect(self, host=None):
        if host not in self.clients:
            raise ValueError('Unknown host[%s]' % host)
        del self.clients[host]

    # read, write, connect, disconnect, reconnect
    def process_query(self, **query):
        """
        query = dict
        query['action'] = action to perform
        query[...] = kwargs

        Returns
        ------
        outcome : bool
            If query was successful
        result : varies
            Result of query
        """
        a = query.pop('action', 'STATE')
        if not (hasattr(self, a)):
            return fail("Unknown action %s" % a)
        try:
            r = getattr(self, a)(**query)
            return success(r)
        except Exception as E:
            return fail("Action[%s] failed=%s" % (a, E))


if __name__ == '__main__':
    actions = [
            dict(action='connect', host='fake'),
            dict(action='listen', host='fake', name='a'),
            ]
    # connect to host
    # listen for variable changes
    # read
