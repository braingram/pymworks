This is a pure-python module for reading mworks data files.

Requirements
----

Nothing for 'basics' on python 2.7

python 2.6 requires lxml because the ElementTree
included with py2.6 does not support enough XPath

protocol inspection requires networkx

====
Intro
====

MWorks files are made up of events. Each event has

time
  Unsigned integer. Time of event (in microseconds).
  May be relative to system time or server start time.

code
  Unsigned integer. Number assigned to this type of event.
  Some are standard (0 = codec, etc...) others are experiment dependent.

value
  Flexible type. The 'payload' of the event.
  May be a dict, list, int, None, etc...

One special event (name = 'codec', code = 0) is useful for understanding
other events. The codec contains (as a value) a dictionary of codes (as keys)
and names (as values).

Opening files
----

An MWorks file can be opened in pymworks using pymworks.open_file.

::

    import pymworks
    fn = 'foo.mwk'
    df = pymworks.open_file(fn)

By default, open_file with index the file (speeding up event fetching).
This index is written to disk as as a hidden file ('.' pre-pended).
For the above example (opening foo.mwk) a index file '.foo.mwk' would be
created if it did not already exist. If you do not want to index the file,
set the indexed kwarg to False for open_file:

::

    df = pymworks.open_file(fn, indexed=False)

The codec for this datafile is accessable as df.codec and for convenience a
reversed version (keys=names, values=codes) is available as df.rcodec

::

    df.codec  # dict, keys = codes, values = event names
    df.rcodec  # dict, keys = event names, values = codes

Reading events
----

Events can be accessed several ways, the easiest being df.get_events.

::

    evs = df.get_events()  # get all events
    cevs = df.get_events(0)  # get all events with code 0

    # get all events with name 'success'
    sevs = df.get_events('success')

    # get_events also accepts a list of names (or codes)
    toevs = df.get_events(['success', 'failure', 'ignore'])

    # or a timerange (in microseconds)
    eevs = df.get_events(time_range=[0, 60 * 1E6])  # events during first minute

Events (type pymworks.datafile.Event) each contain a time, code and value

::

    e = df.get_events('success')[0]  # get first success event
    e.time  # time of event (in microseconds)
    e.code  # event code
    e.value  # value for event

====
Notes
====

LDOBinary.py and ScarabMarshal.py are originally from the mworks/mw_data_tools repo

LDOBinary.py was fixed to actually work and not just throw errors
