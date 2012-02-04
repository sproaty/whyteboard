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
Contains the sheet manager, which controls Sheet objects. Each sheet is
presented graphically as a tab in a notebook control.
"""

from __future__ import with_statement

import logging

logger = logging.getLogger("whyteboard.core.sheetmanager")

#----------------------------------------------------------------------


class SheetManager(object):
    def __init__(self):
        self.sheets = []
        #self.current_sheet
        
    def count(self):
        """The number of sheets"""
        return len(self.sheets)
        
    def add_sheet(self, sheet):
        """Adds a sheet to the managed sheets"""
        logger.debug("Adding new sheet")
        self.sheets.append(sheet)
         
    def remove_sheet(self, sheet):
        """Removes a sheet from the managed sheets"""
        pass
    
    def get_sheet(self, position):
        """Retrieves the sheet at position"""
        pass
    
    def all_sheets(self):
        return self.sheets
    
    def sheet_name(self, index):
        pass
    
    def current_sheet_name(self):
        pass
    
#----------------------------------------------------------------------

    
class Sheet(object):
    def __init__(self, name=None):        
        self.name = name
        self.shapes = None
        self.size = (800, 600)
        
    def rename(self, new_name):
        self.name = name