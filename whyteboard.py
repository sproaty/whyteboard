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
This module contains the Whyteboard class, a window that can be drawn upon. Each
Whyteboard panel gets added to a tab in the GUI, and each Whyteboard maintains
a list of undo/redo actions for itself; thus each Whyteboard tab on the GUI has
its own undo/redo.
"""

import os
import copy
import wx
import wx.lib.dragscroller

from tools import (Image, Text, Line,Note, Select, OverlayShape, TOP_LEFT,
                   TOP_RIGHT, BOTTOM_LEFT, BOTTOM_RIGHT)

#----------------------------------------------------------------------

CANVAS_BORDER = 15  # pixels in size
RIGHT = 1
DIAGONAL = 2
BOTTOM = 3

class Whyteboard(wx.ScrolledWindow):
    """
    The drawing frame of the application.
    """
    def __init__(self, tab, gui):
        """
        Initalise the window, class variables and bind mouse/paint events
        """
        style = wx.NO_FULL_REPAINT_ON_RESIZE | wx.CLIP_CHILDREN
        wx.ScrolledWindow.__init__(self, tab, style=style)
        self.canvas_size = (1000, 1000)
        self.area = (self.canvas_size[0] - 300, self.canvas_size[1] - 300)
        self.SetVirtualSizeHints(2, 2)
        #self.SetClientSize((self.area))
        self.SetVirtualSize(self.canvas_size)
        self.SetScrollRate(1, 1)
        if os.name == "nt":
            self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)  # no flicking on Win!
        self.SetBackgroundColour('Grey')
        self.ClearBackground()

        self.scroller = wx.lib.dragscroller.DragScroller(self)
        self.overlay = wx.Overlay()
        self.gui = gui
        self.tab = tab
        self.shapes = []  # list of shapes for re-drawing/saving
        self.shape = None  # currently selected shape *to draw with*
        self.selected = None  # selected shape *with Select tool*
        self.text  = None  # current Text object for redraw all
        self.copy = None  # BitmapSelect instance
        self.resizing = False
        self.cursor_control = False  # toggle resize canvas cursor on/off
        self.resize_direction = None
        self.undo_list = []
        self.redo_list = []
        self.drawing = False
        self.renamed = False  # used by GUI
        self.select_tool()
        self.buffer = wx.EmptyBitmap(*self.area)

        self.Bind(wx.EVT_SIZE, self.on_size)
        self.Bind(wx.EVT_LEFT_DOWN, self.left_down)
        self.Bind(wx.EVT_LEFT_UP, self.left_up)
        self.Bind(wx.EVT_LEFT_DCLICK, self.left_double)
        self.Bind(wx.EVT_MIDDLE_DOWN, self.middle_down)
        self.Bind(wx.EVT_MIDDLE_UP, self.middle_up)
        self.Bind(wx.EVT_MOTION, self.left_motion)
        self.Bind(wx.EVT_PAINT, self.on_paint)


    def left_down(self, event):
        """Starts drawing"""
        x, y = self.convert_coords(event)
        if self.check_canvas_resize(x, y):  # don't draw outside canvas
            self.resizing = True
            return

        self.shape.left_down(x, y)
        if not isinstance(self.shape, Text):  #  Crashes without the Text check
            self.drawing = True


    def left_motion(self, event):
        """Updates the shape. Indicate shape may be changed using Select tool"""
        x, y = self.convert_coords(event)

        if self.resizing:
            self.resize_canvas((x, y), self.resize_direction)
            return
        else:
            direction = self.check_canvas_resize(x, y)

            if direction:
                if not self.resize_direction:
                    self.resize_direction = direction
                if( not self.cursor_control or direction != self.resize_direction):
                    self.resize_direction = direction
                    self.cursor_control = True
                    self.resize_cursor(direction) # change cursor
                if self.resizing:
                    self.resize_canvas((x, y), direction)

                return
            else:
                if self.cursor_control:
                    self.change_cursor()
                    self.cursor_control = False
                    return

        if self.gui.bar_shown:
            self.gui.SetStatusText(" %s, %s" % (x, y))

        if self.drawing:
            self.shape.motion(x, y)
            self.draw_shape(self.shape)
        elif isinstance(self.shape, Select):

            for shape in reversed(self.shapes):
                res = shape.handle_hit_test(x, y)
                if res and isinstance(shape, Line):
                    self.SetCursor(wx.StockCursor(wx.CURSOR_SIZING))
                    break
                elif res in [TOP_LEFT, BOTTOM_RIGHT]:
                    self.SetCursor(wx.StockCursor(wx.CURSOR_SIZENWSE))
                    break
                elif res in [TOP_RIGHT, BOTTOM_LEFT]:
                    self.SetCursor(wx.StockCursor(wx.CURSOR_SIZENESW))
                    break
                if shape.hit_test(x, y):
                    self.SetCursor(wx.StockCursor(wx.CURSOR_HAND))
                    break
            else:
                self.change_cursor()


    def left_up(self, event):
        """
        Called when the left mouse button is released.
        """
        if self.resizing:
            self.resizing = False
            return
        if self.drawing or isinstance(self.shape, Text):
            before = len(self.shapes)
            self.shape.left_up(*self.convert_coords(event))

            if len(self.shapes) - before:
                self.select_tool()
                self.update_thumb()
            self.drawing = False


    def left_double(self, event):
        """Double click for the Select tool - edit text"""
        x, y = self.convert_coords(event)
        if isinstance(self.shape, Select):
            self.shape.double_click(x, y)


    def check_canvas_resize(self, x, y):
        if x > self.area[0] and y > self.area[1]:
            return DIAGONAL
        elif x > self.area[0]:
            return RIGHT
        elif y > self.area[1]:
            return BOTTOM
        return False


    def resize_cursor(self, direction):
        if direction == DIAGONAL:
            self.SetCursor(wx.StockCursor(wx.CURSOR_SIZENWSE))
        elif direction == RIGHT:
            self.SetCursor(wx.StockCursor(wx.CURSOR_SIZEWE))
        elif direction == BOTTOM:
            self.SetCursor(wx.StockCursor(wx.CURSOR_SIZENS))


    def resize_canvas(self, size, direction=None):
        """ Resizes the canvas. Size = (w, h) tuple """
        if size[0] < 1 or size[1] < 1:
            return

        if direction == RIGHT:
            size = (size[0] + CANVAS_BORDER, self.area[1])
            self.Scroll(size[0], -1)
        elif direction == BOTTOM:
            size = (self.area[0], size[1])
            self.Scroll(-1, size[1] + CANVAS_BORDER)
        else:
            self.Scroll(*size)

        self.buffer = wx.EmptyBitmap(*size)
        self.area = size

        size = (size[0] + CANVAS_BORDER, size[1] + CANVAS_BORDER)
        self.SetVirtualSize(size)
        self.redraw_all()


    def redraw_dirty(self, dc):
        """ Figure out what part of the window to refresh. """
        x1, y1, x2, y2 = dc.GetBoundingBox()
        rect = wx.Rect()
        rect.SetTopLeft(self.CalcScrolledPosition(x1, y1))
        rect.SetBottomRight(self.CalcScrolledPosition(x2, y2))
        self.RefreshRect(rect.Inflate(2, 2))


    def redraw_all(self, update_thumb=False, dc=None):
        """
        Redraws all shapes that have been drawn. self.text is used to show text
        characters as they're being typed, as new Text/Note objects have not
        been added to self.shapes at this point.
        dc is used as the DC for printing.
        """
        if not dc:
            dc = wx.BufferedDC(None, self.buffer)
            dc.Clear()

        for s in self.shapes:
            s.draw(dc, True)
        if self.text:
            self.text.draw(dc, True)
        if self.copy:
            self.copy.draw(dc, True)
        self.Refresh()
        if update_thumb:
            self.update_thumb()


    def select_tool(self, new=None):
        """
        Changes the users' tool (and cursor) they are drawing with. new is an
        int, corresponding to new - 1 = Tool ID in Utility.items
        Can be called with no new ID to reset itself with the current tool
        """
        if not new:
            new = self.gui.util.tool
        else:
            self.gui.util.tool = new

        colour = self.gui.util.colour
        thickness = self.gui.util.thickness
        params = [self, colour, thickness]  # Object constructor parameters
        self.shape = self.gui.util.items[new - 1](*params)  # create new Tool
        self.change_cursor()
        self.gui.control.preview.Refresh()


    def change_cursor(self):
        if isinstance(self.shape.cursor, wx.Cursor):
            self.SetCursor(self.shape.cursor)
        else:
            self.SetCursor(wx.StockCursor(self.shape.cursor) )

    def add_shape(self, shape):
        """ Adds a shape to the "to-draw" list. """
        self.add_undo(shape)
        self.shapes.append(shape)

        if self.selected:
            self.deselect()
            self.redraw_all()
        if self.text:
            self.text = None
        if self.copy:
            self.copy = None
            self.redraw_all()


    def add_undo(self, shape=None):
        """ Creates an undo point """
        l = [copy.copy(x) for x in self.shapes]
        self.undo_list.append(l)

        if self.redo_list:
            self.redo_list = []
        if self.gui.util.saved:
            self.gui.util.saved = False

    def undo(self):
        """ Undoes an action, and adds it to the redo list. """
        self.perform(self.undo_list, self.redo_list)

    def redo(self):
        """ Redoes an action, and adds it to the undo list. """
        self.perform(self.redo_list, self.undo_list)

    def perform(self, list_a, list_b):
        """ list_a: to remove from / list b: append to """
        if not list_a:
            return
        list_b.append(list(self.shapes))
        shapes = list_a.pop()
        self.shapes = shapes
        self.deselect()
        self.redraw_all(True)

        # nicest way to sort the notes out at the moment
        notes = self.gui.notes
        notes.tree.DeleteChildren(notes.tabs[self.gui.tabs.GetSelection()])
        for x in shapes:
            if isinstance(x, Note):
                self.gui.notes.add_note(x)

    def clear(self, keep_images=False):
        """ Removes all shapes from the 'to-draw' list. """
        self.add_undo()
        images = []
        if keep_images:
            for x in self.shapes:
                if isinstance(x, Image):
                    images.append(x)

        self.shapes = images
        self.redraw_all(update_thumb=True)


    def convert_coords(self, event):
        """ Translate mouse x/y coords to virtual scroll ones. """
        return self.CalcUnscrolledPosition(event.GetX(), event.GetY())

    def middle_down(self, event):
        """ Begin dragging the scroller to move around the panel """
        self.SetCursor(wx.StockCursor(wx.CURSOR_SIZENESW))
        self.scroller.Start(event.GetPosition())

    def middle_up(self, event):
        """ Stop dragging the scroller. """
        self.scroller.Stop()
        self.change_cursor()  # bugfix with custom cursor

    def on_paint(self, event=None):
        """ Called when the window is exposed. """
        wx.BufferedPaintDC(self, self.buffer, wx.BUFFER_VIRTUAL_AREA)

    def deselect(self):
        for x in self.shapes:
            if isinstance(x, OverlayShape):
                x.selected = False
        if self.selected:
            self.draw_shape(self.selected, True)
            self.selected = None

    def get_dc(self):
        cdc = wx.ClientDC(self)
        self.PrepareDC(cdc)
        return wx.BufferedDC(cdc, self.buffer, wx.BUFFER_VIRTUAL_AREA)

    def draw_shape(self, shape, replay=False):
        """ Redraws a single shape """
        dc = self.get_dc()
        if replay:
            shape.draw(dc, replay)
        else:
            shape.draw(dc)
        self.redraw_dirty(dc)

    def get_tab(self):
        """ Returns the current tab number of this Whyteboard instance. """
        return self.tab.GetSelection()

    def update_thumb(self):
        """ Updates this tab's thumb """
        self.gui.thumbs.update(self.get_tab())


    def on_size(self, event):
        """ Updates the scrollbars when the window is resized. """
        size = self.GetClientSize()
        self.update_scrollbars(size)
        self.redraw_all()


    def update_scrollbars(self, new_size, ignore_min=False):
        """
        Updates the Whyteboard's scrollbars if the loaded image/text string
        is bigger than the scrollbar's current size.
        Ignore_min is used when the user is resizing the canvas manually
        """
        width, height = new_size
        x, y = width, height
        update = True
        if not ignore_min:
            x = self.canvas_size[0]
            if width > self.canvas_size[0]:
                x = width
            y =  self.canvas_size[1]
            if height > self.canvas_size[1]:
                y = height

            update = False #  update the scrollbars and the board's buffer size
            if x > self.canvas_size[0]:
                update = True
            elif y > self.canvas_size[1]:
                update = True

        if update:
            size = (x + CANVAS_BORDER, y + CANVAS_BORDER)
            self.canvas_size = (size)
            self.buffer = wx.EmptyBitmap(x, y)
            self.SetVirtualSize(size)
            self.area = (x, y)
            #self.SetSize((x, y))
            #self.SetBackgroundColour("Grey")
            #self.ClearBackground()
            self.redraw_all()
        else:
            return False

#----------------------------------------------------------------------

if __name__ == '__main__':
    from gui import WhyteboardApp
    app = WhyteboardApp()
    app.MainLoop()