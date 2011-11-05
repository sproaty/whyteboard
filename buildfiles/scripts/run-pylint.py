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
Outputs pylint report to a text file.
"""

import glob
import os

baseDir = os.path.abspath("../whyteboard")

dirsToCheck = ["core", "gui", "misc", "test", "updater"]
for dir in dirsToCheck:
    print os.path.join(baseDir, dir)
directories = [glob.glob(os.path.join(baseDir, directory))[0] for directory in dirsToCheck]

disableMessages = ["C0103", "C0111", "C0301", "R0902", 
                   "R0904", "W0104", "W0141", "W0221",  
                   "W0232", "W0613", "W0704"]

for directory in directories:
    for _file in glob.glob(directory + "/*.py"):           
        print 'Running pylint on: ' + _file
        flags = " --disable=".join(disableMessages)
        args = "pylint --disable=%s %s >> pylint-report.txt" % (flags, _file)
        os.system(args) 