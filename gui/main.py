#!/usr/bin/env python

import Tkinter as tk

import clientmodel

clients = [('127.0.0.1', 19989)]


class MainManager(object):
    def __init__(self, root):
        self.root = root
        self.cms = []
        self.cvs = []

    def add_client(self, parent, host, port, template):
        cm = clientmodel.ClientManager(host=host, port=port)
        prefix = str(len(self.cms)) + '_'
        cv = clientmodel.ClientView(cm, parent, \
                prefix=prefix, template_file=template)
        self.cms.append(cm)
        self.cvs.append(cv)

    def update(self, dt):
        [cm.update() for cm in self.cms]
        self.root.after(dt, self.update, dt)

    def start(self, dt=100):
        self.update(dt)


class MainView(object):
    def __init__(self, root, manager):
        self.root = root
        self.manager = manager
        self.make_gui()

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
        self.host.insert(0, '127.0.0.1')
        self.host.pack(side=tk.LEFT)
        tk.Label(p, text='Port:').pack(side=tk.LEFT)
        self.port = tk.Entry(p)
        self.port.insert(0, '19989')
        self.port.pack(side=tk.LEFT)
        tk.Label(p, text='Template:').pack(side=tk.LEFT)
        self.template = tk.Entry(p)
        self.template.insert(0, 'template')
        self.template.pack(side=tk.LEFT)

    def make_client_frame(self):
        self.client_frame = tk.Frame(self.root)
        self.client_frame.pack()

    def add_client(self):
        host, port, template = self.read_client_info()
        self.manager.add_client(self.client_frame, host, port, template)

    def read_client_info(self):
        return self.read_host(), self.read_port(), self.read_template()

    def read_host(self):
        return self.host.get()

    def read_port(self):
        return int(self.port.get())

    def read_template(self):
        return self.template.get()


if __name__ == '__main__':
    root = tk.Tk()
    manager = MainManager(root)
    MainView(root, manager)
    manager.start()
    root.mainloop()
