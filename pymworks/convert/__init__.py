#!/usr/bin/env python

import hdf5er
import pickler


def to_hdf5(datafile, filename):
    return hdf5er.datafile_to_hdf5(datafile, filename)


def to_pickle(datafile, filename):
    return pickler.datafile_to_pickle(datafile, filename)

__all__ = ['hdf5er', 'pickler']
