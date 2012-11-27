#!/usr/bin/env python
"""
"""

import collections


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
