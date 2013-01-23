#!/usr/bin/env python
"""
Ajaxify a clientmanager
find the template & static dirs
serve up templates

Request format:
    {
        "func" : function (string)
        "args" : args (json encoded list)
        "kwargs": kwargs (json encoded object/dict)
        "attr" : attribute (string)
    }

if a request has an attr, check that it does NOT have a func
if a request has a func, check that it does NOT have an attr

Return format:
    {
        "status" : 0 (no error, 1 python error, 2 js error)
        "error" : error message (string)
        "result" : variable (json encoded something)
    }
"""


import os

import flask

import flask_filetree
import flask_ajaxify


def abs_path(cwd, fn):
    return os.path.join(os.path.dirname(os.path.abspath(cwd)), fn)


def make_client_app(client, app=None):
    if app is None:
        app = flask.Flask('test', \
                template_folder=abs_path(__file__, 'client_templates'), \
                static_folder=abs_path(__file__, 'static'))

    flask_filetree.make_blueprint(app=app, register=True)

    # TODO make events json encodable
    flask_ajaxify.make_blueprint(client, app=app, register=True)

    @app.route('/')
    def default():
        return flask.render_template('index.html')

    return app


if __name__ == '__main__':
    host = 'localhost'
    port = 19989
    try:
        import qarg
        ns = qarg.get('H(host=localhost,P(port[int=19989')
        host = ns.host
        port = ns.port
    except ImportError:
        pass
    import pymworks
    print "Making client for: %s:%s" % (host, port)
    c = pymworks.io.stream.Client(host, port, autostart=False)
    app = make_client_app(c)
    print "Serving on default: 127.0.0.1:5000"
    app.run()
