#!/usr/bin/env python

import os
import re
import socket

import datafile
import stream


def guess_class(addr):
    if isinstance(addr, (tuple, list)):
        return stream.Client
    if not isinstance(addr, str):
        raise TypeError("Unknown type for addr: %s" % addr)
    if os.path.splitext(addr)[1].lower == '.mwk':
        return datafile.IndexedDataFile
    if re.match(r'[0-9]+(?:\.[0-9]+){3}', addr):
        return stream.Client
    if os.path.exists(addr):
        return datafile.IndexedDataFile
    try:
        socket.gethostbyname(addr)
        return stream.Client
    except socket.error:
        pass
    raise ValueError("Unknown addr: %s" % addr)


def load(addr, C=None):
    if C is None:
        C = guess_class(addr)
    if isinstance(addr, (tuple, list)):
        return C(*addr)
    else:
        return C(addr)


__all_ = ['datafile', 'stream']
