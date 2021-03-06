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
     import warnings
     warnings.warn("pycparserext not found, falling back to pycparser (likely to fail)", ImportWarning)
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
          name = node.name
          if isinstance(name, c_ast.ID):
               self._data.func_called(node.name.name)
          else:
               # The next most common case is struct reference, as e.g. for a stored callback.
               # So isinstance(name, c_ast.StructRef) == True, and `name` has two c_ast.ID
               # children (like a->b). To try and handle more general cases than just a
               # StructRef, we find the textually-latest c_ast.ID node -- i.e. the one
               # furthest down the AST. This should be the text directly left of the
               # opening paren of the function call. Delegate to the helper function for clarity.
               # For example: if our call looks like:
               #
               # val = structptr1->child1.callback(args);
               #
               # Then 'structptr1', 'child1', and 'callback' will all appear as c_ast.ID nodes
               # somewhere in `name.children()`. We want the textually latest, i.e. rightmost
               # name -- 'callback' -- and use that as the "name" of the function.
               retval = self._find_furthest_node(name, c_ast.ID)
               if retval is None:
                    raise ValueError('Got a function call with no ID node')
               self._data.func_called(retval.name)

          self.generic_visit(node)

     def _find_furthest_node(self, startnode, cls):
          for attr, value in reversed(startnode.children()):
               if isinstance(value, cls):
                    return value
               else:
                    self._find_furthest_node(value, cls)
          return None

     def result(self):
          '''After parsing is complete, call this to get the function->subcalls
          dictionary and nested functions set (as a tuple).'''
          return self._data.result()

from codeschematics.parsers.fake_libc_include import find_fake_libc_include
# http://eli.thegreenplace.net/2015/on-parsing-c-type-declarations-and-fake-headers/

def make_call_dict(filename, include_dirs=None, defines=None, *, nostdinc=False):
     '''This parses the given file into an AST, then traverses the AST to create
     the function definition list. The return value is a tuple of
     (function_def_dict, set_of_nested_funcs), where the latter is the set of
     functions that aren't defined at top level in the module.

     This C version of this function passes the given include_dirs and defines
     to the pre-processor; they are merely prefixed with '-I' and '-D' manually,
     and so must be shell-quoted.

     Additionally, if the package can't locate pycparser's fake_libc_include
     files on your system, you will have to pass them to include_dirs, as well
     as set the keyword 'nostdinc' to True.'''
     cpp_args = []
     dname = find_fake_libc_include()
     if dname:
          cpp_args += ['-nostdinc', "-I{}".format(dname)]
     elif nostdinc:
          cpp_args += ['-nostdinc']
     if include_dirs:
          cpp_args += ["-I{}".format(idir) for idir in include_dirs]
     if defines:
          cpp_args += ["-D{}".format(define) for define in defines]
     tree = parse_file(filename, use_cpp=True, cpp_args=cpp_args if cpp_args else '')
     visitor = CTraverser()
     #print('starting traversal')
     visitor.visit(tree)
     return visitor.result()
