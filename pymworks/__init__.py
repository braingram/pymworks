#!/usr/bin/env python

from io import datafile, stream, load
from events.event import Event

from io.datafile import DataFile, IndexedDataFile, open_file, save_file
from io.stream import Client

from io.datafile import open_file as open
from io.datafile import save_file as save

import events
import protocol
import stats

__version__ = "2.0.1"

__all__ = ['datafile', 'Event', 'DataFile', 'IndexedDataFile', 'open_file',
           'save_file', 'save', 'stream', 'Client', 'load', 'events',
           'protocol', 'stats']

#import datafile
#from datafile import DataFile, IndexedDataFile, open_file
#from event import Event
#
#__all__ = ['datafile', 'DataFile', 'Event', 'IndexedDataFile', 'open_file', \
#        'Event']
