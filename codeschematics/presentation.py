# This is written to Python 3.3 standards (may use 3.4 features, I haven't kept track)
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
# First the tree data structure. The order of function calls is preserved

from collections import OrderedDict as _OrderedDict
from copy import deepcopy as _deepcopy
_gv = None # Conditional graphviz import to minimize dependencies


class _Tree(_OrderedDict): # The auto-vivifaction was cool, but explicit > implicit
     '''An arbitrary "tree" structure, where "tree" is used loosely. It's halfway
     between a directional graph and an actual tree... arbitrary structure, including
     even loops. All values inserted to the dictionary must also be _Tree()s. Also
     this is a "doubly linked tree", where each node also tracks its parents'''

     def __init__(self, name):
          super().__init__()
          self._parents = _OrderedDict()
          self._name = name

     def __setitem__(self, key, value):
          if not isinstance(value, self.__class__):
               raise TypeError("{0} child values can only be other instances of {0}".format(self.__class__))
          super().__setitem__(key, value)
          value._parents[self._name] = self

     def __reduce_ex__(self, protocol):
          ret = list(super().__reduce_ex__(protocol))
          # The ret[0] is the class/constructor, ret[1] are its args, see pickle docs
          ret[1] = (self.name,) # Even if it wasn't an empty tuple, I can't really handle what it may have been
          return tuple(ret)

     @property
     def name(self):
          return self._name

     # Note: This class is comparison-by-identity only
     __eq__ = lambda self, other: self is other
     __ne__ = lambda self, other: self is not other
     def __hash__(self):
          return hash(id(self))

     def parents(self):
          return self._parents.items()

     def tree_iter(self, visited=None):
          '''Depth first unique traversal of the tree. The starting node isn't yielded'''
          if visited is None:
               visited = set()
          for child in self.values():
               if child not in visited:
                    visited.add(child)
                    yield child
                    yield from child.tree_iter(visited)

     def destroy(self):
          # Destroy our childrens' references to us
          for child in self.values():
               del child._parents[self._name]
          # Destroy our parents' references to us
          for parent in self._parents.values():
               del parent[self._name]
          self._parents.clear()
          self.clear()


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

     # Current data attributes: _data, _tree, and _func_to_node

     ###########################################################################
     # Used for creating copies for the filter methods

     # _copy copies from other to self. This should really only be called during construction/initialization
     def _copy(self, other):
          self._data = other._data.copy()
          self._tree = _deepcopy(other._tree)
          self._func_to_node = {}
          self._recreate_func_to_node(self._tree)

     # When we deep copy the tree, we're making all-new nodes, invalidating the
     # old other._func_to_node
     def _recreate_func_to_node(self, node):
          for call, child in node.items():
               if call in self._func_to_node:
                    if child is not self._func_to_node[call]:
                         raise ValueError('call tree has duplicate nodes for {}'.format(call))
               else:
                    self._func_to_node[call] = child
                    if child.keys():
                         self._recreate_func_to_node(child)

     def deepcopy(self):
          '''Returns a deep copy of the tree, so that you may leave self intact while
          futzing with a duplicate'''
          # Thin wrapper to _copy
          return self.__class__(self)

     ###########################################################################

     def __init__(self, data):
          if isinstance(data, self.__class__):
               self._copy(data)
               return

          # For development at least, type check the input
          for func, calls in data.items():
               if not isinstance(func, str):
                    raise TypeError("function names should be strings (got {}: {} instead)".format(func, type(func)))
               for call in calls:
                    if not isinstance(call, str):
                         raise TypeError("function body calls should be strings (got {}: {} instead)".format(call, type(call)))
                    if calls.count(call) > 1:
                         raise ValueError("function {} has duplicate entries for {}".format(func, call))

          self._data = data
          self._make_tree()


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
          # node to our mapping
          for func, calls in self._data.items():

               if func in func_to_node:       # This function already has a node (i.e. is
                    node = func_to_node[func] # a child of some other function)
               else: # This function doesn't yet exist in the tree
                    parentless.add(func)
                    func_to_node[func] = node = _Tree(func)

               for call in calls:
                    # add call as a child of node
                    if call in func_to_node:
                         node[call] = func_to_node[call]
                         parentless.discard(call) # Silent if call not in parentless
                         # If this call is part of a standalone loop, the entire loop will
                         # eventually be marked as parented, and thus not accessible from
                         # the root node. Fixed below
                    else:
                         func_to_node[call] = node[call] = _Tree(call)

          # We use a root node to host all top level parents
          self._tree = _Tree(None) # Empty name
          for func in parentless:
               self._tree[func] = func_to_node[func]

          # As noted above, standalone loops would be marked as parented yet won't be accessible
          # Manually verify now, by traversing everything and seeing what's missing
          visited = set(self._tree.tree_iter()) | set(self._tree)
          missing = set(func_to_node.values()) - visited
          # The hard part is figuring how many standalone loops there are in missing, and
          # which nodes should be the highest level parents
          while missing:
               new_top_level = self._find_parent(missing.pop()) # set.pop() returns an arbitrary element
               self._tree[new_top_level.name] = new_top_level
               newly_in_tree = set(new_top_level.tree_iter())
               missing -= newly_in_tree

          self._func_to_node = func_to_node


     # Now some _make_tree helper methods

     def _find_parent(self, node):
          # _make_tree helper method: for a given node, finds its "farthest parent"
          # The given node is assumed to be (as yet) independent of self._tree, as part
          # of a standalone loop
          # Since said loop may have children though, we can't assume that every node in
          # the loop would make a suitable parent
          self._max = 0
          self._node = node
          self._find_parent_(node)
          node = self._node
          del self._node
          del self._max
          return node

     def _find_parent_(self, node, visited=None, cur=0):
          # _find_parent recursive method: for a given node, finds its "farthest parent"
          # We assume that if visited is not None, then the current node is already in it
          if visited is None:
               visited = set(node)
          if cur > self._max:
               self._max = cur
               self._node = node
          for _, parent in node.parents():
               if parent not in visited:
                    visited.add(parent)
                    self._find_parent_(parent, visited, cur+1)


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


     def to_plain_text(self, indent='      '):
          """This renders the Presenter object in a simple plain text tree,
             with suitable indentation. It's essentially a "pretty printer"."""

          # The helper method starts with a parent node and traverses the tree depth first
          return '\n'.join(self._to_plain_text(call, indent=indent) for call in self._tree)


     __str__ = to_plain_text


     def to_graphviz(self):
          '''This converts the tree to a format usable by the graphviz library to produce images.
          Call the graphviz_render or its related aliases to actually create the image.
          You needn't call this function first, graphviz_render will do that for you.

          The result is cached on the object in the 'graphviz' attribute.'''
          global _gv
          if _gv is None:
               import graphviz as _gv
          graph = _gv.Digraph(graph_attr={'labelloc': 't', 'labelfontsize': '20'},
                              node_attr={'shape': 'oval', 'color': 'purple', 'style': 'filled',
                                         'fontcolor': 'white'})
          graph.edges((node.name, func) for node in self._tree.tree_iter() for func in node)
          self.graphviz = graph
          return graph

     def graphviz_render(self, format, filename):
          '''Renders the tree via graphviz, writing to "{filename}.{format}"'''
          try:
               graph = self.graphviz
          except AttributeError:
               graph = self.to_graphviz()

          fname = filename + '.' + format
          with open(fname, 'wb') as f:
               f.write(graph.pipe(format))

     # A handy dandy helper to to create shorthand methods for all formats known to graphviz
     # This is a nop if graphviz can't be imported
     try:
          from graphviz.files import FORMATS as _FORMATS
     except ImportError:
          pass
     else:
          for format in _FORMATS:
               format = format.replace('.', '_').replace('-', '_') # Some formats would be syntactically invalid
               exec(
            '''def to_{format}(self, filename):                            \n'''
            '''     " == graphviz_render('{format}', filename)"         \n'''
            '''     return self.graphviz_render('{format}', filename)   \n'''
               .format(format=format) # Kappa
               )

     ###########################################################################
     # Now the filter methods. They return new Presenter instances, suitably
     # modified.
     #
     # The public methods return the modified version, leaving self intact (i.e. immuatable)
     # The private _methods are in place, and violate immutability

     def default_filter(self):
          """This creates a copy of this Presenter instance, except all functions
             lacking a "definition" are deleted from the call tree."""
          out = self.deepcopy()
          out._default_filter()
          return out

     def _default_filter(self):
          all_funcs     = set(self._func_to_node.keys())
          defined_funcs = set(self._data.keys())
          to_be_deleted = all_funcs - defined_funcs

          for func in to_be_deleted:
               try:
                    node = self._func_to_node.pop(func)
               except KeyError:
                    pass
               else:
                    node.destroy()

