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

import httplib
import json
import logging
import threading
import time

import flask

from clientmanager import ClientManager

name = 'FlaskMWorks'
host = '127.0.0.1'
port = 5000
# when debug = True, update_thread is launched twice!
debug = True

global updating
updating = False


def make_app(name):
    app = flask.Flask(name)
    cm = ClientManager()

    @app.route('/')
    def hello_world():
        return "Hello World"

    @app.route('/ajax')
    def ajax():
        r = 'Error'
        try:
            print flask.request.args
            q = dict([(k, v) for k, v in flask.request.args.iteritems()])
            for k in q:
                if isinstance(q[k], unicode):
                    q[k] = str(q[k])
            o, r = cm.process_query(**q)
            ret = dict(outcome=o, result=r)
            try:
                return json.dumps(ret)
            except:
                return json.dumps(str(ret))
        except Exception as E:
            return json.dumps('Error: %s' % E)

    @app.route('/launchupdater')
    def launch_updater():
        global updating
        if not updating:
            update_thread(wait=1., initial=2.)
            updating = True
            return "Updater launched"
        return "Updater already running"

    return app


def update():
    try:
        # issue ajax request to server (host, port) of {'function': 'update'}
        url = '/ajax?function=update'
        #print "Connecting to addr: %s, %s" % (host, port)
        conn = httplib.HTTPConnection(host, port)
        #print "Getting url: %s" % url
        conn.request('GET', url)
        r = conn.getresponse()
        if r.status != 200:
            raise ValueError('Status != 200 [%s, %s]' % (r.status, r.reason))
        #print r.status, r.reason
    except KeyboardInterrupt as E:
        raise KeyboardInterrupt
    except Exception as E:
        logging.error('Update failed: %s(%s)' % (type(E), E))


def update_thread(wait=1., initial=None):
    if initial is not None:
        delay = initial
    else:
        update()  # don't run this the first time
        delay = wait
    #print "setting timer for:", time.time() + delay
    threading.Timer(delay, update_thread, [], dict(wait=wait)).start()

if __name__ == '__main__':
    app = make_app(name)
    # if this is called and debug=True, 2 x threads will be started
    #update_thread(wait=1., initial=5.)  # start update thread
    print "---------------- Running App -----------------"
    app.run(host=host, port=port, debug=debug)
