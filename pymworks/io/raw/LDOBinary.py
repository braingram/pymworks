""" $Id: LDOBinary.py,v 1.10 2000/03/10 23:07:52 kmacleod Exp $

LDOBinary.py is derived from xml.marshal and pickle

FIXME class instances aren't being revived yet

LDOBinary.py implements the ``Self-Describing Binary Data
Representation'' (LDO-Binary) at <http://casbah.org/Scarab/>.

FIXME ScarabMarshal should be implementing the LDO-Types delegate for
converting types between on-the-wire types and internal types.

"""

import logging

from ScarabMarshal import *
from types import *
import string
import struct
#import numpy as np

MAGIC = "\x89" + "CBF"
MAJOR = 0
MINOR = 0

VERSION = "\x01"

INTEGER_N = "\x02"
INTEGER_P = "\x03"
FLOAT_NN = "\x04"
FLOAT_NP = "\x05"
FLOAT_PN = "\x06"
FLOAT_PP = "\x07"
FLOAT_INF = "\x08"
FLOAT_NAN = "\x09"
OPAQUE = "\x0A"
NULL = "\x0B"
LIST = "\x0C"
DICTIONARY = "\x0D"

DEFINE_REFERENCE = "\x0E"
REFERENCE = "\x0F"

ATTRIBUTES = "\x10"
FLOAT_OPAQUE = "\x11"

TYPE_ATTR = 'type'


class LDOBinaryMarshaler(Marshaler):

    def __init__(self, stream):
        self.written_stream_header = 0
        self.write = stream.write
        self.flush = stream.flush

    def m_init(self):
        if not self.written_stream_header:
            self.written_stream_header = 1
            self.write(MAGIC)
            self.write(VERSION + self.encode_ber(MAJOR) + \
                    self.encode_ber(MINOR))
            logging.debug("%s, m_init: Magic: %s, Version: %s.%s.%s" % \
                    (self, MAGIC, VERSION, MAJOR, MINOR))

    def persistent_id(self, object):
        return None

    def encode_ber(self, d):
        if d < 128:
            return chr(d)
        else:
            d1 = (d & 0x7f)
            d = d >> 7
            return self.encode_ber_high(d) + chr(d1)

    def encode_ber_high(self, d):
        if d < 128:
            return chr(d | 0x80)
        else:
            d1 = (d & 0x7f)
            d = d >> 7
            return self.encode_ber_high(d) + chr(d1 | 0x80)

    def encode_opaque(self, str):
        self.write(OPAQUE + self.encode_ber(len(str)) + str)

    def encode_float_opaque(self, str):
        self.write(FLOAT_OPAQUE + self.encode_ber(len(str)) + str)

    def m_reference(self, object):
        raise NotImplementedError("References are not implemented")
        self.write(REFERENCE + \
                self.encode_ber(string.atoi(dict[str(id(object))])))

    def m_NoneType(self, object):
        self.write(NULL)

    def m_int(self, object):
        if object >= 0:
            self.write(INTEGER_P + self.encode_ber(object))
        else:
            self.write(INTEGER_N + self.encode_ber(-object))

    def m_long(self, object):
        if object >= 0:
            self.write(INTEGER_P + self.encode_ber(object))
        else:
            self.write(INTEGER_N + self.encode_ber(-object))

    def m_float(self, object):
        """
        # TODO: figure out how this differs from a normal opaque
        #raise NotImplemented, "I don't know what an opaque is"
        l = self.decode_ber()
        # how many bytes make up this float
        #print "Float had %i bytes" % l
        char_str = self.read(l)
        if l == 4:
            return struct.unpack('f', char_str)[0]
        elif l == 8:
            return struct.unpack('d', char_str)[0]
        else:
            raise ValueError("Cannot unpack float_opaque with len %s" % l)
        """
        self.encode_float_opaque(struct.pack('d', object))
        #self.encode_opaque(repr(object))

    def m_complex(self, object):
        self.encode_opaque(repr(object))

    def m_str(self, object):
        # the c scarab in mworks expects a null terminated string
        self.encode_opaque(object + '\x00')

    def m_list(self, object):
        self.write(LIST)
        n = len(object)
        self.write(self.encode_ber(n))
        for k in xrange(n):
            self._marshal(object[k])

    def m_tuple(self, object):
        self.m_list(object)

    def m_dict(self, object):
        self.write(DICTIONARY)
        items = object.items()
        n = len(items)
        self.write(self.encode_ber(n))
        for k in xrange(n):
            key, value = items[k]
            self._marshal(key)
            self._marshal(value)

    def m_instance(self, object):
        cls = object.__class__
        module = whichmodule(cls)
        name = cls.__name__
        self.write(ATTRIBUTES + DICTIONARY + self.encode_ber(1))
        # FIXME support LDO-Types
        self._marshal(TYPE_ATTR)
        self._marshal(module + '\n' + name)
        self.write(DICTIONARY)
        try:
            getstate = object.__getstate__
        except AttributeError:
            stuff = object.__dict__
        else:
            stuff = getstate()
        items = stuff.items()
        n = len(items)
        self.write(self.encode_ber(n))
        for k in xrange(n):
            key, value = items[k]
            self._marshal(key)
            self._marshal(value)


