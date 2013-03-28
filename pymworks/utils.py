#!/usr/bin/env python


# get appropriate xml parser
import xml.etree.ElementTree
v = float('.'.join(xml.etree.ElementTree.VERSION.split('.')[:2]))
if v < 1.3:
    from lxml.etree import ElementTree as ETree
else:
    ETree = xml.etree.ElementTree.ElementTree


__all__ = ['ETree']
