# Note: tab depth is 5, as a personal preference


#    Copyright (C) 2014-2015 Bill Winslow
#
#    This module is a part of the CodeSchematics package.
#
#    This program is libre software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
#    See the LICENSE file for more details.


# The second parser for my "parse-a-program-and-diagram-its-design" lib

'''This module uses the pycparser package to parse a given C file and
produce a list of defined functions and their subcalls suitable for passing
to the codeschematics.presentation module.'''

from __future__ import print_function

from pycparser import c_ast, preprocess_file, parse_file as _parse_file
from codeschematics.parsers.parser_data import ParserData

try:
     from pycparserext.ext_c_parser import GnuCParser
except ImportError:
     from warnings import ImportWarning
     raise ImportWarning("pycparserext not found, falling back to pycparser (likely to fail)")
     parse_file = _parse_file
else:
     from functools import partial as _partial
     parser = GnuCParser()
     parse_file = _partial(_parse_file, parser=parser)
# Basically parse_file should dynamically use GnuCParser when available, or
# silently fallback if not

class CTraverser(c_ast.NodeVisitor):

     top_level = '__file__' # The fake name for containing-function of 
                            # top level function calls
     def __init__(self):
          self._data = ParserData(self.top_level)

     def visit_FuncDef(self, node):
          # For now, we assume that function name is unique (i.e. no overloading),
          # so ignore param types and return type
          self._data.parse_func(node.decl.name, self.generic_visit, node)

     def visit_FuncCall(self, node):
          self._data.func_called(node.name.name)            
          self.generic_visit(node)

     def result(self):
          '''After parsing is complete, call this to get the function->subcalls
          dictionary and nested functions set (as a tuple).'''
          return self._data.result()

def make_call_dict(filename):
     '''This parses the given file into an AST, then traverses the AST to create
     the function definition list. The return value is a tuple of
     (function_def_dict, set_of_nested_funcs), where the latter is the set of
     functions that aren't defined at top level in the module.'''
     tree = parse_file(filename, use_cpp=True)
     visitor = CTraverser()
     #print('starting traversal')
     visitor.visit(tree)
     return visitor.result()
