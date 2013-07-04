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

import glob
import json
import logging
import os
import pickle
import sys
import time

update_pause = 0.3
if len(sys.argv) > 1:
    update_pause = float(sys.argv[1])

fmt = '%(asctime)s|%(levelname)s|%(filename)s|%(funcName)s|%(lineno)d| %(message)s'
fn = os.path.expanduser('~/.pymworks/flask.log')
if not (os.path.exists(os.path.expanduser('~/.pymworks/'))):
    os.makedirs(os.path.expanduser('~/.pymworks/'))
for i in xrange(8, 0, -1):
    ofn = '%s.%i' % (fn, i)
    if os.path.exists(ofn):
        os.rename(ofn, '%s.%i' % (fn, i + 1))
if os.path.exists(fn):
    os.rename(fn, '%s.0' % fn)
print 'logging to file: %s' % fn
logging.basicConfig(level=logging.INFO, filename=fn, filemode='w', format=fmt)

import flask
import gdata
import gdata.spreadsheet.service
import gevent
import gevent.monkey

from socketio import socketio_manage
from socketio.namespace import BaseNamespace
from socketio.server import SocketIOServer

import werkzeug.serving

import flask_filetree
import pymworks


app = flask.Flask('pymworks client')
gevent.monkey.patch_all()

animals_filename = os.path.expanduser('~/.pymworks/colony.p')

gdata_filename = os.path.expanduser('~/.pymworks/gdata.p')
gd = {}
if os.path.exists(gdata_filename):
    with open(gdata_filename, 'r') as f:
        gd = pickle.load(f)


def load_animals():
    a = {}
    if os.path.exists(animals_filename):
        with open(animals_filename, 'r') as f:
            a = pickle.load(f)
    return a


def fnfilter(fn):
    bn = os.path.basename(fn)
    return (len(bn) and bn[0] != '.' and
            os.path.splitext(fn)[1].lower() == '.xml')


def dfilter(d):
    bn = os.path.basename(d)
    return (len(bn) and bn[0] != '.')


_, app = flask_filetree.make_blueprint(
    register=True, app=app,
    fnfilter=fnfilter, dfilter=dfilter)


@app.route('/t/<template>')
def template(template):
    logging.info('loading template: /t/%s' % template)
    return flask.render_template(template)


@app.route('/a/')
def animal_selection():
    # load animals
    animals = load_animals()
    templates = [t for t in flask.current_app.jinja_env.list_templates()
                 if t not in ['animals.html', 'filetree_test.html']]
    logging.info('selecting animal from %s' % animals)
    return flask.render_template(
        "animals.html", animals=animals, templates=templates)


@app.route('/', methods=['GET', 'PUT'])
def default():
    return animal_selection()


@app.route('/a/<animal>')
def select_animal(animal):
    # load animals
    animals = load_animals()
    logging.info('loading animal: /a/%s' % animal)
    if animal in animals:
        cfg = animals[animal]
        if 'animal' not in cfg:
            cfg['animal'] = animal
        t = cfg.get('template', 'behavior.html')
        logging.info('rendering template %s for animal %s with config %s'
                     % (t, animal, cfg))
        return flask.render_template(t, animal=animal, session_config=cfg)
    else:
        logging.error('failed to find animal %s in %s' % (animal, animals))
        return flask.abort(404)


@app.route('/save_animals')
def save_animals():
    s = 'Saved to: %s' % animals_filename
    e = False
    try:
        data = json.loads(flask.request.args['data'])
        with open(animals_filename, 'w') as f:
            pickle.dump(data, f)
    except Exception as E:
        e = True
        s = str(E)
    return flask.jsonify(status=s, error=e)


@app.route('/report')
def report():
    s = 'Reported'
    e = False
    try:
        for k in ('email', 'password'):
            if k not in gd:
                raise ValueError('missing %s in gdata: see %s'
                                 % (k, gdata_filename))
        for k in ('spreadsheet', 'worksheet'):
            if k not in flask.request.args:
                raise ValueError('missing %s in request' % k)
        ss = flask.request.args['spreadsheet']
        ws = flask.request.args['worksheet']
        data = json.loads(flask.request.args['data'])
        for k in data.keys():
            if '_' in k:
                data[k.replace('_', '')] = data.pop(k)
        gdc = gdata.spreadsheet.service.SpreadsheetsService()
        gdc.email = gd['email']
        gdc.password = gd['password']
        gdc.source = 'behavior.pymworks'
        gdc.ProgrammaticLogin()
        # post data
        if ('datetime' not in data):
            data['datetime'] = time.asctime()
        r = gdc.InsertRow(data, ss, ws)
        if not isinstance(r, gdata.spreadsheet.SpreadsheetsList):
            s = 'Report failed: %s' % r
            e = True
    except Exception as E:
        e = True
        s = str(E)
    # also save to disk
    try:
        d = os.path.expanduser('~/.pymworks/reports')
        if not os.path.exists(d):
            os.makedirs(d)
        b = '%s_%s' % (data['animal'], time.strftime('%Y%m%d'))
        n = len(glob.glob(os.path.join(d, b) + '*'))
        bfn = '%s_%i.p' % (b, n)
        fn = os.path.join(d, bfn)
        with open(fn, 'w') as f:
            pickle.dump(data, f)
        logging.info('saved report to: %s' % fn)
    except Exception as E:
        logging.error('Failed to save report to disk: %s' % E)
    return flask.jsonify(status=s, error=e)


