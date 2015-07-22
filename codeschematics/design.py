#! /usr/bin/env python
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


from __future__ import print_function
import ast
from collections import defaultdict, OrderedDict
import json
from pprint import pprint

''' A dirty script to parse and prettily print the function call hierarchy for a
program. As yet, such complications as decorators and annotations are ignored 
(partially for a lack of idea how to deal with them). It's (as yet) unknown how
well this deals with functions returned from other functions/other high-level stuff.
'''

class OrderedDefaultDict(OrderedDict):
     # To create an ordered default dict, one cannot merely subclass both
     # Rather, subclass the hard one and reimplement the easy one
     def __init__(self, default_factory=None, *a, **kw):
          if (default_factory is not None and not callable(default_factory)):
               raise TypeError('first argument must be callable')
          super(self.__class__, self).__init__(self, *a, **kw)
          self.default_factory = default_factory

     def __missing__ (self, key):
          if self.default_factory is None:
               raise KeyError(key)
          self[key] = default = self.default_factory()
          return default

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
# First section is the Python source --> reduced func-call-tree code
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
          # Alternately, generic_visit is equivalent to:
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
     with open(filename) as f:
          return ast.parse(f.read(), filename)


def make_call_dict(filename):
     parser = Parser()
     tree = parse(filename)
     #print('starting traversal')
     parser.visit(tree)
     return parser.data


def load_json(filename):
     with open(filename) as f:
          dic = json.load(f, object_pairs_hook=OrderedDict)
     dic = OrderedDict((func, set(calls)) for func, calls in dic.items())
     return Data(dic)

################################################################################
# Second section is the func-call-tree (language agnostic) --> text and html

# Determining the top level function can be hard -- a simple guess is just
# whatever makes the deepest call tree
def find_deepest_call_chain(dic, chain=None):
     # The arg is a dict of sets, where the key is a function and 
     # the set is the functions called from the key function
     # This is at the moment a brute force make-all-trees and compare method
     if chain == None:
          deepest = 0
          out = None
          for func in dic.keys():
               chain = [func]
               this = find_deepest_call_chain(dic, chain)
               if this > deepest:
                    deepest = this
                    out = func
          #print(deepest)
          return out
     else: # There's a bit of duplication between the top case and recursive case, 
           # but whatever
          func = chain[-1]
          deepest = 0
          for call in dic[func]:
               if call in dic and call not in chain: # avoid endless loops of a->b->a->b etc
                    chain.append(call)
                    this = find_deepest_call_chain(dic, chain)
                    chain.pop()
                    if this > deepest:
                         #print(this, chain)
                         deepest = this
               else: # this chain can go no further
                    this = len(chain)
                    if this > deepest:
                         #print(this, chain)
                         deepest = this
          return deepest               





def Tree(): return OrderedDefaultDict(Tree) # The classic "auto-vivification"


def make_call_tree(data, func, tree=None, chain=None, passed=None):
     if tree is None or chain is None or passed is None:
          tree = Tree()
          chain = []
          passed = set()

     passed.add(func)
     
     
 
     if func not in data.dict.keys():
          tree[func] = None
          return tree, passed

     next = tree[func] # Admissable due to the auto-vivification
     for call in data.dict[func]:
          if call in chain:
               # Allow exactly one duplicate as the tail of the chain
               next[call] = None
               passed.add(call)
               return tree, passed
          else:
               chain.append(call)
               make_call_tree(data, call, next, chain, passed)
               chain.pop()
     return tree, passed
# Still a bug with some last-tier calls randomly disappearing...


def dumps(data, func, ignores, chain=None, prefix='', indent='      '):
     if chain is None:
          chain = []
     if func in ignores:
          return ''
     if func not in data.dict.keys():
          return prefix + func + '()'
     # else:
     out = prefix + func + '():\n'
     strs = []
     for i, call in enumerate(data.dict[func]):
          if call in chain:
               # Allow exactly one duplicate as the tail of the chain
               strs.append(prefix + indent + call + '()')
          else: # no duplicates, continue recursing
               chain.append(call)
               s = dumps(data, call, ignores, chain, prefix+indent)
               if s: # Don't add an entry (i.e. newline) for empty strings
                    strs.append(s)
               chain.pop()
     return out + '\n'.join(strs)

################################################################################
# Miscellanea

def make_pprintable(tree):
     if isinstance(tree, ast.AST):
          node = {key: make_pprintable(getattr(tree, key)) for key in tree._fields}
          node['aaaa'] = tree.__class__.__name__
          return node
     elif isinstance(tree, list):
          return [make_pprintable(thing) for thing in tree]
     else:
          return tree


################################################################################
# main()

if __name__ == '__main__':
#     tree = parse('design.py')
#     pprint(make_pprintable(tree))
     #print(ast.dump(parse('design.py')))\
     #pprint(make_pprintable(parse('design.py')))
     import argparse
     def parse_args():
          parser = argparse.ArgumentParser(conflict_handler='resolve',
                              description='A small (so far) script to'
                              ' analyze Python source files and print function call'
                              ' hierarchies, hopefully facilitating learning new code.')
          parser.add_argument('filename', 
                              help="The Python source file to parse")
          parser.add_argument('-o', '--output', metavar='FILE',
                              help='the base filename for any output files')
          parser.add_argument('-t', '--txt', action='store_true',
                              help='write text to FILE.txt')
          parser.add_argument('-h', '--html', action='store_true', 
                              help='write html to FILE.html')
          
          parser.add_argument('-j', '--json', action='store_true',
                              help='parse a dictionary of function calls from a json file')
          parser.add_argument('-f', '--function', action='append', default=[], nargs='+',
                              help='produce the call tree for only the given function')
          parser.add_argument('-i', '--ignore', action='append', metavar='FUNCTION', default=[], nargs='+',
                              help='ignore (do not output) the given function(s)')
          return parser.parse_args()
     
     def flatten(lst):
          out = []
          for thing in lst:
               if type(thing) == list:
                    for t in flatten(thing):
                         out.append(t)
               else:
                    out.append(thing)
          return out
     
     
     args = parse_args()
          
     if args.json:
          data = load_json(args.filename)
     else:
          data = make_call_dict(args.filename)
     #pprint(data.dict)
     
     if not args.function:
          args.function = [find_deepest_call_chain(data.dict)]
     else:
          args.function = flatten(args.function)
     
     if args.ignore:
          args.ignore = flatten(args.ignore)

     for func in args.function:
          tree, done = make_call_tree(data, func)
          #pprint(tree)
          print('\n' + '#'*80 + '\n')
          print(dumps(data, func, args.ignore))
     
     #data = make_call_dict('design.py')
     #pprint(data.dict)
     #func = find_deepest_call_chain(data.dict)
     #print('\n\n\n\n\n')
     #print(dumps(data, func, args.ignore))

###################################
# Todo:
#   - be able to output the hierarchy above a function (limited to whatever level if any)
#   - limit the depth
#   - disable the full tree for a function in all places its called
#   - make flowchart?
#   - include some optional default funcs to ignore (such as builtins and builtin-type methods)
#   - change order from ordered-by-call-order to order-by-depth-of-node
     
