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
Generates the whyteboard.org/latest file that's used by the program to check
for new versions.

It has the format:

version
windows exe zip filename
zip size
source archive filename
source size
"""

import os
import sys

def usage():
    print "USAGE: python write-latest-update-file VERSION [linux/windows/all]"
    sys.exit()
    
def check_file_exists(filename):
    if not os.path.exists(filename):
        print 'ERROR: file [%s] does not exist' % filename
        sys.exit()


def lines_to_write(filetype):
    filename = "whyteboard-%s.%s" % (sys.argv[1], filetype)
    check_file_exists(filename)    
    return [filename, str(os.path.getsize(os.path.abspath(filename)))]


def update_version(current_file, filetype, output, index1, index2):
    for index, line in enumerate(open(current_file)):
        if index == 0:
            continue
        if index == index1:
            line = lines_to_write(filetype)[0]
        if index == index2:
            line = lines_to_write(filetype)[1]
        output.append(line.strip())


if len(sys.argv) <= 2:
    usage()
if not sys.argv[2] in ['linux', 'windows', 'all']:
    usage()
    

current_file = "resources/latest"            
output = [sys.argv[1]]
    
if sys.argv[2] == "windows":    
    update_version(current_file, "zip", output, 1, 2)
    
if sys.argv[2] == "linux":
    update_version(current_file, "tar.gz", output, 3, 4)
    
if sys.argv[2] == "all":
    for filetype in ["zip", "tar.gz"]:
        lines = lines_to_write(filetype)
        output.append(lines[0])
        output.append(lines[1])
    
output = "\n".join(output)     
f = file(current_file, "w")
f.write(output)
f.close()