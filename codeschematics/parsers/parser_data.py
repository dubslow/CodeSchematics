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


'''This is a language/parser agnostic helper module that defines common code to be
used with any parser callable from Python that emulates the Python ast module (though
almost certainly most any other parser style can be made to work with this too).

Both the Python.ast-derived parser and the pycparser-derived parser use this class
internally.'''

from __future__ import print_function
from collections import OrderedDict


# An incomplete implementation that only does what I need it to, namely append
# things to it and iterate off it
# So most set methods are unimplemented
# And since it's fundamentally a list, and not hashable, insertion performance may be O(n)
# Perhaps a better name would be UniqueList
class _OrderedSet(list):

     def __init__(self, *a, **kw):
          super(self.__class__, self).__init__(*a, **kw)
     
     def append(self, thing):
          if thing not in self:
               super(self.__class__, self).append(thing)
     
     add = append

################################################################################
# Python/any source --> reduced func-call-tree code

class ParserData(OrderedDict):
     '''A helper class that can by used by at least Python.ast style parsers, and
     very probably many other kinds as well, that tracks and returns the data required
     for the package's purpose.

     It's simple to use: pass a fake top level name to the constructor (I use
     "__module__" for the Python parser), then:
     
     1) When your parser encounters a function definition, call ParserData.parse_func
     with the function's name as the first arg, followed by the function to call
     to continue parsing, and any arguments it requires. (ParserData.parse_func
     has to clean up after parsing a function definition, so control must be returned
     to it by the parser.)

     2) When a function call node is encounted, merely call
     ParserData.func_called(funcname)

     3) When the parser finishes, have it call ParserData.result() to get the
     function->subcalls dictionary (and the set of which functions aren't top level,
     if any)
     '''

     def __init__(self, top_level):
          '''The only argument is the name of the top-level pseudo-function (e.g.
          I used "__module__" as the fake top level name in the Python parser)'''
          super(self.__class__, self).__init__()
          self.top_level = top_level
          self[top_level] = _OrderedSet()
          self.nested_funcs = set()
          self.current_func = top_level

     def _uniquify(self, name):
          '''If 'name' already exists, append a period '.' and an integer to the
          func name, which for any language where periods aren't allowed in func
          names, guarantees a unique name (nop for names that don't exist)'''
          out = name
          template = name + ".{}"
          i = 0
          while out in self.keys():
               i += 1
               out = template.format(i)
          return out

     def parse_func(self, funcname, visitor, *visargs, **kwargs):
          '''When a function definition is encountered, pass this function's name
          and the next function to continue traversing the tree (and said func's
          args).'''
          name = self._uniquify(funcname)
          self[name] = _OrderedSet()
          if self.current_func != self.top_level:
               self.nested_funcs.add(name)

          old = self.current_func
          self.current_func = name
          visitor(*visargs, **kwargs)
          self.current_func = old

     def func_called(self, funcname):
          '''Call this whenever a function call is encountered'''
          self[self.current_func].add(funcname)

     def result(self):
          '''Returns a tuple of (this object as a regular OrderedDict, the set of
          functions whose definitions were not top level)'''
          # Convert the OrderedSet nonsense into a tuple
          dic = OrderedDict( (func, tuple(subcalls)) for func, subcalls in self.items() )
          return dic, self.nested_funcs
