#! /usr/bin/env python3

from codeschematics.parsers.c_parser import make_call_dict
#from codeschematics.parsers.fake_libc_include import find_fake_libc_include
from codeschematics.presentation import Presenter
from pycparser import c_ast, preprocess_file

from sys import argv
from os.path import basename, join

################################################################################

tox_dir = '/home/bill/qtox/libs/libtoxcore-latest/'
subdir = 'toxcore/'
fname = 'net_crypto.c'

libsodiumdir = '/usr/local/include/'

path = join(tox_dir, subdir)
filepath = join(path, fname)

cpp_args = []
#dname = find_fake_libc_include()
#if dname:
#     cpp_args += ['-nostdinc', "-I{}".format(dname)]
cpp_args.append('-I{}'.format(path))
cpp_args.append('-I{}'.format(libsodiumdir))
#text = preprocess_file(filepath, cpp_args=cpp_args)


#raise Exception
dic, nested = make_call_dict(filepath, include_dirs=[path, libsodiumdir]) # Ignore the nested funcs retval

tree = Presenter(dic)

fname = basename(fname)
tree = tree.default_filter()
tree.to_svg(fname)
