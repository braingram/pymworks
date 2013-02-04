#!/usr/bin/env python
"""
check that all states are visited and how are they visited
"""

import networkx

ENTERSTATE = "Enter"
EXITSTATE = "Exit"


class FindError(Exception):
    pass


def find_state_systems(e):
    return e.findall('.//task_system')


def find_states(e):
    # finds subelements of e
    return e.findall('.//task_system_state')


def find_first_state(e):
    return e.find('./task_system_state')


def find_transitions(e):
    # types: (all have: tag, type)
    # - conditional: target, condition
    # - timer_expired: target, timer
    # - direct: target
    # - yield:
    return e.findall('.//transition')


def make_graph(e, exit_node=EXITSTATE, enter_node=ENTERSTATE):
    try:
        e = find_state_systems(e)[0] if \
                ((not hasattr(e, 'tag')) or (e.tag != 'task_system')) \
                else e
    except IndexError:
        raise FindError("No state systems found under: %s" % e)
    states = find_states(e)
    transitions = dict([(s, find_transitions(s)) for s in states])
    g = networkx.DiGraph()
    g.add_node(enter_node)
    for s in states:
        g.add_node(s.attrib['tag'], s.attrib)
    g.add_node(exit_node)
    fs = find_first_state(e)
    g.add_edge(enter_node, fs.attrib['tag'])
    for (s, ts) in transitions.iteritems():
        for t in ts:
            if 'target' in t.attrib:
                g.add_edge(s.attrib['tag'], t.attrib['target'], t.attrib)
            elif t.attrib['type'] == 'yield':
                g.add_edge(s.attrib['tag'], exit_node, t.attrib)
    return g


def find_unused_states(g, ignore=[ENTERSTATE, EXITSTATE]):
    states = []
    for (k, v) in g.degree().iteritems():
        if (v == 1) and (v not in ignore):
            states.append(k)
    return states


def find_potential_stalls(g, ignore=[ENTERSTATE, EXITSTATE]):
    """
    Find states where the transitions may 'stall'
    for example they are all conditional
    """
    stalls = []
    for n in g:
        if n in ignore:
            continue
        edges = g.out_edges(n)
        stall = True
        for e in edges:
            t = g.get_edge_data(*e)
            if t['type'] in ('timer_expired', 'direct', 'yield'):
                stall = False
                break
        if stall:
            stalls.append(n)
    return stalls
