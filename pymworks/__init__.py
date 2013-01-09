#!/usr/bin/env python

from io import datafile, stream, load
from events.event import Event

from io.datafile import DataFile, IndexedDataFile, open_file
from io.stream import Client

from io.datafile import open_file as open

import events

__all__ = ['datafile', 'Event', 'DataFile', 'IndexedDataFile', 'open_file',
        'stream', 'Client', 'load', 'events']

#import datafile
#from datafile import DataFile, IndexedDataFile, open_file
#from event import Event
#
#__all__ = ['datafile', 'DataFile', 'Event', 'IndexedDataFile', 'open_file', \
#        'Event']
