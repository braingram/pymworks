#!/usr/bin/env python

import glob
import os

from .. import utils
## get appropriate xml parser
#import xml.etree.ElementTree
#v = float('.'.join(xml.etree.ElementTree.VERSION.split('.')[:2]))
#if v < 1.3:
#    import lxml.etree.ElementTree as ETree
#else:
#    ETree = xml.etree.ElementTree.ElementTree


class ExperimentLoadError(IOError):
    pass


class MediaParsingError(ExperimentLoadError):
    pass


def squash_filename(fn):
    return fn.replace('/', '_').replace('~', '_').replace(' ', '__')


def make_experiment_payload(fn):
    # expand path
    fn = os.path.expanduser(fn) if '~' in fn else fn
    fn = os.path.realpath(fn)

    b = ''
    try:
        with open(fn, 'r') as f:
            b = f.read()
    except IOError as E:
        raise ExperimentLoadError(E)
    if b == '':
        raise ExperimentLoadError("Loaded blank experiment from %s" % fn)
    sfn = squash_filename(fn)
    return dict(Contents=b, Filename=sfn)


def arange(start, end, step):
    if step == 0:
        raise ValueError("Invalid range step: %s cannot == 0" % (step))
    if ((end > start) and (step < 0)) or \
            ((end < start) and (step > 0)):
        raise ValueError("Invalid range params: %s, %s, %s" % \
                (start, end, step))
    if start == end:
        return [start, ]
    values = []
    i = start
    if end > start:
        while i <= end:
            values.append(i)
            i += step
    else:
        while i >= end:
            values.append(i)
            i += step
    return values


def to_number(s):
    return float(s) if '.' in s else int(s)


def parse_list_replicator_values(values, fn):
    tokens = values.split(',')
    if len(tokens) == 0:
        return []
    r = []
    for t in tokens:
        # TODO: does not escape strangly escaped sequences like: \&quot;
        if ('(' in t):  # filenames/FILENAMES
            assert ')' in t
            assert 'filenames' in t.lower()
            path = t.split('(')[1].split(')')[0]
            #v = t.split('(')[1].split(')')[0]

            wasrel = False  # was this path relative??
            if not os.path.isabs(path):
                path = os.path.realpath(os.path.join( \
                        os.path.dirname(fn), path))
                wasrel = True
            if '*' in path:  # wildcard
                fns = glob.glob(path)
                if len(fns) == 0:
                    raise ValueError( \
                            "list replicator filenames expression " \
                            "matched 0 files: %s" % values)
                if wasrel:
                    d = os.path.dirname(fn)
                    r += [os.path.relpath(f, d) for f in fns]
                else:
                    r += fns
            else:
                raise ValueError( \
                        "list replicator filenames expression " \
                        "missing wildcard[*]: %s" % values)
        else:
            try:
                v = to_number(t)
            except ValueError:
                v = t
            r.append(v)
    return r


def expand_replicator(node, fn):
    if node.tag == 'range_replicator':
        # checks
        for a in ('from', 'to', 'variable', 'step'):
            if a not in node.attrib:
                raise MediaParsingError( \
                        'range_replicator %s missing attribute: %s' % \
                        (node, a))
        try:
            s = to_number(node.attrib['from'])
            e = to_number(node.attrib['to'])
            d = to_number(node.attrib['step'])
        except ValueError as E:
            raise MediaParsingError( \
                    "Invalid range parameters: %s, %s, %s [%s]" % \
                    (a.attrib['from'], a.attrib['to'], a.attrib['step'], E))
        # numbers = ints or floats
        # right-inclusive: i.e range(0,3,1) = 0, 1, 2, 3
        values = arange(s, e, d)
    elif node.tag == 'list_replicator':
        # checks
        for a in ('values', 'variable'):
            if a not in node.attrib:
                raise MediaParsingError( \
                        'list_replicator %s missing attribute: %s' % \
                        (node, a))
        # values are a comma-separated list of
        #   1) numbers (ints/floats?)
        #   2) strings (e.g. 'five')
        #   3) filename expressions (e.g. filenames(foo), FILENAMES(foo/*))
        #       ! with wildcards
        values = parse_list_replicator_values(node.attrib['values'], fn)
    else:
        raise MediaParsingError('Invalid parent: %s, expected replicator' % \
                node)
    return values


