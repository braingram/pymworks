#!/usr/bin/env python

import json
import logging
import os
import socket
import sys

import Tkinter as tk

import clientmodel

clients = [('127.0.0.1', 19989)]

defaults = {
        'host': '127.0.0.1',
        'port': 19989,
        'template': 'template',
        'autoconnect': False,
        'clients': [
            ],
        }


def parse_config(filename):
    if os.path.exists(filename):
        try:
            j = json.load(open(filename, 'r'))
        except Exception as E:
            logging.error("Loading %s failed with %s" % (filename, E))
            j = {}
    else:
        j = {}

    for k, v in defaults.iteritems():
        if k not in j:
            j[k] = v

    for ci in xrange(len(j['clients'])):
        for k in ['host', 'port', 'template', 'autoconnect']:
            if k not in j['clients'][ci]:
                j['clients'][ci][k] = j[k]

    return j


def get_defaults(filename='~/.tkmworks'):
    if '~' in filename:
        filename = os.path.expanduser(filename)
    return parse_config(filename)


class MainManager(object):
    def __init__(self, root):
        self.root = root
        self.cms = []
        self.cvs = []

    def add_client(self, parent, host, port, template, timeout=None):
        host = socket.gethostbyname(host)
        try:
            cm = clientmodel.ClientManager(host=host, port=port, timeout=timeout)
            prefix = str(len(self.cms)) + '_'
            cv = clientmodel.ClientView(cm, parent, \
                    prefix=prefix, template_file=template)
            self.cms.append(cm)
            self.cvs.append(cv)
            return True
        except Exception as E:
            print("Couldn't add client %s:%s %s" % (host, port, E))
            return False
        
        
=======
        except Exception as E:
            logging.error(\
                    "Adding client[%s:%s] with template %s failed with %s" % \
                    (host, port, template, E))
>>>>>>> a5eac22c085ed55bb253cddc9e5ce0d0f1e6a4a2

    def update(self, dt):
        [cm.update() for cm in self.cms]
        self.root.after(dt, self.update, dt)

    def start(self, dt=100):
        self.update(dt)


class MainView(object):
    def __init__(self, root, manager):
        self.root = root
        self.manager = manager
        self.defaults = get_defaults()
        self.make_gui()
        self.autoconnect()

    def make_gui(self):
        self.make_controls()
        self.make_client_frame()

    def make_controls(self):
        self.controls_frame = tk.Frame(self.root)
        self.controls_frame.pack()
        p = self.controls_frame
        tk.Button(p, text='Add', command=self.add_client).pack(side=tk.LEFT)
        tk.Label(p, text='Host:').pack(side=tk.LEFT)
        self.host = tk.Entry(p)
        self.host.insert(0, self.defaults['host'])
        self.host.pack(side=tk.LEFT)
        tk.Label(p, text='Port:').pack(side=tk.LEFT)
        self.port = tk.Entry(p)
        self.port.insert(0, self.defaults['port'])
        self.port.pack(side=tk.LEFT)
        tk.Label(p, text='Template:').pack(side=tk.LEFT)
        self.template = tk.Entry(p)
        self.template.insert(0, self.defaults['template'])
        self.template.pack(side=tk.LEFT)

    def make_client_frame(self):
        self.client_frame = tk.Frame(self.root)
        self.client_frame.pack()

    def add_client(self):
        host, port, template = self.read_client_info()
        if self.manager.add_client(self.client_frame, host, port, template, timeout=1.):
            self.set_next_client_info(and_pop=True)
    
    def read_client_info(self):
        return self.read_host(), self.read_port(), self.read_template()

    def read_host(self):
        return self.host.get()

    def read_port(self):
        return int(self.port.get())

    def read_template(self):
        return self.template.get()

    def set_next_client_info(self, and_pop=False):
        if len(self.defaults['clients']):
            c = self.defaults['clients'][0]
            self.host.delete(0, tk.END)
            self.host.insert(0, c['host'])
            self.port.delete(0, tk.END)
            self.port.insert(0, str(c['port']))
            self.template.delete(0, tk.END)
            self.template.insert(0, c['template'])
            if and_pop:
                self.defaults['clients'].pop(0)

    def autoconnect(self):
        acis = []
        for (ci, c) in enumerate(self.defaults['clients']):
            if c['autoconnect']:
                if self.manager.add_client(self.client_frame, \
                        c['host'], c['port'], c['template']):
                    acis.append(ci)

        # remove autoconnected clients
        for ci in acis[::-1]:
            self.defaults['clients'].pop(ci)

        # setup gui for first client
        self.set_next_client_info()


if __name__ == '__main__':
    root = tk.Tk()
    manager = MainManager(root)
    MainView(root, manager)
    manager.start()
    root.mainloop()
