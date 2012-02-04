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
Unit tests for the SheetManager and Sheet classes
"""

import unittest

from whyteboard.core import SheetManager, Sheet
from whyteboard.lib.mock import patch, Mock

#----------------------------------------------------------------------

def test_sheet():
   return Sheet("sheet one") 

class TestSheetManager(unittest.TestCase):
    """
    Contains sheets that have been closed and can be restored
    """
    def setUp(self):
        self.manager = SheetManager()

    def test_add_sheet(self):
        # given
        sheet = test_sheet()
        
        # when
        self.manager.add_sheet(sheet)
        
        # then
        self.assertEquals(1, self.manager.count())