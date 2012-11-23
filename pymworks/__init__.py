#!/usr/bin/env python

from io import datafile, stream, load
from event import Event

from io.datafile import DataFile, IndexedDataFile, open_file
from io.stream import Client

__all__ = ['datafile', 'Event', 'DataFile', 'IndexedDataFile', 'open_file',
        'stream', 'Client', 'load']

#import datafile
#from datafile import DataFile, IndexedDataFile, open_file
#from event import Event
#
#__all__ = ['datafile', 'DataFile', 'Event', 'IndexedDataFile', 'open_file', \
#        'Event']
