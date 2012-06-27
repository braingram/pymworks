This is a pure-python module for reading mworks data files.

Requirements
----

- Numpy (for np.inf and np.nan)
- (optional) pytables (for conversion to hdf5)


Notes
----

LDOBinary.py and ScarabMarshal.py are originally from the mworks/mw_data_tools repo

LDOBinary.py was fixed to actually work and not just throw errors

Currently the ugly method of reading files are


b = open('file.mwk', 'rb')

f = LDOBinary.LDOBinaryUnmarshaler(b)

f.load() # loads first event, most likely the state names

f.load() # load second event, most likely the codec


Events are lists of [code<int>, time<int>, value]

where value can be of any type (including np.inf and np.nan)
