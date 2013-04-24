#!/usr/bin/env python


def valuemax(events):
    return max(events, key=lambda e: e.value)


def valuemin(events):
    return min(events, key=lambda e: e.value)


def valuerange(events):
    return valuemax(events).value - valuemin(events).value


def time_in_state(events, test=lambda e: e.value < 500.):
    """
    Measure amount of time when test(e) == True during a sequence of events.

    returns (time where test(e) == True, total time)

    Example: to test the amount of time that 'head_input' < 500. run
        st, tt = time_in_state(df.get_events('head_input'), \
                test=lambda e: e.value < 500.)
    """
    sevents = sorted(events, key=lambda e: e.time)
    t0 = sevents[0].time
    t1 = sevents[-1].time
    state = test(sevents[0])
    t = sevents[0].time

    stime = 0
    for e in sevents:
        if (not state) and test(e):
            t = e.time
            state = True
            continue
        if state and (not test(e)):
            stime += e.time - t
            state = False

    if state:
        stime += t1 - t
    return stime, t1 - t0


def remove_non_incrementing(events):
    """
    Remove events where events[i+1].value != (events[i].value + 1)

    Does a forward, followed by a backwards remove
    """
    return remove(
        remove(events[:],
               test=lambda a, b: b.value > (a.value + 1),
               recurse=True, direction=1)[:],
        test=lambda a, b: b.value < (a.value + 1),
        recurse=True, direction=-1)


def remove(events, test=lambda a, b: b.value > (a.value + 1),
           recurse=True, direction=1):
    bad_indices = []
    if direction == 1:
        ievents = xrange(len(events) - 1)
        t = lambda i: test(events[i], events[i + 1])
    elif direction == -1:
        ievents = xrange(1, len(events))
        t = lambda i: test(events[i - 1], events[i])
    bad_indices = filter(t, ievents)
    for i in bad_indices[::-1]:
        del(events[i])
    if recurse and len(bad_indices):
        remove(events, test=test, recurse=recurse, direction=direction)
    return events


def removeforward(events, test=lambda a, b: b.value > (a.value + 1),
                  recurse=True):
    """
    Remove events that satisfy test(events[i], events[i+1])
    """
    bad_indices = []
    for i in xrange(len(events) - 1):
        if test(events[i], events[i + 1]):
            bad_indices.append(i)
    for i in bad_indices[::-1]:
        del(events[i])
    if recurse and len(bad_indices):
        removeforward(events, test=test, recurse=recurse)
    return events


def removebackward(events, test=lambda a, b: b.value < (a.value + 1),
                   recurse=True):
    """
    Remove events that satisfy test(events[i-1], events[i])
    """
    bad_indices = []
    for i in xrange(1, len(events)):
        if test(events[i - 1], events[i]):
            bad_indices.append(i)
    for i in bad_indices[::-1]:
        del(events[i])
    if recurse and len(bad_indices):
        removebackward(events, test=test, recurse=recurse)
    return events