class ClientNamespace(BaseNamespace):
    def recv_connect(self):
        self.client = pymworks.io.stream.Client('127.0.0.1', autoconnect=False)
        self.client.register_callback(-1, self.emit_event)  # emit all events

        # start update thread
        def update(pause):
            prev_state = {}
            prev_iostatus = None
            errs = []
            while len(errs) < 3:
                if self.client._connected != prev_iostatus:
                    self.emit('iostatus', self.client._connected)
                    prev_iostatus = self.client._connected
                if self.client._connected:
                    # update
                    try:
                        self.client.update()
                        errs = []
                    except EOFError as E:
                        # reached the 'end' of the stream, so... disconnect
                        logging.error("EOFError encountered: %s" % E)
                        self.emit('error', "EOFError encountered: %s" % E)
                        errs.append(E)
                        #self.client.disconnect()
                    # check state & codec
                    state = self.client.state
                    try:
                        state['codec'] = self.client.codec
                        state['variable groups'] = self.client.variable_groups
                        if prev_state != state:
                            print 'State:', state
                            self.emit('state', state)
                            prev_state = state.copy()
                    except LookupError as E:
                        # failed to find codec
                        logging.error(
                            "Failed to find codec during state update: %s" % E)
                gevent.sleep(pause)
            self.emit('error', 'Too many errors, disconnecting: %s' % errs)

        self.gid = self.spawn(update, update_pause)

    def disconnect(self, *args, **kwargs):
        """This is for disconnecting the entire socket"""
        logging.info("received disconnect from websocket")
        if hasattr(self, 'client') and self.client._connected:
            self.client.disconnect()
        if hasattr(self, 'client'):
            del self.client
        if hasattr(self, 'gid'):
            self.gid.kill()
            del self.gid
        super(ClientNamespace, self).disconnect(*args, **kwargs)

    def emit_event(self, event):
        logging.debug("sending event from websocket: %s" % event)
        self.emit('event', dict(event))

    #def on_register(self, key):
    #    logging.debug("register: %s" % key)
    #    if hasattr(self, 'client'):
    #        try:
    #            self.client.register_callback(key, self.emit_event)
    #        except ValueError as E:
    #            self.emit('error', 'failed to register %s, %s' % (key, E))

    def on_event(self, event):
        logging.debug("received event on websocket: %s" % event)
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
            logging.error('Exception [%s] while handling event %s'
                          % (E, event))
            self.emit('error', 'Exception [%s] while handling event %s' %
                      (E, event))

    def on_command(self, command, *args):
        logging.debug("received command on websocket: %s, %s" %
                      (command, args))
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
                    self.emit('error',
                              'Expected len(args) == 1 for %s, %s'
                              % (command, args))
                    return
                setattr(self.client, command, args[0])
        except Exception as E:
            logging.error('Command failed: %s, %s, %s' %
                          (command, args, E))
            self.emit('error', 'Command failed: %s, %s, %s' %
                      (command, args, E))


@app.route('/socket.io/<path:rest>')
def push_stream(rest):
    try:
        socketio_manage(flask.request.environ,
                        {'/client': ClientNamespace}, flask.request)
    except Exception as E:
        app.logger.error("Exception while handling socketio connection",
                         exc_info=True)
        logging.error("Exception while handling socketio connection: %s"
                      % E)
    return flask.Response()


def run(host='', port=5000):
    logging.info("Running server on %s:%s" % (host, port))
    SocketIOServer((host, port), app, resource='socket.io').serve_forever()


@werkzeug.serving.run_with_reloader
def run_dev_server(host='', port=5000):
    app.debug = True
    SocketIOServer((host, port), app, resource='socket.io').serve_forever()


if __name__ == '__main__':
    #run_dev_server()
    run()
