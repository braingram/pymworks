#!/usr/bin/env python
"""

-- Event Comparisons --
comparisons of events are ill-defined
for example:
 e0 = Event(0, 1, 0)
 e1 = Event(0, 0, 1)
is e0 > e1?
 e0.value < e1.value == True
 e0.time < e1.value == False
therefore, only compare the parts of each event
 e0.value > e1.value
and pass correct keys to other functions:
 max([e0, e1], key=lambda e: e.time)  # = e0
 max([e0, e1], key=lambda e: e.value)  # = e1
"""

import collections


comparison_error = ArithmeticError( \
        "Event comparisons are ill-defined, instead compare the code, " \
        "time or values directly")


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

    def __eq__(self, other):
        return (self.name == other.name) and (self.time == other.time) and \
                (self.value == other.value)

    def __ne__(self, other):
        return not self.__eq__(other)

    # comparisons of events are ill-defined
    def __lt__(self, other):
        raise comparison_error

    def __le__(self, other):
        raise comparison_error

    def __gt__(self, other):
        raise comparison_error

    def __ge__(self, other):
        raise comparison_error
