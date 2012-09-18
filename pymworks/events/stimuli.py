#!/usr/bin/env python
"""
pixel clock will change every update [code]
blank screen may always be there (never disappear)
"""

import copy
import logging


blacklisttests = [
        lambda s: (('name' in s.keys()) and (s['name'] == 'pixel clock')),
        lambda s: (('type' in s.keys()) and (s['type'] == 'blankscreen')),
        ]


class Stimulus(object):
    def __init__(self, time, attributes):
        self.time = time
        self.attributes = attributes
        self.duration = None

    def __cmp__(self, other):
        return dict.__cmp__(self.attributes, other.attributes)

    def to_dict(self):
        d = self.attributes.copy()
        d.update(dict(time=self.time, duration=self.duration))
        return d


def find_stims(onscreen, current, time):
    """ Return a list of stims that disappeared and the updated buffer"""
    stims = []
    for s in onscreen[:]:
        if s not in current:
            s.duration = time - s.time
            stims.append(copy.copy(s))
            # remove it from onscreen
            onscreen.remove(s)
    for s in current:
        if s not in onscreen:
            onscreen.append(s)
    return stims, onscreen


def to_stims(events, as_dicts=True):
    stims = []
    onscreen = []
    for e in sorted(events, key=lambda e: e.time):
        if e.value is None:
            logging.warning("Encountered event with value == None")
            if onscreen != {}:
                logging.error("Event.value == None with items on screen")
            continue
        current = []
        if hasattr(e.value, '__getitem__'):
            for stim in e.value:
                if not isinstance(stim, dict) or \
                        any([t(stim) for t in blacklisttests]):
                    continue
                current.append(Stimulus(e.time, stim))
        newstims, onscreen = find_stims(onscreen, current, e.time)
        stims += newstims
    return [s.to_dict() for s in stims]
