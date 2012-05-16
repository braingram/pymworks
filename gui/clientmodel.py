#!/usr/bin/env python
"""
simple packed window with a top panel containing
[+:Button][host:Text][Port:Spin][Load:Button]

Window contains rows, one for each host, constructed by a 
template (see template file)

Need to:
    1) bind variables
    2) construct widgets
    3) handle loop & update
"""

import time

import Tkinter as tk

import pymworks
import pymworks.stream


vtypes = {\
        'Checkbutton': tk.IntVar,
        'Spinbox': tk.DoubleVar,
        'Scale': tk.DoubleVar,
        }


class ClientManager(object):
    def __init__(self, client=None, host='127.0.0.1', port=19989):
        if client is None:
            client = pymworks.stream.CallbackCodecClient(host=host, port=port)
        self.client = client

        # construct stuff for the client to display/connect
        self.variables = {}
        self.mask = {}
        self.traces = {}
    
    def register_variable(self, name, var):
        self.variables[name] = var
        # register as a callback
        self.client.register_callback(name, self.new_event)
        self.attach_trace(name)

    def new_event(self, event):
        if event.code in self.client.codec:
            name = self.client.codec[event.code]
            self.update_variable(name, event.value)
        else:
            print >> "Received unknown code: %s" % event.code

    def update_variable(self, name, value):
        self.mask[name] = value
        self.variables[name].set(value)
            

    def write_event(self, name, index, mode):
        var, name = self.find_variable(name)
        #var = self.variables[name]
        value = var.get()
        if name in self.mask:
            if value == self.mask[name]:
                self.mask.pop(name)
                return
        self.client.write_event([self.client.rcodec[name], self.now(), value])

    def attach_trace(self, name):
        if name not in self.traces:
            print "attaching trace: %s" % name
            self.traces[name] = self.variables[name].trace('w', self.write_event)

    def dettach_trace(self, name):
        if name in self.traces:
            print "dettaching trace: %s" % name
            trace = self.traces.pop(name)
            self.variables[name].trace_vdelete('w', trace)

    def find_variable(self, name):
        for (k, v) in self.variables.iteritems():
            if v._name == name:
                return v, k
        raise KeyError("Variable %s not found" % name)

    def now(self, delay=0):
        return int(time.time() * 1E6) + delay

    def update(self, max_n=10, timeout=0.01):
        """
        Call in tk.mainloop
        """
        self.client.update(max_n, timeout)



class ClientView(object):
    def __init__(self, client_manager, parent, prefix='', template_file='template'):
        self.parent = parent
        self.client_manager = client_manager
        self.frame = tk.Frame(parent)
        # setup the view for this client
        # read in the template
        names, widget_defs = read_template(template_file)

        # make necessary variables and controls
        variables = make_variables(parent, prefix, names, widget_defs)
        widgets = make_widgets(self.frame, variables, names, widget_defs)

        # register variables with client manager
        [self.client_manager.register_variable(n, v) for n, v in zip(names, variables)]

        # pack widgets
        for w in widgets:
            w.pack(side=tk.LEFT)

        self.frame.pack(fill=tk.X)  # this fills the width


def read_template(filename):
    names = []
    widgets = []
    with open(filename, 'r') as F:
        for l in F:
            if l.strip()[0] == '#':
                continue
            if '#' in l:
                l = l.split('#')[0].strip()
            name, widget = l.split(':')
            names.append(name.strip())
            widgets.append(widget.strip())
    return names, widgets


def make_variables(parent, prefix, names, wdefs):
    return [make_variable(parent, prefix+n, wd) for n, wd in zip(names, wdefs)]


def make_variable(parent, name, wdef):
    vtype = lookup_type(wdef)
    return vtype(parent, name=name)


def lookup_type(wdef):
    wd = wdef.split()[0]
    return vtypes[wd]


def make_widgets(parent, variables, names, wdefs):
    widgets = []
    for v, n, wd in zip(variables, names, wdefs):
        widgets.append(make_label(parent, n))
        widgets.append(make_widget(parent, v, wd))
    return widgets


def make_label(parent, name):
    return tk.Label(parent, text=name)


def make_widget(parent, variable, wdef):
    wd = wdef.split()[0]
    assert hasattr(tk, wd), "Invalid widget name: %s" % wd
    if wd == 'Scale':
        kwargs = {'variable': variable}
    elif wd == 'Checkbutton':
        kwargs = {'variable': variable, 'onvalue': 1, 'offvalue': 0}
    else:
        kwargs = {'textvariable': variable}
    return getattr(tk, wd)(parent, **kwargs)
