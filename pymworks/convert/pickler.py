#!/usr/bin/env python

import logging
import cPickle as pickle


def datafile_to_pickle_data(datafile):
    logging.debug("converting datafile to pickledata: %s" % datafile.filename)
    pdata = {'codec': datafile.codec, 'revCodec': datafile.rcodec, \
            'events': []}
    for e in datafile.get_events():
        pdata['events'].append(dict(code=e.code, time=e.time, \
                value=e.value))
    #            value=json.dumps(e.value)))
    return pdata


def datafile_to_pickle(datafile, filename):
    pdata = datafile_to_pickle_data(datafile)
    logging.debug("Writing pickled data to file: %s" % filename)
    ofile = open(filename, 'w')
    pickle.dump(pdata, ofile, protocol=2)
