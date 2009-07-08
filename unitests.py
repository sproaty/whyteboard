#!/usr/bin/python

# Copyright (c) 2009 by Steven Sproat
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
"""

import random

import fakewidgets
import tools
import gui


def make_shapes(board):
    """
    Generates random shapes. Needs a Whyteboard instance to add the shapes to
    """
    params = [board, "Black", 1]
    items = board.gui.util.items

    for x in range(20):
        item = items[random.randrange(0, len(items))]
        board.add_shape(item(*params))

class SimpleApp(fakewidgets.core.PySimpleApp):
    """
    Create a GUI instance and create a new
    """
    def __init__(self):
        g = gui.GUI(None)  # mock the GUI, referenced by all
        self.board = g.board
        self.board.Show()

#----------------------------------------------------------------------

class TestWhyteboard:
    """
    Tests the Whyteboard panel and its functionality:
        Undo/redo
        Adding new shapes
        Clearing shapes / undoing/redoing the clearing
    """
    def setup(self):
        """
        Create a random list of fake Tool objects, excluding Erasers
        The actual values of the shapes don't matter, as they're all
        instanciated to default values of 0
        """
        self.board = SimpleApp().board
        make_shapes(self.board)
        self.shapes = list(self.board.shapes)  # value to test changes against

    def add(self, pos=None):
        """
        Add a shape to the list, optionally positional
        """
        shape = tools.Rectangle(self.board, (0, 0, 0), 1)
        if pos:
            self.board.add_shape(shape, pos)
        else:
            self.board.add_shape(shape)
        assert not self.board.redo_list
        assert not self.board.gui.util.saved


    def test_add_shape(self):
        self.add()

    def test_add_positional_shape(self):
        self.add(4)

    def test_select_tool(self):
        """
        This depends on the Tool list order not changing, unlikely from a UI
        perspective; note: select_tool() called in Whyteboard.__init__
        """
        assert isinstance(self.board.shape, tools.Pen)
        self.board.select_tool(1)  # passing in Pen explicitly
        assert isinstance(self.board.shape, tools.Pen)
        self.board.select_tool()
        assert isinstance(self.board.shape, tools.Pen)
        self.board.select_tool(2)
        assert isinstance(self.board.shape, tools.Eraser)
        self.board.select_tool()
        assert isinstance(self.board.shape, tools.Eraser)

    def test_undo_then_redo(self):
        """Test undoing/redoing together"""
        [self.board.undo() for x in range(4)]
        assert len(self.board.shapes) == len(self.shapes) - 4
        [self.board.redo() for x in range(4)]
        assert len(self.board.shapes) == len(self.shapes)

    def test_clear(self):
        self.board.clear()
        assert not self.board.shapes
        assert self.board.undo_list

    def test_clear_keep_images(self):
        """
        Try clearing, asking to keep images without any images existing in the
        list, then add an image and check again
        """
        self.board.clear(True)
        assert not self.board.shapes
        self.board.shapes = self.shapes  # restore shapes

        self.board.add_shape(tools.Image(self.board, (0, 0, 0), 1))
        self.board.clear(True)
        assert self.board.shapes
        assert self.board.undo_list

    def test_undo_and_redo_clear(self):
        """
        Clear then undo = state restored. Redo; clear is re-applied = no shapes
        """
        self.board.clear()
        self.board.undo()
        assert len(self.board.shapes) == len(self.shapes)
        self.board.redo()
        assert len(self.board.shapes) == 0, "Shapes should be empty"


class TestGuiFunctionality:

    def setup(self):
        """
        Add a few mock tabs, each with random shapes
        """
        self.board = SimpleApp().board
        self.gui = self.board.gui
        for x in range(9):
            self.gui.on_new_tab()

            make_shapes(self.board)
        assert len(self.gui.tabs.pages) == 10

    def test_close_tab(self):
        """Currently lacking a faked tab thing that's good enough"""
        x = len(self.gui.tabs.pages)
        #self.gui.on_close_tab()
        #self.gui.on_change_tab()
        #assert len(self.gui.tabs.pages) == x - 1
        #print self.gui.current_tab
        #self.gui.on_close_tab()
        #assert len(self.gui.tabs.pages) == x - 1


class TestShapes:
    """
    We want to test shape's functionality, if they respond to their hit tests
    correctly and boundaries.
    """
    def setup(self):
        self.board = SimpleApp().board
        self.gui = self.board.gui

    def test_circle_hit(self):
        circ = tools.Circle(self.board, (0, 0, 0), 1)
        circ.radius = 15
        circ.x = 50
        circ.y = 50

        assert circ.hit_test(50, 50)
        assert circ.hit_test(38, 45)
        assert circ.hit_test(36, 45)  # very edge
        assert not circ.hit_test(34, 50)

    def test_rect_hit(self):
        r1 =  tools.Rectangle(self.board, (0, 0, 0), 1)
        r2 =  tools.Rectangle(self.board, (0, 0, 0), 1)
        r3 =  tools.Rectangle(self.board, (0, 0, 0), 1)
        r4 =  tools.Rectangle(self.board, (0, 0, 0), 1)
        x, y = 150, 150
        r1.x, r2.x, r3.x, r4.x = x, x, x, x
        r1.y, r2.y, r3.y, r4.y = y, y, y, y

        r1.width, r1.height = 50, 50
        assert r1.hit_test(155, 155)
        assert not r1.hit_test(145, 155)

        r2.width, r2.height = -50, -50
        assert r2.hit_test(120, 130)
        assert not r2.hit_test(155, 155)

        r3.width, r3.height = 50, -50
        assert r3.hit_test(165, 130)
        assert not r3.hit_test(140, 155)

        r4.width, r4.height = -50, 50
        assert r4.hit_test(120, 180)
        assert not r4.hit_test(120, 130)
        assert not r4.hit_test(155, 155)
