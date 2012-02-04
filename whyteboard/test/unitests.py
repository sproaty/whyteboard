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


** NOTE -- July 2011 **

These really need to be re-written to not require so much setup and GUI
stubbing. Using the fake widgets to have to do all this is testing is not good.

I'll slowly be pulling out core program logic functionality from the GUI 
classes and into their own separate things - will lead to an easier to test
program and better code overall.

"""

import os
import wx

import unittest

import whyteboard.test.fakewidgets
import whyteboard.gui.frame as gui
from whyteboard.misc import meta
import whyteboard.tools

from whyteboard.lib import ConfigObj, Mock, pub, Validator
from whyteboard.lib.mock import patch
from whyteboard.gui.canvas import Canvas, RIGHT, DIAGONAL, BOTTOM
from whyteboard.test.fakewidgets.core import Bitmap, Event, Colour, PySimpleApp
from whyteboard.misc import (get_version_int, version_is_greater, get_wx_image_type,
                       get_time, get_image_path, format_bytes, convert_quality)


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
    frame = Mock()
    frame.util = Mock()
    frame.util.tool, frame.util.thickness = 1, 1
    frame.util.items = whyteboard.tools.items

    return Canvas(wx.Notebook(frame), frame, (800, 600))

#----------------------------------------------------------------------

class SimpleApp(PySimpleApp):
    """
    Create a GUI instance and create a new canvas reference
    """
    def __init__(self):
        PySimpleApp.__init__(self)
        g = gui.GUI()  # mock the GUI with fake wxPython classes
        self.canvas = g.canvas

#----------------------------------------------------------------------

class TestCanvas(unittest.TestCase):
    """
    Tests the Canvas and its functionality
    """
    def setUp(self):
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


#    def test_change_tool(self):
#        """
#        User changing tools actually updates the drawing tool
#        """
#        # This depends on the Tool list order not changing, unlikely from a UI
#        # perspective; note: change_tool() called in Whyteboard.__init__
#        assert isinstance(self.canvas.shape, whyteboard.tools.Pen)
#
#        pub.sendMessage('canvas.change_tool')#self.canvas.gui.change_tool(1)
#        self.assertIsInstance(self.canvas.shape, whyteboard.tools.Pen)
#
#        self.canvas.change_tool()
#        assert isinstance(self.canvas.shape, whyteboard.tools.Pen)
#        self.canvas.change_tool(2)
#        assert isinstance(self.canvas.shape, whyteboard.tools.Eraser)
#
#        self.canvas.change_tool()
#        assert isinstance(self.canvas.shape, whyteboard.tools.Eraser)


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
        assert shape.background != wx.TRANSPARENT
        self.canvas.toggle_transparent()
        assert shape.background == wx.TRANSPARENT


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
        top_shape = self.canvas.shapes[-1]
        self.canvas.move_top(shape)
        assert self.canvas.shapes[-1] == shape
        assert self.canvas.shapes[-2] == top_shape
        assert not self.canvas.shapes[0] == shape
        self.canvas.move_top(shape)
        assert self.canvas.shapes[-1] == shape


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

    def test_move_bottom(self):
        """shape moves to the bottom"""
        shape = self.canvas.shapes[3]
        bottom_shape = self.canvas.shapes[0]
        self.canvas.move_bottom(shape)
        assert self.canvas.shapes[0] == shape
        assert self.canvas.shapes[1] == bottom_shape

#----------------------------------------------------------------------


class TestGuiFunctionality:#(unittest.TestCase):
    """
    Bit tricky to do due to some GUI functions firing events and depending upon
    that function call at that time in -that- function call.
    """

    def setUp(self):
        """
        Add a few mock tabs, each with random shapes
        Currently lacking a faked system that's good enough
        """
        self.canvas = make_canvas()
        self.gui = self.canvas.gui
        make_shapes(self.canvas)


    def make_sheets(self):
        shapes = list(self.canvas.shapes)

        for x in range(4):
            self.gui.on_new_tab()
            self.gui.canvas.shapes = list(shapes)

        assert len(self.gui.tabs.pages) == 5


    def test_close_sheet(self):
        """
        A sheet closes correctly
        """
        self.make_sheets()
        x = len(self.gui.tabs.pages)
        self.gui.on_close_tab()
        assert len(self.gui.tabs.pages) == x - 1
        self.gui.on_close_tab()
        assert len(self.gui.tabs.pages) == x - 2


    def test_close_other_sheets_when_first_selected(self):
        self.make_sheets()
        print self.gui.get_tab_names()
        #self.gui.on_close_tab()
        #assert len(self.gui.tabs.pages) == x - 1
        #self.gui.on_close_tab()
        #assert len(self.gui.tabs.pages) == x - 2

    def test_close_other_sheets_when_middle_selected(self):
        self.make_sheets()
        #x = len(self.gui.tabs.pages)
        #self.gui.on_close_tab()
        #assert len(self.gui.tabs.pages) == x - 1
        #self.gui.on_close_tab()
        #assert len(self.gui.tabs.pages) == x - 2
        
    def test_close_other_sheets_when_last_selected(self):
        self.make_sheets()
        #x = len(self.gui.tabs.pages)
        #self.gui.on_close_tab()
        #assert len(self.gui.tabs.pages) == x - 1
        #self.gui.on_close_tab()
        #assert len(self.gui.tabs.pages) == x - 2
                
                
    def test_new_sheet(self):
        """Adding new sheet"""
        canvas = self.gui.canvas
        self.gui.on_new_tab()
        self.gui.on_change_tab()
        #assert self.gui.current_tab == 1
        #assert self.gui.canvas != canvas


    def test_changing_sheets(self):
        """Changing a sheet"""
        self.make_sheets()
        before = self.gui.current_tab
        self.gui.tabs.SetSelection(2)   # this would usually fire an event
        self.gui.on_change_tab() # so call it manually
        assert self.gui.current_tab != before

        before = self.gui.current_tab
        self.gui.tabs.SetSelection(2)
        self.gui.on_change_tab()
        assert self.gui.current_tab == before

        self.gui.tabs.SetSelection(1)
        self.gui.on_change_tab()
        assert self.gui.current_tab == 0
        #print self.gui.thumbs.text[0].GetFontWeight(), self.gui.thumbs.text[1].GetFontWeight(), self.gui.thumbs.text[2].GetFontWeight()
        #assert self.gui.thumbs.text[2].GetFontWeight() == wx.FONTWEIGHT_NORMAL

        #assert self.gui.thumbs.text[2].GetFontWeight() == wx.FONTWEIGHT_BOLD
        #assert self.gui.thumbs.text[1].GetFontWeight() == wx.FONTWEIGHT_NORMAL
         #assert self.gui.current_tab == 2, self.gui.current_tab



    def test_undo_closed_sheets(self):
        """Undoing a closed sheet restores its data"""
        self.make_sheets()
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
        if os.name == "posix":
            self.hotkey(115, whyteboard.tools.Select)  # 's'
            self.hotkey(112, whyteboard.tools.Pen)  # 'p'
            self.hotkey(98, whyteboard.tools.BitmapSelect)  # 'b'
            self.hotkey(98, whyteboard.tools.BitmapSelect), "current tool shouldn't have changed"


    def hotkey(self, code, expected):
        evt = Event()
        evt.GetKeyCode = lambda code = code: code
        self.gui.hotkey(evt)
        assert isinstance(self.gui.canvas.shape, expected)


    def test_clear_all(self):
        """Clearing all sheets' shapes"""
        self.make_sheets()
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
        self.make_sheets()
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


