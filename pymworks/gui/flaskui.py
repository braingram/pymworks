#!/usr/bin/env python
"""
"""


import json
import os

import flask

import flask_filetree
import flask_ajaxify

#TODO fix me later
print "Fix this line (flaskui.py:16) ........"
import pymworks


class EventEncoder(json.JSONEncoder):
    """
    Overload jso
    """
    def default(self, obj):
        if isinstance(obj, pymworks.Event):
            return dict(obj)
        return json.JSONEncoder.default(self, obj)


def abs_path(cwd, fn):
    return os.path.join(os.path.dirname(os.path.abspath(cwd)), fn)


def make_client_app(client, app=None):
    if app is None:
        app = flask.Flask('test', \
                template_folder=abs_path(__file__, 'client_templates'), \
                static_folder=abs_path(__file__, 'static'))

    flask_filetree.make_blueprint(app=app, register=True)

    # TODO make events json encodable
    flask_ajaxify.make_blueprint(client, app=app, register=True,
            json_dumps_kwargs=dict(cls=EventEncoder))

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
