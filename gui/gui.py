#!/usr/bin/env python
"""
simple packed window with a top panel containing
[+:Button][host:Text][Port:Spin][Load:Button]

Window contains rows, one for each host, constructed by a 
template (see template file)

Need to:
    1) bind variables
    2) construct widgets
    3) handle loop & update
"""

import Tkinter as tk

import pymworks