class TestDialogs():
    """
    Again, test code functionality and not too much the GUI itself.
    """
    def setUp(self):
        pass

    def test_save(self):
        pass

#----------------------------------------------------------------------


class TestShapes(unittest.TestCase):
    """
    We want to test shape's functionality, if they respond to their hit tests
    correctly and boundaries.
    """
    def setUp(self):
        self.canvas = Mock()
        self.rect, self.circle, self.text = None, None, None

    def create_canvas(self):
        self.canvas = make_canvas()
        pub.subscribe(self.add, 'shape.add')

    def add(self, shape):
        self.canvas.add_shape(shape)

    def test_save(self):
        rect = whyteboard.tools.Rectangle(self.canvas, (0, 0, 0), 1)
        assert rect.canvas not in [False, None]
        assert rect.brush not in [False, None]
        rect.save()
        assert rect.canvas is None
        assert rect.brush is None


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
        """Rectangle hit test"""
        # using different x/y combinations to mock user drawing the rectangle
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
        """Text tool is hit"""
        # mocking with a fixed text extent (58, 17)
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
        """Note tool is hit"""
        # Same as text, with added padding for the background
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
        
    @patch('whyteboard.gui.panels.Config')
    @patch("whyteboard.misc.utility.wx.CollapsiblePane")
    @patch('whyteboard.misc.utility.wx.TheClipboard')
    @patch('whyteboard.misc.utility.Config')
    def test_select_tool_click_selects(self, util_config, clipboard, collapsilbe_pane, panels_config):
        """Select Tool left click selects a shape"""
        # given
        panels_config.return_value.colour.return_value = [0, 0, 0] 
        self.canvas = SimpleApp().canvas
        select = whyteboard.tools.Select(self.canvas, (0, 0, 0), 1)
        self.make_tools()
        
        # when
        select.left_down(250, 250)
        
        # then
        assert len(self.canvas.shapes) == 3
        assert self.circle.selected


    def test_select_tool_click_deselects(self):
        """Select Tool left click de-selects a shape when no shape is 'hit'"""
        self.canvas = SimpleApp().canvas
        select = whyteboard.tools.Select(self.canvas, (0, 0, 0), 1)
        self.make_tools()
        select.left_down(250, 250)
        assert self.circle.selected
        
        # a 'miss' selection should deselect the circle
        select.left_down(550, 550)
        assert not self.circle.selected


    def test_select_tool_click_selects_shape_overlapping(self):
        """Select Tool left click selects the topmost shape when shapes overlap"""
        self.canvas = SimpleApp().canvas
        select = whyteboard.tools.Select(self.canvas, (0, 0, 0), 1)
        self.make_tools()
        select.left_down(250, 250)

        select.left_down(155, 155)
        assert self.text.selected
        assert not self.rect.selected

        self.canvas.deselect_shape()
        self.canvas.move_top(self.rect)  # new top shape

        select.left_down(155, 155)
        assert self.rect.selected
        assert not self.text.selected


    def make_tools(self):
        # create some shapes
        self.rect = whyteboard.tools.Rectangle(self.canvas, (0, 0, 0), 1)
        self.rect.x = 150
        self.rect.y = 150
        self.rect.width, self.rect.height = 50, 50

        self.text = whyteboard.tools.Text(self.canvas, (0, 0, 0), 3)
        self.text.x = 150
        self.text.y = 150
        self.text.text = "blah blah"  # 'x' extent of 58
        self.text.find_extent()

        self.circle = whyteboard.tools.Circle(self.canvas, (0, 0, 0), 1)
        self.circle.radius = 25
        self.circle.x = 250
        self.circle.y = 250

        # add shapes to canvas, update the shapes for hit testing
        shapes = [self.rect, self.text, self.circle]
        for shape in shapes:
            pub.sendMessage('shape.add', shape=shape)
            shape.sort_handles()