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
Unit tests for the functionality parts of Whyteboard. Simulates wxPython
with mock classes. Doesn't test the GUI itself (i.e. parts of wx), but parts of
the GUI event handling code (example: undo/redo closing tabs)

Uses mock objects where possible to reduce needing to create the Application
which is an expensive operation. This also makes the tests run quicker
"""

import unittest
import os
import sys
import wx

from whyteboard.test import fakewidgets
from whyteboard.gui import Canvas#, RIGHT, DIAGONAL, BOTTOM
from whyteboard.lib import ConfigObj, Validator, Mock, pub
from whyteboard.misc import meta

import whyteboard.tools as tools
from whyteboard.test.fakewidgets.core import Bitmap, Colour, Event, Notebook


#----------------------------------------------------------------------

def make_shapes(canvas):
    """
    Generates shapes. Needs a Canvas instance to add the shapes to
    """
    params = [canvas, Colour(0, 0, 0), 1]

    for tool in canvas.gui.util.items:
        item = tool(*params)
        item.left_down(5, 6)
        item.left_up(10, 15)


def make_config():
    config = ConfigObj(configspec=meta.config_scheme)
    config.validate(Validator())
    return config


def make_canvas():
    frame = wx.Frame(None)
    frame.util = Mock()
    frame.util.items = tools.items
    frame.util.tool = 1
    frame.util.thickness = 1

    canvas = Mock(wraps=Canvas)
    canvas.gui = frame
    return canvas# Canvas(wx.Notebook(frame), frame, (800, 600))

#----------------------------------------------------------------------

class TestCanvas:
    """
    Tests the Canvas and its functionality
    """
    def __init__(self):
        self.canvas = None
        self.shapes = None

    def setup(self):
        """
        Create a random list of fake Tool objects, excluding Erasers
        The actual values of the shapes don't matter, as they're all
        instanciated to default values of 0
        """
        self.canvas = make_canvas()
        func = lambda shape: self.canvas.add_shape(shape)
        pub.subscribe(func, 'shape.add')

        make_shapes(self.canvas)
        self.shapes = list(self.canvas.shapes)  # value to test changes against


    def test_add(self):
        """
        Adds some shape to the canvas' shape list
        """
        self.canvas.shapes = list()
        shape = whyteboard.tools.Rectangle(self.canvas, (0, 0, 0), 1)
        self.canvas.add_shape(shape)
        assert len(self.canvas.shapes) == 1
        assert len(self.canvas.redo_list) == 0
        assert not self.canvas.gui.util.saved


    def test_change_tool(self):
        """
        User changing tools actually updates the drawing tool
        """
        # This depends on the Tool list order not changing, unlikely from a UI
        # perspective; note: change_tool() called in Whyteboard.__init__
        assert isinstance(self.canvas.shape, whyteboard.tools.Pen)

        self.canvas.change_tool(1)
        assert isinstance(self.canvas.shape, whyteboard.tools.Pen)

        self.canvas.change_tool()
        assert isinstance(self.canvas.shape, whyteboard.tools.Pen)
        self.canvas.change_tool(2)
        assert isinstance(self.canvas.shape, whyteboard.tools.Eraser)

        self.canvas.change_tool()
        assert isinstance(self.canvas.shape, whyteboard.tools.Eraser)


    def test_select_shape(self):
        """Selected shape will now be selected"""
        shape = self.canvas.shapes[3]
        other = self.canvas.shapes[2]
        self.canvas.select_shape(shape)
        assert self.canvas.selected == shape
        assert shape.selected
        self.canvas.select_shape(other)
        assert self.canvas.selected == other
        assert other.selected
        assert not shape.selected


    def test_deselect_shape(self):
        """Previous shape should now be 'deselected'"""
        self.canvas.select_shape(self.canvas.shapes[2])
        self.canvas.deselect_shape()
        assert not self.canvas.selected
        assert not self.canvas.shapes[2].selected


    def test_toggle_transparency(self):
        """Shape's transparency should be toggled on/off"""
        shape = self.canvas.shapes[3]
        self.canvas.select_shape(shape)

        self.canvas.toggle_transparent()
        assert shape.background != RANSPARENT
        self.canvas.toggle_transparent()
        assert shape.background == TRANSPARENT


    def test_resize(self):
        """Canvas should resize diagonally in any size"""
        self.canvas.resize((800, 600))
        assert self.canvas.area == (800, 600)
        self.canvas.resize((200, 300))
        assert self.canvas.area == (200, 300)
        self.canvas.resize((0, 300))
        assert self.canvas.area == (200, 300)
        self.canvas.resize((200, 0))
        assert self.canvas.area == (200, 300)


    def test_resize_right(self):
        """Canvas should not resize in y direction, only x"""
        self.canvas.resize((800, 600))         # given
        self.canvas.resize((900, 400), RIGHT)  # when
        assert self.canvas.area == (900, 600)  # then

    def test_resize_down(self):
        """Canvas should not resize in x direction, only y"""
        self.canvas.resize((800, 600))          # given
        self.canvas.resize((500, 900), BOTTOM)  # when
        assert self.canvas.area == (800, 900)   # then


    def test_undo(self):
        """Undo reverts to previous states"""
        shapes = self.canvas.shapes
        assert len(self.canvas.redo_list) == 0
        self.canvas.undo()
        assert shapes != self.canvas.shapes
        assert len(self.canvas.redo_list) > 0


    def test_redo(self):
        """Redo after undoing restores the state"""
        shapes = self.canvas.shapes
        self.canvas.undo()
        self.canvas.redo()
        assert shapes == self.canvas.shapes
        self.canvas.redo()  # nothing to restore
        assert shapes == self.canvas.shapes
        assert len(self.canvas.redo_list) == 0
        assert len(self.canvas.undo_list) > 0


    def test_clear(self):
        """Clearing the canvas of all shapes"""
        self.canvas.clear()
        assert not self.canvas.shapes
        assert self.canvas.undo_list
        self.canvas.add_shape(whyteboard.tools.Image(self.canvas, Bitmap(None), "C:\picture.jpg"))
        self.canvas.clear()
        assert len(self.canvas.shapes) == 0


    def test_clear_keep_images(self):
        """
        Clearing, asking to keep images without any images existing in the
        list, then add an image and check again
        """
        self.canvas.clear(True)
        assert len(self.canvas.shapes) == 0
        self.canvas.shapes = self.shapes  # restore shapes

        self.canvas.add_shape(whyteboard.tools.Image(self.canvas, Bitmap(None), "C:\picture.jpg"))
        self.canvas.clear(True)
        assert len(self.canvas.shapes) == 1
        assert len(self.canvas.undo_list)


    def test_check_resize_direction(self):
        """Check the correct resize canvas mouse direction is returned"""
        self.canvas.resize((800, 600))
        direction = self.canvas.check_resize_direction(805, 100)
        assert direction == RIGHT
        direction = self.canvas.check_resize_direction(600, 700)
        assert direction == BOTTOM
        direction = self.canvas.check_resize_direction(805, 605)
        assert direction == DIAGONAL


    def test_undo_and_redo_clear(self):
        """
        Clear then undo = state restored. Redo; clear is re-applied = no shapes
        """
        self.canvas.clear()
        self.canvas.undo()
        assert len(self.canvas.shapes) == len(self.shapes), "Shapes should be restored"
        self.canvas.redo()
        assert len(self.canvas.shapes) == 0, "Shapes should be empty"


    def test_move_top(self):
        """shape moves to top"""
        shape = self.canvas.shapes[0]
        top_shape = self.canvas.shapes[3]
        self.canvas.move_top(shape)
        assert self.canvas.shapes[3] == shape, (self.canvas.shapes[3], shape)
        assert self.canvas.shapes[2] == top_shape
        assert not self.canvas.shapes[0] == shape
        self.canvas.move_top(shape)
        assert self.canvas.shapes[3] == shape, (self.canvas.shapes[3], shape)


    def test_move_up(self):
        """shape moves up"""
        shape = self.canvas.shapes[0]
        shape_above = self.canvas.shapes[1]
        self.canvas.move_up(shape)
        assert self.canvas.shapes[1] == shape
        assert self.canvas.shapes[0] == shape_above


    def test_move_down(self):
        """shape moves down"""
        shape = self.canvas.shapes[2]
        shape_below = self.canvas.shapes[1]
        self.canvas.move_down(shape)
        assert self.canvas.shapes[1] == shape
        assert self.canvas.shapes[2] == shape_below


    def test_move_bottom(self):
        """shape moves to the bottom"""
        shape = self.canvas.shapes[3]
        bottom_shape = self.canvas.shapes[0]
        self.canvas.move_bottom(shape)
        assert self.canvas.shapes[0] == shape
        assert self.canvas.shapes[1] == bottom_shape