class LDOBinaryUnmarshaler(Unmarshaler):

    def __init__(self, stream):
        self.read_stream_header = 0
        self.read = stream.read
        self.memo = {}

    def um_init(self):
        if not self.read_stream_header:
            self.read_stream_header = 1
            m = self.read(len(MAGIC))
            if m == '':
                raise EOFError
            #if self.read(len(MAGIC)) == '':
            #    raise EOFError
            v = self.read(1)
            #if self.read(1) == '':
            #    raise EOFError
            if v == '':
                raise EOFError
            major = self.decode_ber()
            minor = self.decode_ber()
            logging.debug("%s, um_init: Magic: %s, Version: %s.%s.%s" % \
                    (self, m, v, major, minor))

    def _unmarshal(self):
        id = ""
        key = self.read(1)
        if key == '':
            raise EOFError

        if key == DEFINE_REFERENCE:
            raise NotImplementedError("References are not implemented")
            id = str(self.decode_ber())
            key = self.read(1)
            if key == '':
                raise EOFError

        if key == ATTRIBUTES:
            attributes = self._unmarshal()
            # FIXME support LDO-Types
            items = string.split(attributes[TYPE_ATTR], "\n")
            if len(items) != 2:
                raise ValueError("invalid Python class in attributes")
            # FIXME check existence of class too

            module, name = items[0], items[1]
            #klass = self.find_class(module, name)

            key = self.read(1)
            if key == '':
                raise EOFError

        try:
            # print "Dispatching key: %s" % hex(ord(key))
            item = self.um_dispatch[key](self)
        except KeyError:
            raise ValueError("unknown field tag: " + hex(ord(key)))
        if id:
            self.memo[id] = item
        return item

    def decode_ber(self):
        d = 0
        a_byte = self.read(1)
        if a_byte == '':
            raise EOFError
        octet = ord(a_byte)
        while octet & 0x80:
            d = (d << 7) + (octet & 0x7f)
            a_byte = self.read(1)
            if a_byte == '':
                raise EOFError
            octet = ord(a_byte)
        d = (d << 7) + octet
        return d

    um_dispatch = {}

    def um_eof(self):
        raise EOFError
    um_dispatch[''] = um_eof

    def um_int_n(self):
        return(-self.decode_ber())
    um_dispatch[INTEGER_N] = um_int_n

    def um_int_p(self):
        return(self.decode_ber())
    um_dispatch[INTEGER_P] = um_int_p

    def um_float_nn(self):
        mantissa = -self.decode_ber()
        exponent = -self.decode_ber()
        return(string.atof(mantissa + "E" + exponent))
    um_dispatch[FLOAT_NN] = um_float_nn

    def um_float_np(self):
        mantissa = -self.decode_ber()
        exponent = self.decode_ber()
        return(string.atof(mantissa + "E" + exponent))
    um_dispatch[FLOAT_NP] = um_float_np

    def um_float_pn(self):
        mantissa = self.decode_ber()
        exponent = -self.decode_ber()
        return(string.atof(mantissa + "E" + exponent))
    um_dispatch[FLOAT_PN] = um_float_pn

    def um_float_pp(self):
        mantissa = self.decode_ber()
        exponent = self.decode_ber()
        return(string.atof(mantissa + "E" + exponent))
    um_dispatch[FLOAT_PP] = um_float_pp

    def um_float_nan(self):
        #raise NotImplemented, \
        #    "FLOAT_NAN not supported in LDO/Python"
        return float('nan')
    um_dispatch[FLOAT_NAN] = um_float_nan

    def um_float_inf(self):
        #raise NotImplemented, \
        #    "FLOAT_INF not supported in LDO/Python"
        return float('inf')
    um_dispatch[FLOAT_INF] = um_float_inf

    def um_opaque(self):
        l = self.decode_ber()
        return(self.read(l).strip('\x00'))
    um_dispatch[OPAQUE] = um_opaque

    def um_float_opaque(self):
        # TODO: figure out how this differs from a normal opaque
        #raise NotImplemented, "I don't know what an opaque is"
        l = self.decode_ber()
        # how many bytes make up this float
        #print "Float had %i bytes" % l
        char_str = self.read(l)
        if l == 4:
            return struct.unpack('f', char_str)[0]
        elif l == 8:
            return struct.unpack('d', char_str)[0]
        else:
            raise ValueError("Cannot unpack float_opaque with len %s" % l)
        #return(self.read(l).strip('\x00'))
    um_dispatch[FLOAT_OPAQUE] = um_float_opaque

    def um_none(self):
        return(None)
    um_dispatch[NULL] = um_none

    def um_list(self):
        n = self.decode_ber()
        new_list = []
        for ii in xrange(n):
            item = self._unmarshal()
            new_list.append(item)
        return new_list
    um_dispatch[LIST] = um_list

    def um_dict(self):
        n = self.decode_ber()
        d = {}
        for ii in xrange(n):
            item = self._unmarshal()
            key = item
            item = self._unmarshal()
            d[key] = item
        return(d)
    um_dispatch[DICTIONARY] = um_dict

    def um_reference(self):
        d = self.decode_ber()
        return(self.memo[str(d)])
    um_dispatch[REFERENCE] = um_reference

    def find_class(self, module, name):
        env = {}
        try:
            exec 'from %s import %s' % (module, name) in env
        except ImportError:
            raise SystemError("Failed to import class %s from module %s" % \
                (name, module))
        klass = env[name]
        if type(klass) is BuiltinFunctionType:
            raise SystemError(\
                    "Imported object %s from module %s is not a class" % \
                    (name, module))
        return klass

classmap = {}


def whichmodule(cls):
    """Figure out the module in which a class occurs.

    Search sys.modules for the module.
    Cache in classmap.
    Return a module name.
    If the class cannot be found, return __main__.
    """
    if cls in classmap.keys():
        return classmap[cls]
    import sys
    clsname = cls.__name__
    for name, module in sys.modules.items():
        if name != '__main__' and \
            hasattr(module, clsname) and \
            getattr(module, clsname) is cls:
            break
        else:
            name = '__main__'
    classmap[cls] = name
    return name

# Shorthands (credits to and copied from pickle.py)

from StringIO import StringIO


def dump(object, file):
    LDOBinaryMarshaler(file).dump(object)


def dumps(object):
    file = StringIO()
    LDOBinaryMarshaler(file).dump(object)
    return file.getvalue()


def load(file):
    return LDOBinaryUnmarshaler(file).load()


def loads(str):
    file = StringIO(str)
    return LDOBinaryUnmarshaler(file).load()

if __name__ == '__main__':
    runtests(load, loads, dump, dumps)
