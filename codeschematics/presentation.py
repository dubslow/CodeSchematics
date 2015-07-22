# This is written to Python 3 standards (at least 3.2, and possibly 3.3 or 3.4, I'm not really sure)
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


# This is the second half of this package; it takes a dictionary whose keys are function names,
# whose value is a set of function names called by the key-function. The order of the names
# in the set is preserved in the presentation; presumably they are in order of first call
# in the key-function's definition.
#
# Note that this is a simple data structure trivially representable in JSON, and can be
# produced for just about any language one's project is in. That is, this module is
# source language agnostic, it only works with the already-parsed function names


################################################################################
# First some private data structures. The order of function calls is preserved,
# but we also need defaultdict behavior to implement the tree.

from collections import OrderedDict

class _OrderedDefaultDict(OrderedDict):
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


def _Tree(): return _OrderedDefaultDict(_Tree) # The classic "auto-vivification"


################################################################################
# Now the public interface

class Presenter:
     """This is the main class of this module. You provide the function call dictionary
        to its constructor, and call its various methods to understand the call structure
        in various ways.
        
        This class is effectively immutable. The filter methods distill the call
        structure to its more essential forms, as defined by the programmer; they return
        a new Presenter whose underlying data has been suitably pared down.
        
        These filtered Presenters have all the same "view" methods as the "full" original,
        and calling them will produce the requested view."""

     def _copy(self, other):
          self._data = other._data.copy()
          self._tree = other._tree # TODO. HOW THE FUCK DO I COPY A TREE #TODO: experiment with copy.deepcopy
          self._func_to_node = other._func_to_node.copy()


     def __init__(self, data):
          if isinstance(data, type(self)):
               self._copy(other)
               return

          # For development at least, type check the input
          for func, calls in data.items():
               if not isinstance(func, str):
                    raise TypeError("function names should be strings)
               for call in calls:
                    if not isinstance(call, str):
                         raise TypeError("function body calls should be strings")
               if list(set(calls)) != calls:
                    raise ValueError("function {} has duplicate subcall entries".format(func))

          self._data = data
          self._make_tree(data)


     def _make_tree(self):
          self._tree = None
          # "tree" is a very loosely used term here. The data may contain multiple disconnected
          # trees, or a tree with more than one unique root node (i.e. node with no parents),
          # merged branches, or even loops of arbitrary size (i.e. recursion).
          #
          # Start with the first key in the dictionary (an arbitrary but deterministic choice)
          # and simply start adding nodes to the tree. We also create and maintain a secondary
          # dictionary to map each function to its corresponding node, since we don't yet know
          # the structure of the tree
          func_to_node = {}
          parentless = set() # A temp dict to figure out what's top level

          # We process child function calls by 1) adding them to the tree (by merely accessing
          # node[child], since Tree default constructs nodes) and 2) adding the newly created
          # node to our local/temporary mapping
          for func, calls in data.items():

               if func in func_to_node:       # This function already has a node (i.e. is
                    node = func_to_node[func] # a child of some other function)
               else: # This function doesn't yet exist in the tree
                    parentless.add(func)
                    func_to_node[func] = node = Tree()

               for call in calls: # add call as a child of node
                    # This is a pretty mind bending ~~four~~ five lines of code
                    # If the node for this child call already exists, store it in this node
                    # Otherwise, auto-create it by accessing node[call], and store the new
                    # node in func_to_node
                    if call in func_to_node:
                         node[call] = func_to_node[call]
                         parentless.discard(call) # Silent if call not in parentless
                    else:
                         func_to_node[call] = node[call]          

          # We use a "top-er level" root node to host all entries to the tree, if more than one
          if len(parentless) > 1:
               self._tree = Tree()
               for func in parentless:
                    self._tree[func] = func_to_node[func]
          else:
               self._tree = func_to_node[parentless.pop()]
          self._func_to_node = _func_to_node


     ###########################################################################
     # The view methods. For now, we only have a plain text representation.

     def _to_plain_text(self, func, chain=None, prefix='', indent='      '):
          # A simple recursive depth first traversal of the tree. Chain records
          # the call chain for duplicate/recursion detection.
          if chain is None:
               chain = []
          if func not in self._data.keys():
               return prefix + func + '()'
          # else:
          out = prefix + func + '():\n'
          strs = []
          for call in self._func_to_node[func]:
               if call in chain:
                    # Allow exactly one duplicate as the tail of the chain
                    strs.append(prefix + indent + call + '()')
               else: # no duplicates, continue recursing
                    chain.append(call)
                    s = self._to_plain_text(call, chain, prefix+indent)
                    if s: # Don't add an entry (i.e. extra newline) for leaf nodes
                         strs.append(s)
                    chain.pop()
          return out + '\n'.join(strs)


     def to_plain_text(self):
          """This renders the Presenter object in a simple plain text tree,
             with suitable indentation. It's essentially a "pretty printer"."""

          # The helper method starts with a parent node and traverses the tree depth first
          return '\n'.join(self._to_plain_text(call) for call in self._tree)


     __str__ = to_plain_text



     ###########################################################################
     # Now the filter methods. They return new Presenter instances, suitably
     # modified.

     def default_filter(self):
          """This creates a copy of this Presenter instance, except all functions
             lacking a "definition" are deleted from the call tree."""

          result = type(self)(self) # __init__ recognizes its own instances, and copies
                                    # all `self` data to `result` (leaving self intact)

          all_funcs     = set(result._func_to_node.keys())
          defined_funcs = set(result._data.keys())
          to_be_deleted = all_funcs - defined_funcs

          for func in to_be_deleted:
               try:
                    del result._func_to_node[func]
               except KeyError:
                    pass

          # Simpe O(n*m) search and destory algorithm
          # Is it worth it to have the Tree object track its parents as well as
          # its children?
          for node in result._func_to_node.values():
               for func in to_be_deleted:
                    try:
                         del node[func]
                    except KeyError:
                         pass

          return result













