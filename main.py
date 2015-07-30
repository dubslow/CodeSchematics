#! /usr/bin/env python3

from codeschematics.python_parser import make_call_dict
from codeschematics.presentation import Presenter

from sys import argv
from os.path import basename

################################################################################

fname = argv[1]

dic, nested = make_call_dict(fname) # Ignore the nested funcs retval =

tree = Presenter(data)

fname = basename(fname) + '.svg'
tree.to_svg(fname)
