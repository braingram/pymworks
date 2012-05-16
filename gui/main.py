#!/usr/bin/env python

import Tkinter as tk

import clientmodel

clients = [('127.0.0.1', 19989)]


# make root
root = tk.Tk()

# make client frame
cframe = tk.Frame()
cframe.pack()

# make clients & attach updates
cms = []
cvs = []
for client in clients:
    host = client[0]
    port = client[1]
    cm = clientmodel.ClientManager(host=host, port=port)
    cv = clientmodel.ClientView(cm, cframe)
    cms.append(cm)
    cvs.append(cvs)

# attach client updates
def update(cms):
    [cm.update() for cm in cms]
    root.after(100, update, cms)
root.after(100, update, cms)

# run
root.mainloop()
