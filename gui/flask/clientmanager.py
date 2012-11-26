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

import pymworks.io.stream


def fail(s):
    return (False, "ERROR: %s" % s)


def success(r=None):
    return (True, r)


class ClientManager(object):
    def __init__(self, hosts=None, names=None, tdelay=0):
        self.clients = {}

    def update(self, **kwargs):
        for c in self.clients.values():
            c.update(**kwargs)

    def connect(self, host='fake', port=19989, **kwargs):
        try:
            c = pymworks.io.stream.Client(host, port, **kwargs)
            self.clients[c.host] = c
        except Exception as E:
            raise E

    def disconnect(self, host=None):
        if host not in self.clients:
            raise ValueError('Unknown host[%s]' % host)
        del self.clients[host]

    # read, write, connect, disconnect, reconnect
    def process_query(self, **query):
        """
        query = dict
        query['client'] = client address
        query['function'] = action to perform
        query['args'] = arguments
        query['kwargs'] = kwargs

        Returns
        ------
        outcome : bool
            If query was successful
        result : varies
            Result of query
        """
        c = query.pop('client', None)
        f = query.pop('function', 'STATE')
        a = query.pop('args', [])
        kw = query.pop('kwargs', {})

        try:
            o = self if c is None else self.clients[c]
        except KeyError:
            return fail("Unknown client: %s" % c)

        if not (hasattr(o, f)):
            return fail("Unknown function %s" % f)
        try:
            r = getattr(o, f)(*a, **kw)
            return success(r)
        except Exception as E:
            return fail("function[%s.%s] failed=%s" % (o, f, E))


if __name__ == '__main__':
    actions = [
            dict(action='connect', host='fake'),
            dict(action='listen', host='fake', name='a'),
            ]
    # connect to host
    # listen for variable changes
    # read
