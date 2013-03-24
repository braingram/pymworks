#!/usr/bin/env python

import os
import re
import socket

import datafile
import stream

try:
    import hdf5
    has_hdf5 = True
except:
    has_hdf5 = False


def guess_class(addr):
    if isinstance(addr, (tuple, list)):
        return stream.Client
    if not isinstance(addr, str):
        raise TypeError("Unknown type for addr: %s" % addr)
    if has_hdf5 and isinstance(addr, hdf5.tables.file.File):
        return hdf5.HDF5DataFile
    if os.path.splitext(addr)[1].lower == '.mwk':
        return datafile.IndexedDataFile
    if os.path.splitext(addr)[1].lower == '.h5':
        if not has_hdf5:
            raise IOError('Cannnot read hdf5 file %s without pytables' % addr)
        return hdf5.HDF5DataFile
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


__all__ = ['datafile', 'stream']
if has_hdf5:
    __all__.append('hdf5')
