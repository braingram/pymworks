#!/usr/bin/env python


import os
import re


from . import variables


def resolve_file(f):
    if isinstance(f, (str, unicode)):
        return open(os.path.expanduser(f), 'r')
    return f


def varbinds(f):
    f = resolve_file(f)
    s = f.read()
    p = """var-bind=['"](.*)["']"""
    return re.findall(p, s)


def varbinds_to_varnames(vbs):
    vns = []
    for vb in vbs:
        if ':' in vb:
            vns.append(vb.split(':')[-1])
        else:
            vns.append(vb)
    return list(set(vns))


def get_varnames(f):
    return varbinds_to_varnames(varbinds(f))


def check_for_unknown_variables(template, protocol):
    """
    Check a template for reference to variables NOT in the protocol
    """
    tvns = get_varnames(template)
    pvns = variables.get_names(protocol)
    return [n for n in tvns if n not in pvns]
