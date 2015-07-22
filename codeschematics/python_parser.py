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
to the presentation module.'''


from __future__ import print_function
import ast
import json
from collections import OrderedDict


# An incomplete implementation that only does what I need it to, namely
# append things to it and iterate off it
# So most set methods are unimplemented
class OrderedSet(list):

     def __init__(self, *a, **kw):
          super(self.__class__, self).__init__(*a, **kw)
     
     def append(self, thing):
          if thing not in self:
               super(self.__class__, self).append(thing)
     
     add = append

################################################################################
# Python source --> reduced func-call-tree code
class Data:
     def __init__(self, dic=None):
          self.dict = OrderedDict()
          if dic: self.dict.update(dic)
          self.nested_funcs = set()

# Note: Add class name to methods, and also catch attribute calls
# Note2: Make the former configurable
class Parser(ast.NodeVisitor):

     top_level = '__module__' # The fake name for containing-function of 
                            # top level function calls
     def __init__(self):
          self.data = Data()
          self.data.dict[self.top_level] = OrderedSet()
          self.current_func = self.top_level 
                              # Whatever function whose code we are walking through
               

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

     def uniquify(self, name):
          # This is guaranteed to work for some i, because '.' is disallowed
          # in Python identifiers
          template = name + ".{}"
          i = 1
          out = template.format(i)
          while out in self.data.dict.keys():
               i += 1
               out = template.format(i)
          return out


     def visit_FunctionDef(self, node):
          #print('visiting function def', node.name)
          if node.name in self.data.dict.keys():
               name = self.uniquify(node.name)
          else:
               name = node.name
          self.data.dict[name] = OrderedSet()
          
          if self.current_func != self.top_level:
               self.data.nested_funcs.add(name)
          
          old = self.current_func
          self.current_func = name
          self._generic_visit(node.body)
          self.current_func = old


     def visit_Call(self, node):
          # A function's "name" need not be an identifier, e.g. 
          # for i in mylist:
          #    mylist[i](myargs, mykwargs)
          # For now, if this is the case, then ignore this node
          #print('visiting call node inside function', self.current_func)
          if isinstance(node.func, ast.Name): # simple call by identifier
               self.data.dict[self.current_func].add(node.func.id)
               #print(self.current_func, node.func.id)
          elif isinstance(node.func, ast.Attribute): # call by attribute
               self.data.dict[self.current_func].add(node.func.attr)
               # For now, we ignore whatever object(s) whose attr is the func
               # ignore(node.func.value)            
          self.generic_visit(node)


def parse(filename):
     '''This parses the given file into an abstract syntax tree'''
     with open(filename) as f:
          return ast.parse(f.read(), filename)


def make_call_dict(filename):
     '''This parses the given file into an AST, then traverses the AST to create
     the function definition list. The return value is a tuple of
     (function_def_dict, set_of_nested_funcs), where the latter is the set of
     functions that aren't defined at top level in the module.'''
     tree = parse(filename)
     parser = Parser()
     #print('starting traversal')
     parser.visit(tree)
     return parser.data.dict, parser.data.nested_funcs