def resolve_path(fn, node, tree, attrib):
    if attrib not in node.attrib:
        raise MediaParsingError("Missing attribute: %s in %s" % (attrib, node))
    path = node.attrib[attrib]
    if '$' not in path:
        return path
        #if os.path.isabs(path):
        #    return path
        ## use the relative path and the filename, to resolve a real path
        #return os.path.realpath(os.path.join(os.path.dirname(fn), path))
    # the path contains a '$', has a variable reference
    # the parent node must be parsed (it is [hopefully] a replicator)
    parents = tree.findall('.//*[@%s]..' % attrib)
    parent = None
    for p in parents:
        if node in p.getchildren():
            parent = p
            break
    if parent is None:
        raise MediaParsingError( \
                'Unable to find parent node for %s to resolve path: %s' % \
                (node, path))

    # find the correct form of the match string
    if '${' in path:
        ms = '${%s}' % parent.attrib['variable']
    else:
        ms = '$' + parent.attrib['variable']

    # check that parent has 'variable' and variable in path
    if ('variable' not in parent.attrib) or (ms not in path):
        raise MediaParsingError( \
                'Invalid parent data %s, unable to resolve path: %s' % \
                (parent, path))

    # expand parent to evaluate '$'
    values = expand_replicator(parent, fn)
    paths = []
    for v in values:
        paths.append(path.replace(ms, str(v)))
    return paths


def find_media_references(fn):
    """
    Returns a list of filenames that must be packaged up
    """
    # to resolve paths, use (already expanded) fn
    mfns = []
    try:
        #e = xml.etree.ElementTree.parse(fn)
        e = utils.ETree(file=fn)
        for n in e.findall('.//*[@path]'):
            r = resolve_path(fn, n, e, 'path')
            if isinstance(r, (tuple, list)):
                mfns += r
            else:
                mfns.append(r)
        for n in e.findall('.//*[@directory_path]'):
            # add as directory
            r = resolve_path(fn, n, e, 'directory_path')
            if not isinstance(r, (tuple, list)):
                r = (r, )
            for i in r:
                if os.path.isabs(i):
                    fns = glob.glob(os.path.join(i, '*'))
                else:
                    d = os.path.dirname(fn)
                    ai = os.path.realpath(os.path.join(d, i))
                    fns = [os.path.relpath(f) for f in \
                            glob.glob(os.path.join(ai, '*'))]
                mfns += fns
    except IOError as E:  # for missing file
        raise MediaParsingError(E)
    except TypeError as E:  # for bad search strings
        raise MediaParsingError(E)
    return mfns


def make_media_buffers_payload(filename):
    # return None if none are found
    # find all things with 'name': "path" or "directory_path"
    # these appear to be attributes of tags
    fns = find_media_references(filename)
    if len(fns) == 0:
        return None
    mbs = []
    d = os.path.dirname(filename)
    for fn in fns:
        if os.path.isabs(fn):
            afn = fn
        else:
            afn = os.path.realpath(os.path.join(d, fn))
        try:
            with open(afn, 'rb') as f:
                mbs.append(dict(Filename=fn, Contents=f.read()))
        except IOError as E:
            raise MediaParsingError('Failed to package %s: %s' % (fn, E))
    return mbs


def make_payload(fn):
    p = dict(Experiment=make_experiment_payload(fn))
    m = make_media_buffers_payload(fn)
    if (m is not None) and (len(m) > 0):
        p['Media Buffers'] = m
    return p
