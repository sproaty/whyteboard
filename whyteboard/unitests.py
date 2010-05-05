#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2009, 2010 by Steven Sproat
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

import os
import time

from lib.configobj import ConfigObj
from lib.validate import Validator
from lib.pubsub import pub

import wx
import fakewidgets
from fakewidgets.core import Bitmap, Event, Colour
import gui
import meta
import whyteboard.tools

from canvas import RIGHT, DIAGONAL, BOTTOM


def make_shapes(canvas):
    """
    Generates shapes. Needs a Canvas instance to add the shapes to
    """
    params = [canvas, Colour(0, 0, 0), 1]

    for tool in canvas.gui.util.items:
        item = tool(*params)
        item.left_down(5, 6)
        item.left_up(10, 15)


class SimpleApp(fakewidgets.core.PySimpleApp):
    """
    Create a GUI instance and create a new canvas reference
    """
    def __init__(self):
        fakewidgets.core.PySimpleApp.__init__(self)

        config = ConfigObj(configspec=meta.config_scheme.split("\n"))
        config.validate(Validator())

        g = gui.GUI(None, config)  # mock the GUI with fake wxPython classes
        self.canvas = g.canvas

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
        self.canvas = SimpleApp().canvas
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
        assert len(self.canvas.redo_list) == 0, "Redo list should be empty"
        assert not self.canvas.gui.util.saved, "Program should be in 'unsaved' state"


    def test_select_tool(self):
        """
        User changing tools actually updates the drawing tool
        """
        # This depends on the Tool list order not changing, unlikely from a UI
        # perspective; note: change_current_tool() called in Whyteboard.__init__

        assert isinstance(self.canvas.shape, whyteboard.tools.Pen)
        self.canvas.change_current_tool(1)  # passing in Pen explicitly
        assert isinstance(self.canvas.shape, whyteboard.tools.Pen)
        self.canvas.change_current_tool()
        assert isinstance(self.canvas.shape, whyteboard.tools.Pen)
        self.canvas.change_current_tool(2)
        assert isinstance(self.canvas.shape, whyteboard.tools.Eraser)
        self.canvas.change_current_tool()
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
        """Previous shape should now be "deselected"""
        self.canvas.select_shape(self.canvas.shapes[2])
        self.canvas.deselect_shape()
        assert not self.canvas.selected
        assert not self.canvas.shapes[2].selected


    def test_toggle_transparency(self):
        """Shape's transparency should be toggled on/off"""
        undo = self.canvas.undo_list
        shape = self.canvas.shapes[3]
        self.canvas.select_shape(shape)

        self.canvas.toggle_transparent()
        assert shape.background != wx.TRANSPARENT
        self.canvas.toggle_transparent()
        assert shape.background == wx.TRANSPARENT


    def test_resize(self):
        """Canvas should resize correctly"""
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


    def test_undo_then_redo(self):
        """
        Undo then redo puts us back in the same state
        """
        [self.canvas.undo() for x in range(4)]
        assert len(self.canvas.shapes) == len(self.shapes) - 4
        [self.canvas.redo() for x in range(4)]
        assert len(self.canvas.shapes) == len(self.shapes)


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
        assert self.canvas.shapes[3] == shape
        assert self.canvas.shapes[2] == top_shape
        assert not self.canvas.shapes[0] == shape
        self.canvas.move_top(shape)
        assert self.canvas.shapes[3] == shape


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

#----------------------------------------------------------------------


