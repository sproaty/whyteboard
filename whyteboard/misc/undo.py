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
Classes representing undo actions that can be performed
"""

import os
import wx

from whyteboard.lib import pub

_ = wx.GetTranslation

#----------------------------------------------------------------------

class BaseUndo(object):
    """
    The base undo class.
    """
    def __init__(self, data):
        self.data = data

    def undo(self):
        pass

    def redo(self):
        pass


class ShapeUndo(BaseUndo):
    """
    An action that's performed on a shape, such as change position/size/colour
    """
    def undo(self):
        self.data.undo()

    def redo(self):
        self.data.redo()


class ClearSheetUndo(BaseUndo):
    """
    Restore all shapes after clearing a given a sheet
    """
    def undo(self):
        self.data.undo()

    def redo(self):
        self.data.redo()


class ClearAllSheetUndo(BaseUndo):
    """
    Restores all shapes to each canvas after clearing all sheets
    """
    def undo(self):
        self.data.undo()

    def redo(self):
        self.data.redo()


class CanvasResizeUndo(BaseUndo):
    """
    Restores the canvas to its previous size
    """
    def undo(self):
        self.data.undo()

    def redo(self):
        self.data.redo()


class CanvasRenameUndo(BaseUndo):
    """
    Undo renaming a canvas
    """
    def undo(self):
        self.data.undo()

    def redo(self):
        self.data.redo()