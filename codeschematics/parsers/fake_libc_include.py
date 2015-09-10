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

# For now, we only have Linux system commands

from subprocess import check_output, SubprocessError

def find_fake_libc_include():
     # I know that catch-all try statements are bad practice, but... it's basically
     # what I want here
     try:
          lines = check_output(['locate', '-r', '/fake_libc_include$'], universal_newlines=True)
          if not lines:
               print('Warning: "find"ing the whole filesystem for fake includes. Best stop this and pass the'
                     ' location manually or run `sudo updatedb`')
               lines = check_output(['find', '/', '-type', 'd', '-name', "'fake_libc_include'"], universal_newlines=True)
     except SubprocessError as e:
          print('System commands to find the fake libc includes failed (probably because Linux only).'
                " Pass in the folder's location manually.")
          return None
     else:
          lines = lines.splitlines()
          if len(lines) > 1:
               print('Got more than one result, using the first:')
               print(lines)
          line = lines[0]
          return line.strip()