class TestGuiFunctionality:
    """
    Bit tricky to do due to some GUI functions firing events and depending upon
    that function call at that time in -that- function call.
    """
    def __init__(self):
        self.canvas = None
        self.gui = None

    def setup(self):
        """
        Add a few mock tabs, each with random shapes
        Currently lacking a faked system that's good enough
        """
        self.canvas = SimpleApp().canvas
        self.gui = self.canvas.gui
        make_shapes(self.canvas)
        shapes = list(self.canvas.shapes)

        for x in range(4):
            self.gui.on_new_tab()
            self.gui.canvas.shapes = list(shapes)

        assert len(self.gui.tabs.pages) == 5, len(self.gui.tabs.pages)


    def test_close_sheet(self):
        """
        A sheet closes correctly
        """
        x = len(self.gui.tabs.pages)
        self.gui.on_close_tab()
        assert len(self.gui.tabs.pages) == x - 1
        self.gui.on_close_tab()
        assert len(self.gui.tabs.pages) == x - 2


    def test_changing_sheets(self):
        """Changing a sheet"""
        evt = Event()
        evt.selection = 2
        self.gui.on_change_tab(evt)
        #assert self.gui.current_tab == 2, self.gui.current_tab
        #evt.selection = 4
        #self.gui.on_change_tab(evt)
        #assert self.gui.current_tab == 4


    def test_undo_closed_sheets(self):
        """Undoing a closed sheet restores its data"""
        assert self.gui.tab_count == 5
        shapes = self.gui.canvas.shapes
        self.gui.on_close_tab()
        assert self.gui.tab_count == 4
        self.gui.on_undo_tab()
        assert self.gui.tab_count == 5
        assert self.gui.canvas.shapes == shapes
        self.gui.on_undo_tab()  # nothing to undo
        assert self.gui.tab_count == 5


    def test_hotkey(self):
        """Hotkey triggers tool change"""
        self.hotkey(115, whyteboard.tools.Select)  # 's'
        self.hotkey(112, whyteboard.tools.Pen)  # 'p'
        self.hotkey(98, whyteboard.tools.BitmapSelect)  # 'b'
        self.hotkey(98, whyteboard.tools.BitmapSelect), "current tool shouldn't have changed"


    def hotkey(self, code, expected):
        evt = Event()
        evt.GetKeyCode = lambda code=code: code
        self.gui.hotkey(evt)
        assert isinstance(self.gui.canvas.shape, expected)


    def test_clear_all(self):
        """Clearing all sheets' shapes"""
        for x in range(self.gui.tab_count):
            canvas = self.gui.tabs.GetPage(x)
            canvas.clear()
            assert not canvas.shapes
            #assert canvas.undo_list

            canvas.add_shape(whyteboard.tools.Image(canvas, Bitmap(None), "C:\picture.jpg"))
            canvas.clear()
            assert len(canvas.shapes) == 0


    def test_clear_all_keep_images(self):
        """Clearing all sheets' shapes while keeping images"""
        shapes = list(self.canvas.shapes)

        for x in range(self.gui.tab_count):
            canvas = self.gui.tabs.GetPage(x)
            canvas.clear(True)
            assert len(canvas.shapes) == 0
            canvas.shapes = list(shapes)  # restore shapes

            canvas.add_shape(whyteboard.tools.Image(canvas, Bitmap(None), "C:\picture.jpg"))
            canvas.clear(True)
            assert len(canvas.shapes) == 1
            assert len(canvas.undo_list)



#    def test_next(self):
#        """change to next sheet"""
#        assert self.gui.current_tab == 5, self.gui.current_tab
#        self.gui.on_next()
#        assert self.gui.current_tab == 5, self.gui.current_tab
#        self.gui.on_next()
#        evt = Event()
#        evt.selection = 0
#        self.gui.on_change_tab(evt)
#        self.gui.on_next()
#        assert self.gui.current_tab == 1, self.gui.current_tab
#
#    def test_prev(self):
#        """change to previous sheet"""
#        assert self.gui.current_tab == 5, self.gui.current_tab
#        self.gui.on_prev()
#        assert self.gui.current_tab == 4, self.gui.current_tab
#        self.gui.on_next()
#        evt = Event()
#        evt.selection = 1
#        self.gui.on_change_tab(evt)
#        self.gui.on_prev()
#        assert self.gui.current_tab == 1, self.gui.current_tab
#        self.gui.on_prev()
#        assert self.gui.current_tab == 0, self.gui.current_tab
#        self.gui.on_prev()
#        assert self.gui.current_tab == 0, self.gui.current_tab
#
#    def test_load_wtbd(self):
#        _file = os.path.join(os.getcwd(), "test.wtbd")
#        assert os.path.exists(_file), _file
#        self.gui.do_open(_file)


#----------------------------------------------------------------------


