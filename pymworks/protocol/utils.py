#!/usr/bin/env python

from .. import utils
#import xml.etree.ElementTree


def load(fn):
    return utils.ETree(file=fn)
    #e = xml.etree.ElementTree.parse(fn)
    #return e


def parse_exp(v):
    for c in ['(', ')', '+', '-', '/', '#GT', '#LT', \
            '#AND', '#OR', '#NOT', '#LE', '#GE', '==']:
        v = v.replace(c, ' ')
    return v.split()


def iter_nodes(e, stops=[]):
    """
    stops : tag names
    """
    if hasattr(e, 'getroot'):
        for n in iter_nodes(e.getroot(), stops):
            yield n
        return
    if any((f(e) for f in stops)):
        return
    yield e
    for se in e:
        for n in iter_nodes(se, stops):
            yield n
