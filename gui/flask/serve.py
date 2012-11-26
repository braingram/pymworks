#!/usr/bin/env python
"""
Serve up mworks events to some sort of web ui.
Listen to one/many server(s) for certain events (NOT ALL)

EventServer (ONLY 1)
    ClientListener (1/Many)

Assume clients are buggy POSs that will fail... often

JS <-> Python protocol is:
    READ/WRITE (host, name, time) : read/write a variable
    LISTEN (host, name) : listen for events of name
    STATE (host) : get current known state of all variables
    CONNECT/DISCONNECT (host)


Example:
    1) start server
    2) receive CONNECT(host)
    3) receive LISTEN(host, name)
    4) receive STATE(host)


JQueryUI
flask
look at collustro for ajax api example?
"""

import json

import flask

from clientmanager import ClientManager

name = 'FlaskMWorks'
app = flask.App(name)
cm = ClientManager()


@app.route('/')
def hello_world():
    return "Hello World"


@app.route('/ajax')
def ajax():
    r = 'Error'
    try:
        o, r = cm.process_query(**flask.request.args)
        try:
            return json.dumps(r)
        except:
            return json.dumps(str(r))
    except:
        return json.dumps('Error')


if __name__ == '__main__':
    # TODO launch an 'updater' process that polls the server every N ms
    app.run()