class TestShapes:
    """
    We want to test shape's functionality, if they respond to their hit tests
    correctly and boundaries. Can probably ignore the math-based ones (?)
    This doesn't depend on the GUI or its classes
    """
    def __init__(self):
        self.canvas = None
        self.gui = None

    def setup(self):
        self.canvas = SimpleApp().canvas
        self.gui = self.canvas.gui


    def test_circle_hit(self):
        """Circle's hit test"""
        circ = whyteboard.tools.Circle(self.canvas, (0, 0, 0), 1)
        circ.radius = 15
        circ.x = 50
        circ.y = 50

        assert circ.hit_test(50, 50)
        assert circ.hit_test(38, 45)
        assert circ.hit_test(36, 45)  # very edge
        assert not circ.hit_test(34, 50)


    def test_ellipse_hit(self):
        """Ellipse hit test"""
        #values from playing with the ellipse itself
        ellipse = whyteboard.tools.Ellipse(self.canvas, (0, 0, 0), 1)
        ellipse.width = 150
        ellipse.height = 152
        ellipse.x = 50
        ellipse.y = 50

        assert ellipse.hit_test(51, 128)  # very edge
        assert ellipse.hit_test(125, 125)
        assert not ellipse.hit_test(46, 73)
        assert not ellipse.hit_test(151, 204)
        assert not ellipse.hit_test(49, 46)


    def test_rect_hit(self):
        """
        Test the rectangle by using different x/y combinations to represent
        the user drawing the rectangle by dragging to different directions
        """
        rect = whyteboard.tools.Rectangle(self.canvas, (0, 0, 0), 1)
        rect.x = 150
        rect.y = 150
        rect.width, rect.height = 50, 50
        rect.update_rect()

        assert rect.hit_test(155, 155)
        assert not rect.hit_test(145, 155)

        rect.width, rect.height = -50, -50
        rect.update_rect()
        assert rect.hit_test(120, 130)
        assert not rect.hit_test(155, 155)

        rect.width, rect.height = 50, -50
        rect.update_rect()
        assert rect.hit_test(165, 130)
        assert not rect.hit_test(140, 155)

        rect.width, rect.height = -50, 50
        rect.update_rect()
        assert rect.hit_test(120, 180)
        assert not rect.hit_test(120, 130)
        assert not rect.hit_test(155, 155)


    def test_image_hit(self):
        """Image hit test"""
        img = whyteboard.tools.Image(self.canvas, Bitmap(None), "C:\picture.jpg")
        img.x = 150
        img.y = 150
        img.image.SetSize(50, 50)
        img.sort_handles()

        assert img.hit_test(160, 160)
        assert img.hit_test(150, 150)
        assert img.hit_test(199, 199)
        assert img.handle_hit_test(149, 149)
        assert img.handle_hit_test(148, 148)
        assert img.handle_hit_test(203, 203)
        assert not img.hit_test(149, 149)
        assert not img.hit_test(201, 201)
        assert not img.handle_hit_test(147, 147)



    def test_text_hit(self):
        """
        Mocking with a fixed text extent (58, 17)
        """
        text = whyteboard.tools.Text(self.canvas, (0, 0, 0), 3)
        text.x = 100
        text.y = 102
        text.text = "blah blah"
        text.find_extent()

        assert text.hit_test(103, 117)
        assert text.hit_test(130, 108)
        assert text.hit_test(154, 114)
        assert not text.hit_test(163, 110)
        assert not text.hit_test(122, 87)
        assert not text.hit_test(95, 117)


    def test_note_hit(self):
        """
        Same as text, with added padding for the background
        """
        note = whyteboard.tools.Note(self.canvas, (0, 0, 0), 3)
        note.x = 100
        note.y = 99
        note.note = "blah blah"
        note.find_extent()

        assert note.hit_test(91, 108)
        assert note.hit_test(130, 91)
        assert note.hit_test(166, 106)
        assert note.hit_test(144, 121)
        assert note.hit_test(126, 111)
        assert not note.hit_test(88, 99)
        assert not note.hit_test(129, 87)
        assert not note.hit_test(168, 106)
        assert not note.hit_test(119, 126)


    def test_line_hit(self):
        """Hit test on a line"""
        line = whyteboard.tools.Line(self.canvas, (0, 0, 0), 1)  # diagonal right
        line.x, line.y = 150, 150
        line.x2, line.y2 = 250, 70

        assert line.hit_test(189, 119)
        assert not line.hit_test(182, 119)
        line.thickness = 10
        assert line.hit_test(178, 119)


    def test_poly_hit(self):
        """Hit test on a polygon"""
        poly = whyteboard.tools.Polygon(self.canvas, (0, 0, 0), 1)
        poly.x, poly.y = 180, 248
        poly.points = [(180.0, 248.0), (319.0, 383.0), (420.0, 110.0)]
        poly.sort_handles()
        assert poly.hit_test(350, 217)
        assert poly.hit_test(204, 256)
        assert not poly.hit_test(373, 255)
        assert not poly.hit_test(183, 231)


    def test_select_tool(self):
        """Select Tool is functioning correctly"""
        select = whyteboard.tools.Select(self.canvas, (0, 0, 0), 1)

        # create some shapes
        rect = whyteboard.tools.Rectangle(self.canvas, (0, 0, 0), 1)
        rect.x = 150
        rect.y = 150
        rect.width, rect.height = 50, 50

        text = whyteboard.tools.Text(self.canvas, (0, 0, 0), 3)
        text.x = 150
        text.y = 150
        text.text = "blah blah"  # 'x' extent of 58
        text.find_extent()

        circle = whyteboard.tools.Circle(self.canvas, (0, 0, 0), 1)
        circle.radius = 25
        circle.x = 250
        circle.y = 250

        # add shapes to canvas, update the shapes for hit testing
        shapes = [rect, text, circle]
        for shape in shapes:
            pub.sendMessage('shape.add', shape=shape)
            shape.sort_handles()

        assert len(self.canvas.shapes) == 3

        # test that one of them is hit
        select.left_down(250, 250)
        assert circle.selected

        # a 'miss' selection should deselect the circle
        select.left_down(550, 550)
        assert not circle.selected

        # test hits on overlapping shapes - topmost shape should 'win'
        select.left_down(155, 155)
        assert text.selected
        assert not rect.selected


#----------------------------------------------------------------------