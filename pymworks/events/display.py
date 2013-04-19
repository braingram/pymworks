#!/usr/bin/env python
"""
pixel clock will change every update [code]
blank screen may always be there (never disappear)
"""

import copy
import logging

import utils


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


def to_stims(events, as_dicts=True, blacklist=None):
    if blacklist is None:
        blacklist = blacklisttests
    if not isinstance(blacklist, (tuple, list)):
        blacklist = (blacklist, )
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
                        any([t(stim) for t in blacklist]):
                    continue
                if ('name' in stim.keys()) and (stim['name'] == 'pixel clock'):
                    pixelclock = stim
                else:
                    if stimulus is not None:
                        logging.warning(
                            "Two stimuli onscreen: %s, %s"
                            % (stimulus, stim))
                    stimulus = stim
            if stimulus is not None:
                current.append(Stimulus(e.time, stimulus, pixelclock))
        newstims, onscreen = find_stims(onscreen, current, e.time)
        stims += newstims
    if as_dicts:
        return [s.to_dict() for s in stims]
    return stims


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
                        logging.warning(
                            "Two codes found for event %s: %s, %s"
                            % (e, code, stim['bit_code']))
                    code = stim['bit_code']
        if codes is not None:
            codes.append((e.time, code))
    return codes


def to_trials(stim_display_events, outcome_events, remove_unknown=True,
              duration_multiplier=2, stim_blacklists=None):
    """
    If remove_unknown, any trials where a corresponding outcome_event cannot
    be found will be removed.

    If duration_multiplier is not None, to_trials will check to see if the
    outcome event occured within duration_multiplier * duration microseconds
    of the trial start. If the outcome event occured later, the trial outcome
    will be marked as unknown.
    """
    if (len(outcome_events) == 0) or (len(stim_display_events) == 0):
        return []
    assert hasattr(outcome_events[0], 'name')

    trials = to_stims(stim_display_events, as_dicts=True,
                      blacklist=stim_blacklists)

    if (len(trials) == 0):
        return []

    outcomes = utils.sync(outcome_events, trials,
                          direction=1, mkey=lambda x: x['time'])

    assert len(trials) == len(outcomes)
    unknowns = []
    if duration_multiplier is None:
        dtest = lambda t, o: True
    else:
        dtest = lambda t, o: \
            o.time < (t['time'] + t['duration'] * duration_multiplier)
    for i in xrange(len(trials)):
        if (outcomes[i] is not None) and dtest(trials[i], outcomes[i]):
            trials[i]['outcome'] = outcomes[i].name
        else:
            if remove_unknown:
                unknowns.append(i)
            else:
                trials[i]['outcome'] = 'unknown'

    # remove trials with 'unknown' outcome, in reverse
    for u in unknowns[::-1]:
        del trials[u]

    return trials
