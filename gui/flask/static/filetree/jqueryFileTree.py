#
# jQuery File Tree
# Python/Django connector script
# By Martin Skou
#
import os
import urllib

import flask

app = flask.Flask('fileTree')


@app.route('/', methods=['POST'])
def dirlist():
    r = ['<ul class="jqueryFileTree" style="display: none;">']
    try:
        r = ['<ul class="jqueryFileTree" style="display: none;">']
        d = urllib.unquote(flask.request.form.get('dir', './'))
        d = os.path.expanduser(d)
        for f in sorted(os.listdir(d)):
            ff = os.path.join(d, f)
            if os.path.isdir(ff):
                r.append('<li class="directory collapsed">'
                        '<a href="#" rel="%s/">%s</a></li>' % (ff, f))
            else:
                e = os.path.splitext(f)[1][1:]  # get .ext and remove dot
                r.append('<li class="file ext_%s">'
                '<a href="#" rel="%s">%s</a></li>' % (e, ff, f))
        r.append('</ul>')
    except Exception, e:
        r.append('Could not load directory: %s' % str(e))
    r.append('</ul>')
    return ''.join(r)

app.run(debug=True)
