#!/usr/bin/env python
"""
Websocket MWClient

Generic (something like ajaxify, for low-level access)

Read
- state (processed like Client)
- codec (? is this necessary ?)
- events (register by name, & fetch from buffer?)
- connected (like generic Stream)
- min/max time?

Write
- events (for value updates)
- command (start/stop experiment etc)
- connect/disconnect/reconnect (like generic Stream)
"""

import json
import logging
logging.basicConfig(level=logging.DEBUG)
import os

import flask
import gevent
import gevent.monkey

from socketio import socketio_manage
from socketio.namespace import BaseNamespace
from socketio.server import SocketIOServer

import werkzeug.serving

import flask_filetree
import flask_mercury
import pymworks


app = flask.Flask('pymworks client')
gevent.monkey.patch_all()


def fnfilter(fn):
    bn = os.path.basename(fn)
    return (len(bn) and bn[0] != '.' and
            os.path.splitext(fn)[1].lower() == '.xml')


def dfilter(d):
    bn = os.path.basename(d)
    return (len(bn) and  bn[0] != '.')


_, app = flask_filetree.make_blueprint(register=True, app=app,
        fnfilter=fnfilter, dfilter=dfilter)
tdir = os.path.realpath('mercury_templates')
store = flask_mercury.storage.FlatfileStore()
_, app = flask_mercury.make_blueprint(register=True, app=app,
        template_dir=tdir, store=store)


@app.route('/', methods=['GET', 'PUT'])
def default():
    # TODO make key flexible (experiment based?)
    key = 'default'
    if flask.request.method == 'GET':
        content = {}
        try:
            content = store.load(key)
        except Exception as E:
            print "failed to load page data: %s" % E

        page = flask.render_template("test_client.html", content=content)
        stext = ""
        for rk in content:
            for si in content[rk]['snippets']:
                skey = '[%s/1]' % si
                snippet = content[rk]['snippets'][si]
                stext = flask.render_template('/snippets/%s/preview.html' \
                        % snippet['name'], data=snippet)
                page = page.replace(skey, stext)
        return page
    else:
        data = json.loads(flask.request.data)
        try:
            store.save(key, data['content'])
        except Exception as E:
            print "failed to save page data: %s" % E
        return flask.jsonify(data)


@app.route('/t/<template>')
def template(template):
    return flask.render_template(template)


class ClientNamespace(BaseNamespace):
    def recv_connect(self):
        self.client = pymworks.io.stream.Client('127.0.0.1', autoconnect=False)
        self.client.register_callback(-1, self.emit_event)  # emit all events

        # start update thread
        def update():
            prev_state = {}
            prev_iostatus = None
            while True:
                if self.client._connected != prev_iostatus:
                    self.emit('iostatus', self.client._connected)
                    prev_iostatus = self.client._connected
                if self.client._connected:
                    # update
                    try:
                        self.client.update()
                    except EOFError:
                        # reached the 'end' of the stream, so... disconnect
                        self.client.disconnect()
                    # check state & codec
                    state = self.client.state
                    try:
                        state['codec'] = self.client.codec
                        if prev_state != state:
                            print 'State:', state
                            self.emit('state', state)
                            prev_state = state.copy()
                    except LookupError:
                        # failed to find codec
                        pass
                gevent.sleep(0.3)

        self.spawn(update)

    def disconnect(self, *args, **kwargs):
        logging.debug("disconnect")
        if hasattr(self, 'client') and self.client._connected:
            self.client.disconnect()
            del self.client
        super(ClientNamespace, self).disconnect(*args, **kwargs)

    def emit_event(self, event):
        logging.debug("emit: %s" % event)
        self.emit('event', dict(event))

    #def on_register(self, key):
    #    logging.debug("register: %s" % key)
    #    if hasattr(self, 'client'):
    #        try:
    #            self.client.register_callback(key, self.emit_event)
    #        except ValueError as E:
    #            self.emit('error', 'failed to register %s, %s' % (key, E))

    def on_event(self, event):
        logging.debug("Event: %s" % event)
        if (not isinstance(event, dict)) or ('key' not in event) or \
                ('value' not in event):
            self.emit('error', 'Invalid event: %s' % event)
            return
        if not hasattr(self, 'client'):
            self.emit('error', 'socket missing client')
            return
        try:
            time = event.get('time', None)
            self.client.write_event(event['key'], event['value'], time)
        except Exception as E:
            self.emit('error', 'Exception [%s] while handling event %s' % \
                    (E, event))

    def on_command(self, command, *args):
        logging.debug("Command: %s, %s" % (command, args))
        if not hasattr(self, 'client'):
            self.emit('error', 'socket missing client')
        # process special commands
        if not hasattr(self.client, command):
            self.emit('error', 'Unknown command: %s, %s' % (command, args))
            return
        try:
            a = getattr(self.client, command)
            if callable(a):
                a(*args)
            else:
                if len(args) != 1:
                    self.emit('error', \
                            'Expected len(args) == 1 for %s, %s' \
                            % (command, args))
                    return
                setattr(self.client, command, args[0])
        except Exception as E:
            self.emit('error', 'Command failed: %s, %s, %s' % \
                    (command, args, E))


@app.route('/socket.io/<path:rest>')
def push_stream(rest):
    try:
        socketio_manage(flask.request.environ,
                {'/client': ClientNamespace}, flask.request)
    except:
        app.logger.error("Exception while handling socketio connection",
                exc_info=True)
    return flask.Response()


def run(host='', port=5000):
    SocketIOServer((host, port), app, resource='socket.io').serve_forever()


@werkzeug.serving.run_with_reloader
def run_dev_server(host='', port=5000):
    app.debug = True
    SocketIOServer((host, port), app, resource='socket.io').serve_forever()


if __name__ == '__main__':
    #run_dev_server()
    run()
