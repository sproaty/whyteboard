#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2009-2011 by Steven Sproat
#
# GNU General Public Licence (GPL)
#
# Whyteboard is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 3 of the License, or (at your option) any later
# version.
# Whyteboard is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
# You should have received a copy of the GNU General Public License along with
# Whyteboard; if not, write to the Free Software Foundation, Inc., 59 Temple
# Place, Suite 330, Boston, MA  02111-1307  USA


"""
Replaces the version variable definition in meta.py when creating a release!
"""    

import os
import sys

if len(sys.argv) > 2:
    print "USAGE: python update-version.py VERSION"
    sys.exit()
    

print 'Updating meta version'

lines = []
meta = os.path.abspath("../../whyteboard/misc/meta.py")

for line in open(meta):
    if "version =" in line:
        current = line[line.find(" = u") : -1]
        line = line.replace("version" + current, "version = u\"" + sys.argv[1] + "\"")
    lines.append(line)


_file = open(meta, "w")
for item in lines:
  _file.write(item)