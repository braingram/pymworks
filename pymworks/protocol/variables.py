#!/usr/bin/env python
"""
Check that all variables are used
"""

import collections
import re

from . import utils


def iscap(s):
    return s[0].isupper() and s[1:].islower()


def iscamel(s):
    if not s[0].isupper():
        return False
    if s != ''.join(re.findall('[A-Z][^A-Z]*', s)):
        return False
    return True


def ismixed(s):
    if not s[0].islower():
        return False
    fw = re.findall('[a-z]*[^A-Z]', s)[0]
    tail = re.findall('[A-Z][^A-Z]*', s)
    if s != ''.join((fw, ) + tail):
        return False
    return True


def check_name(name):
    """
        CamelCase
        mixedCase
        lower
        lower_Under
        lower space
        UPPER
        UPPER_UNDER
        UPPER SPACE
        Cap
        Cap_Under
        Cap Space
    """
    if name.isupper():
        if '_' in name:
            return 'UPPER_UNDER'
        elif ' ' in name:
            return 'UPPER SPACE'
        return 'UPPER'
    elif name.islower():
        if '_' in name:
            return 'lower_under'
        elif ' ' in name:
            return 'lower space'
        return 'lower'
    elif '_' in name:
        if all([iscap(w) for w in name.split('_')]):
            return 'Cap_Under'
        else:
            return 'Unknown'
    elif ' ' in name:
        if all([iscap(w) for w in name.split(' ')]):
            return 'Cap Space'
        else:
            return 'Unknown'
    elif iscap(name):
        return 'Cap'
    elif iscamel(name):
        return 'CamelCase'
    elif ismixed(name):
        return 'mixedCase'
    return 'Unknown'


def get_all(e):
    e = utils.resolve_protocol(e)
    return list(e.iter('variable'))


def to_names(variables):
    return [v.attrib['tag'] for v in variables]


def get_names(e):
    return to_names(get_all(e))


def check_naming_convention(names):
    d = collections.defaultdict(list)
    for n in names:
        d[check_name(n)].append(n)
    return dict(d)


def find_variable_refs(e, vs, refs=None):
    e = utils.resolve_protocol(e)
    refs = dict([(v, []) for v in vs]) if refs is None else refs
    # check each node, skipping anything in variables
    for n in utils.iter_nodes(e, [lambda n: n.tag == 'variables']):
        for attr in n.attrib.values():
            for v in vs:
                if v in attr:
                    refs[v].append(n)
    return refs


def find_refs(e):
    vs = to_names(get_all(e))
    return find_variable_refs(e, vs)


def find_unused_variables(e):
    vs = to_names(get_all(e))
    refs = find_variable_refs(e, vs)
    return [k for k in refs if len(refs[k]) == 0]


def find_groupless_variables(e):
    vs = get_all(e)
    return [v for v in vs if v.attrib.get('groups', '').strip() == '']


def targeted_find_variable_refs(e, v):
    e = utils.resolve_protocol(e)
    refs = []
    # search
    for r in e.findall("//action[@type='assignment']"):
        if v == r.attrib['variable']:
            refs.append(r)
            continue
        pv = utils.parse_exp(r.attrib['value'])
        if v in pv.split():
            refs.append(r)
            continue
    for t in e.findall("//transition[@type='conditional']"):
        pv = utils.parse_exp(r.attrib['condition'])
        if v in pv.split():
            refs.append(r)
    for t in e.findall("//action[@type='if']"):
        pv = utils.parse_exp(r.attrib['condition'])
        if v in pv.split():
            refs.append(r)
    for t in e.findall("//action[@type='start_timer']"):
        pv = utils.parse_exp(r.attrib['duration'])
        if v in pv.split():
            refs.append(r)
    for t in e.findall("//range_replicator[@type='start_timer']"):
        if v == r.attrib['variable']:
            refs.append(r)
    for t in e.findall("//staircase[@type='start_timer']"):
        if v in [r.attrib[k] for k in
                 ['watch', 'output', 'lower_limit', 'upper_limit',
                  'step_size']]:
            refs.append(r)
    return refs
