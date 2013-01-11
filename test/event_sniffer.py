#!/usr/bin/env python

import logging
logging.basicConfig(level=logging.DEBUG)

import pymworks

import argparse

description = \
"""
Sniff and record events between a mworks client and server.
Start things in this order: 1) MWorks server 2) Sniffer 3) MWorks client.

This way, the sniffer can create a fake client, connect it to the MWorks
server and then create a fake server for the real MWorks client to connect to.
"""


def parse():
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('-s', '--shost', type=str, default='127.0.0.1', \
            help='ip address of server')
    parser.add_argument('-S', '--sport', type=int, default=19989, \
            help='server port')
    parser.add_argument('-c', '--chost', type=str, default='127.0.0.1', \
            help='ip address for client to connect to')
    parser.add_argument('-C', '--cport', type=int, default=19989, \
            help='client port')
    parser.add_argument('-t', '--timeout', type=float, default=0.001, \
            help='timeout')
    parser.add_argument('-f', '--sfilename', type=str, \
            default='from_server.mwk', \
            help='filename where events from server are written')
    parser.add_argument('-F', '--cfilename', type=str, \
            default='from_client.mwk', \
            help='filename where events from client are written')
    return parser.parse_args()


class Sniffer:
    def __init__(self, server, client, sfilename, cfilename):
        self.client = client
        self.server = server
        logging.debug("Making datafiles")
        self.srec = pymworks.io.datafile.DataFileWriter(sfilename)
        self.crec = pymworks.io.datafile.DataFileWriter(cfilename)

    def update(self):
        r = self.client.read_event(safe=True)
        while r is not None:
            print "from --server--:", r
            self.server.write_event(r)
            self.srec.write_event(r)
            r = self.client.read_event(safe=True)

        r = self.server.read_event(safe=True)
        while r is not None:
            print "from ++client++:", r
            self.client.write_event(r)
            self.crec.write_event(r)
            r = self.server.read_event(safe=True)

    def close(self):
        self.srec.stop()
        self.crec.stop()


def run(args=None):
    # parse command line arguments
    args = parse() if args is None else args

    # connect client to running server
    print "Connecting to server with a client"
    # I use sport, and shost here because we make a client
    # to connect to the server
    c = pymworks.stream.Client(args.shost, args.sport, timeout=args.timeout)

    print "Making fake server and listening fo a client"
    # make 'fake' server
    s = pymworks.stream.Server(args.chost, args.cport, timeout=args.timeout)

    # start native mworks client
    # connect to 'fake' server ip & port

    print "Making sniffer"
    sniffer = Sniffer(s, c, args.sfilename, args.cfilename)
    print "..updating"
    try:
        while True:
            sniffer.update()
    except KeyboardInterrupt:
        sniffer.close()
    except TypeError:  # this is due to the ill-formed termination event
        sniffer.close()
    except EOFError:  # from the server crashing
        sniffer.close()


if __name__ == '__main__':
    run()
