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

import json
import sys

import Tkinter as tk


class TouchButton(tk.Button):
    def __init__(self, *args, **kwargs):
        action = kwargs.pop('action', 'send')
        if action == 'send':
            kwargs['command'] = self.touch
        else:
            raise ValueError("Unknown action: %s" % action)
        tk.Button.__init__(self, *args, **kwargs)

    def touch(self):
        self.setvar(self['textvariable'].string, self['text'])


class SafeSpinbox(tk.Spinbox):
    """
    Only send the value when Enter is pressed
    """
    def __init__(self, *args, **kwargs):
        if 'textvariable' in kwargs:
            self.var = kwargs.pop('textvariable')
        tk.Spinbox.__init__(self, *args, **kwargs)
        self.bind('<Return>', self.send)

    def send(self, event):
        self.var.set(self.get())


vtypes = {\
        'bool': tk.IntVar,
        'int': tk.IntVar,
        'float': tk.DoubleVar,
        'str': tk.StringVar,
        }

type_defaults = {\
        'bool': {
            'widget': 'Checkbutton',
            },
        'int': {
            'widget': 'Spinbox',
            },
        'float': {
            'widget': 'Spinbox',
            },
        'str': {
            'widget': 'Label',
            },
        }

widget_defaults = {\
        'Button': {
            'variable': 'textvariable',
            'action': 'send',
            },
        'Checkbutton': {
            'variable': 'variable',
            'onvalue': 1,
            'offvalue': 0,
            },
        'Label': {
            'variable': 'textvariable',
            },
        #'Listbox': {
        #    'variable': 'listvariable',
        #    'options': 'idk',
        #    },
        'Scale': {
            'variable': 'variable',
            'from_': 0.0,
            'to': 1.0,
            },
        'Spinbox': {
            'variable': 'textvariable',
            'from_': 0,
            'to': 100,
            'increment': 1,
            'width': 4,
            },
        'SafeSpinbox': {
            'variable': 'textvariable',
            'from_': 0,
            'to': 100,
            'increment': 1,
            'width': 4,
            }
        }


def parse_widget_def(wdef):
    if 'type' not in wdef:
        wdef['type'] = 'str'
    vtype = wdef['type']

    # copy over type defaults
    for k, v in type_defaults[vtype].iteritems():
        if k not in wdef:
            wdef[k] = v

    # copy over widget defaults
    wtype = wdef['widget']
    for k, v in widget_defaults[wtype].iteritems():
        if k not in wdef:
            wdef[k] = v

    return wdef


def _decode_list(data):
    rv = []
    for item in data:
        if isinstance(item, unicode):
            item = item.encode('utf-8')
        elif isinstance(item, list):
            item = _decode_list(item)
        elif isinstance(item, dict):
            item = _decode_dict(item)
        rv.append(item)
    return rv


def _decode_dict(data):
    rv = {}
    for key, value in data.iteritems():
        if isinstance(key, unicode):
            key = key.encode('utf-8')
        if isinstance(value, unicode):
            value = value.encode('utf-8')
        elif isinstance(value, list):
            value = _decode_list(value)
        elif isinstance(value, dict):
            value = _decode_dict(value)
        rv[key] = value
    return rv


def load_template(fp):
    """ Hack to get rid of unicode strings """
    return json.load(fp, object_hook=_decode_dict)


def read_template(filename):
    try:
        template = load_template(open(filename, 'r'))
    except Exception as E:
        sys.stderr.write("Failed to load template[%s] with %s:" \
                % (filename, E))
        return [], []

    # template should now be a list of widget definitions
    names = []
    wdefs = []
    for wdef in template:
        names.append(wdef.pop('name'))
        wdefs.append(parse_widget_def(wdef))

    return names, wdefs


def make_variables(parent, prefix, names, wdefs):
    # parent.tk.call('info', 'exists', s._name)
    variables = []
    for n, wd in zip(names, wdefs):
        n = prefix + n
        var = find_variable(n, variables)
        if not var:
            var = make_variable(parent, n, wd)
        #if parent.tk.call('info', 'exists', n):
        #    var = find_variable(n, variables)
        #else:
        #    var = make_variable(parent, n, wd)
        variables.append(var)
    return variables


def find_variable(name, variables):
    matches = filter(lambda v: v._name == name, variables)
    if len(matches) == 1:
        return matches[0]
    elif len(matches) == 0:
        return False
    else:
        raise ValueError("More than 1 variable[%s] has name: %s" \
                % (matches, name))


def make_variable(parent, name, wdef):
    return lookup_vtype(wdef)(parent, name=name)


def lookup_vtype(wdef):
    return vtypes[wdef['type']]


def make_widgets(parent, variables, names, wdefs):
    widgets = []
    for v, n, wd in zip(variables, names, wdefs):
        widgets.append(make_label(parent, n))
        widgets.append(make_widget(parent, v, wd))
    return widgets


def make_label(parent, name):
    return tk.Label(parent, text=name)


def wdef_set_variable(wd, v):
    k = wd.pop('variable', None)
    if k is None:
        return wd
    wd[k] = v
    return wd


def make_widget(parent, variable, wdef):
    # remove name, type, widget
    wdef.pop('name', None)
    wdef.pop('type', None)
    widget = wdef.pop('widget', 'Label')
    wdef = wdef_set_variable(wdef, variable)
    func = {
        'Button': TouchButton,
        'Checkbutton': tk.Checkbutton,
        'Label': tk.Label,
        'Scale': tk.Scale,
        'Spinbox': tk.Spinbox,
        'SafeSpinbox': SafeSpinbox
    }.get(widget, None)
    if func is None:
        raise ValueError("Unknown widget: %s" % widget)
    return func(parent, **wdef)


def old_make_widget(parent, variable, wdef):
    wd = wdef.split()[0]
    assert hasattr(tk, wd), "Invalid widget name: %s" % wd
    if wd == 'Scale':
        kwargs = {'variable': variable}
    elif wd == 'Checkbutton':
        kwargs = {'variable': variable, 'onvalue': 1, 'offvalue': 0}
    else:
        kwargs = {'textvariable': variable}
    return getattr(tk, wd)(parent, **kwargs)
