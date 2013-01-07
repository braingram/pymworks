#!/usr/bin/env python
"""
pixel clock will change every update [code]
blank screen may always be there (never disappear)
"""

import copy
import logging


blacklisttests = [
        #lambda s: (('name' in s.keys()) and (s['name'] == 'pixel clock')),
        lambda s: (('type' in s.keys()) and (s['type'] == 'blankscreen')),
        ]


class Stimulus(object):
    def __init__(self, time, attributes, pixelclock=None):
        self.time = time
        self.attributes = attributes
        if pixelclock is not None:
            self.attributes['bit_code'] = pixelclock['bit_code']
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
            stimulus = None
            pixelclock = None
            for stim in e.value:
                if not isinstance(stim, dict) or \
                        any([t(stim) for t in blacklisttests]):
                    continue
                if ('name' in stim.keys()) and (stim['name'] == 'pixel clock'):
                    pixelclock = stim
                else:
                    if stimulus is not None:
                        logging.warning("Two stimuli onscreen: %s, %s" \
                                % (stimulus, stim))
                    stimulus = stim
            if stimulus is not None:
                current.append(Stimulus(e.time, stimulus, pixelclock))
        newstims, onscreen = find_stims(onscreen, current, e.time)
        stims += newstims
    return [s.to_dict() for s in stims]


def to_pixel_clock_codes(events):
    """
    Return list of tuples (time, code)
    """
    codes = []
    for e in sorted(events, key=lambda e: e.time):
        code = None
        if e.value is None:
            logging.warning("Encountered event with value == None")
            continue
        if hasattr(e.value, '__getitem__'):
            for stim in e.value:
                if not isinstance(stim, dict):
                    continue
                if ('name' in stim.keys()) and (stim['name'] == 'pixel clock'):
                    if code is not None:
                        logging.warning("Two codes found for event %s: %s, %s"\
                               % (e, code, stim['bit_code']))
                    code = stim['bit_code']
        if codes is not None:
            codes.append((e.time, code))
    return codes
