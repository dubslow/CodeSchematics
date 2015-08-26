# This file is written to be Python 2 and 3 compatible
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


# This is one of hopefully many more to come first stage of the code schematics
# package, parsing Python code into a list of function definitions and the 
# function calls in those definitions.

'''This module uses the builtin Python ast module to parse a given filename and
produce a list of function definitions and their subcalls suitable for passing
to the presentation module. It builds on the parser/language agnostic ParserData
class, which encapsulates the logic required for this package.'''

from __future__ import print_function
import ast
from codeschematics.parsers.parser_data import ParserData

# Note: Add class name to methods, and also catch attribute calls
# Note2: Make the former configurable
class PythonParser(ast.NodeVisitor):

     top_level = '__module__' # The fake name for containing-function of 
                            # top level function calls
     def __init__(self):
          self._data = ParserData(self.top_level)

     def _generic_visit(self, thing): 
          # Like super's visit, except also accepts the list "nodes" as well
          # Alternately, super().generic_visit is equivalent to:
          # def generic_visit(self, node):
          #      for field, value in iter_fields(node):
          #           self._generic_visit(value)
          if isinstance(thing, list):
               for thng in thing:
                    if isinstance(thng, ast.AST):
                         self.visit(thng)
          elif isinstance(thing, ast.AST):
               self.visit(thing)

     def visit_FunctionDef(self, node):
          self._data.parse_func(node.name, self._generic_visit, node.body)

     def visit_Call(self, node):
          # A function's "name" need not be an identifier, e.g. 
          # for i in mylist:
          #    mylist[i](myargs, mykwargs)
          # For now, if this is the case, then ignore this node
          #print('visiting call node inside function', self.current_func)
          if isinstance(node.func, ast.Name): # simple call by identifier
               self._data.func_called(node.func.id)
               #print(self.current_func, node.func.id)
          elif isinstance(node.func, ast.Attribute): # call by attribute
               self._data.func_called(node.func.attr)
               # For now, we ignore whatever object(s) whose attr is the func
               # ignore(node.func.value)            
          self.generic_visit(node)

     def result(self):
          '''After parsing is complete, call this to get the function->subcalls
          dictionary and nested functions set (as a tuple).'''
          return self._data.result()


def parse_file(filename):
     '''This parses the given file into an abstract syntax tree'''
     with open(filename) as f:
          return ast.parse(f.read(), filename)


def make_call_dict(filename):
     '''This parses the given file into an AST, then traverses the AST to create
     the function definition list. The return value is a tuple of
     (function_def_dict, set_of_nested_funcs), where the latter is the set of
     functions that aren't defined at top level in the module.'''
     tree = parse_file(filename)
     parser = PythonParser()
     #print('starting traversal')
     parser.visit(tree)
     return parser.result()
