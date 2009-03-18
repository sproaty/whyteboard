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

import wx
import wx.lib.dragscroller

from copy import copy
from tools import Image, Text, Note

#----------------------------------------------------------------------

class Whyteboard(wx.ScrolledWindow):
    """
    The drawing frame of the application.
    """

    def __init__(self, tab):
        """
        Initalise the window, class variables and bind mouse/paint events
        """
        wx.ScrolledWindow.__init__(self, tab, style=wx.CLIP_CHILDREN)
        self.virtual_size = (1000, 1000)
        self.SetVirtualSize(self.virtual_size)
        self.SetScrollRate(20, 20)
        self.SetBackgroundColour("White")
        self.scroller = wx.lib.dragscroller.DragScroller(self)

        self.tab = tab
        self.shapes = []  # list of shapes for re-drawing/saving
        self.shape = None  # selected shape to draw with
        self.undo_list = []
        self.redo_list = []
        self.overlay = wx.Overlay()  # drawing "rubber bands"
        self.drawing = False
        self.zoom = (1.0, 1.0)
        self.select_tool()  # tool ID used to generate Tool object

        self.buffer = wx.EmptyBitmap(*self.virtual_size)
        dc = wx.BufferedDC(None, self.buffer)
        dc.SetBackground(wx.Brush(self.GetBackgroundColour()))
        dc.Clear()

        self.Bind(wx.EVT_SIZE, self.on_size)
        self.Bind(wx.EVT_LEFT_DOWN, self.left_down)
        self.Bind(wx.EVT_LEFT_UP, self.left_up)
        self.Bind(wx.EVT_RIGHT_DOWN, self.right_down)
        self.Bind(wx.EVT_RIGHT_UP, self.right_up)
        self.Bind(wx.EVT_MOTION, self.left_motion)
        self.Bind(wx.EVT_PAINT, self.on_paint)


    def redraw_dirty(self, dc):
        """
        Figure out what part of the window to refresh.
        """
        x1, y1, x2, y2 = dc.GetBoundingBox()
        x1, y1 = self.CalcScrolledPosition(x1, y1)
        x2, y2 = self.CalcScrolledPosition(x2, y2)

        rect = wx.Rect()
        rect.SetTopLeft((x1, y1))
        rect.SetBottomRight((x2, y2))
        rect.Inflate(2, 2)
        self.RefreshRect(rect)


    def redraw_all(self, update_thumb=False):
        """
        Redraws all shapes that have been drawn already.
        """
        dc = wx.BufferedDC(None, self.buffer)
        dc.Clear()

        self.SetBackgroundColour((255, 255, 255))
        for s in self.shapes:
            s.draw(dc, True)
        self.Refresh()
        if update_thumb:
            self.update_thumb()

    def convert_coords(self, event):
        """
        Translate mouse x/y coords to virtual scroll ones.
        """
        newpos = self.CalcUnscrolledPosition(event.GetX(), event.GetY())
        return newpos


    def left_down(self, event):
        """
        Called when the left mouse button is pressed
        Either begins drawing, starts the drawing motion or ends drawing.
        """
        x, y = self.convert_coords(event)
        self.shape.button_down(x, y)

        if not isinstance(self.shape, Text):
            self.drawing = True


    def left_motion(self, event):
        """
        Called when the mouse is in motion.
        """
        if self.drawing:
            x, y = self.convert_coords(event)
            dc = wx.BufferedDC(None, self.buffer)
            self.shape.motion(x, y)
            self.shape.draw(dc)
            self.redraw_dirty(dc)


    def left_up(self, event):
        """
        Called when the left mouse button is released.
        """
        x, y = self.convert_coords(event)

        if self.drawing or isinstance(self.shape, Text):
            before = len(self.shapes)
            self.shape.button_up(x, y)
            after = len(self.shapes)

            if self.tab.GetParent().util.saved:
                self.tab.GetParent().util.saved = False

            # update GUI menus
            if after - before is not 0:
                self.tab.GetParent().update_menus()
                self.select_tool()
                self.update_thumb()
            self.drawing = False


    def right_down(self, event):
        """
        Begin dragging the scroller to move around the panel
        """
        self.scroller.Start(event.GetPosition())

    def right_up(self, event):
        """
        Stop dragging th scroller.
        """
        self.scroller.Stop()


    def select_tool(self, new=None):
        """
        Changes the users' tool (and cursor) they are drawing with. new is an
        int, corresponding to new - 1 = Tool ID in list below.
        Can be called with no new ID to reset itself with the current tool
        """
        if not new:
            new = self.tab.GetParent().util.tool
        else:
            self.tab.GetParent().util.tool = new

        items = self.tab.GetParent().util.items
        colour = self.tab.GetParent().util.colour
        thickness = self.tab.GetParent().util.thickness

        params = [self, colour, thickness]
        self.shape = items[new - 1](*params)  # create new Tool object
        self.SetCursor(wx.StockCursor(self.shape.cursor) )
        self.GetParent().GetParent().control.preview.Refresh()


    def add_shape(self, shape):
        """
        Adds a shape to the "to-draw" list.
        """
        self.shapes.append(shape)
        self.undo_list.append(shape)

        if self.redo_list:
            self.redo_list = []

    def undo(self):
        """
        Undoes an action, and adds it to the redo list.
        """
        shape = self.undo_list.pop()
        self.redo_list.append(shape)

        if isinstance(shape, Note):
            self.undo_note(shape)
            self.shapes.remove(shape)
        elif shape.__class__.__name__ == "list":
            [self.shapes.append(x) for x in shape]
        else:
            self.shapes.remove(shape)

        self.redraw_all(True)


    def redo(self):
        """
        Redoes an action, and adds it to the undo list.
        """
        item = self.redo_list.pop()

        if isinstance(item, Note):
            self.GetParent().GetParent().notes.add_note(item)
            self.shapes.append(item)
        elif item.__class__.__name__ == "list":
            [self.shapes.remove(x) for x in item]
        else:
            self.shapes.append(item)

        self.undo_list.append(item)
        self.redraw_all(True)


    def undo_note(self, note):
        """
        Finds out the passed Note object's element number in the note tree.
        Finds out this Whyteboard's tree ID and iterates over that tree node
        to delete the note item.
        """
        number = 0
        for item in self.shapes:
            if isinstance(item, Note):
                if note == item:
                    break
                number += 1

        # current tab tree element ID
        notes = self.GetParent().GetParent().notes
        tab = notes.tabs[self.get_tab()]
        item, cookie = notes.tree.GetFirstChild(tab)

        x = 0
        while item:
            if x == number:
                notes.tree.Delete(item)
            x += 1
            item, cookie = notes.tree.GetNextChild(tab, cookie)


    def clear(self, keep_images=False):
        """
        Removes all shapes from the "to-draw" list.
        """
        if not keep_images:
            self.undo_list.append(self.shapes)
            self.shapes = []
        else:
            to_remove = []
            images = []

            for x in self.shapes:
                if isinstance(x, Image):
                    images.append(x)
                else:
                    to_remove.append(x)

            self.undo_list.append(to_remove)
            self.shapes = images

        self.redraw_all(update_thumb=True)


    def on_paint(self, event):
        """
        Called when the window is exposed.
        """
        wx.BufferedPaintDC(self, self.buffer, wx.BUFFER_VIRTUAL_AREA)

    def get_tab(self):
        """
        Returns the current tab number of this Whyteboard instance.
        """
        return self.GetParent().GetParent().tabs.GetSelection()

    def update_thumb(self):
        """
        Updates this tab's thumb
        """
        self.GetParent().GetParent().thumbs.update(self.get_tab())

    def on_size(self, event):
        """
        Updates the scrollbars when the window is resized.
        """
        size = self.GetClientSize()
        self.update_scrollbars(size)
        self.redraw_all()


    def update_scrollbars(self, new_size):
        """
        Updates the Whyteboard's scrollbars if the loaded image/text string
        is bigger than the scrollbar's current size.
        """
        width, height = new_size
        if width > self.virtual_size[0]:
            x = width
        else:
            x = self.virtual_size[0]

        if height > self.virtual_size[1]:
            y = height
        else:
            y =  self.virtual_size[1]

        update = False
        #  update the scrollbars and the board's buffer size
        if x > self.virtual_size[0]:
            update = True
        elif y > self.virtual_size[1]:
            update = True

        if update:
            self.virtual_size = (x, y)
            self.SetVirtualSize((x, y))
            self.buffer = wx.EmptyBitmap(*(x, y))
            self.redraw_all()
        else:
            return False

#----------------------------------------------------------------------

if __name__ == '__main__':
    from gui import WhyteboardApp
    app = WhyteboardApp()
    app.MainLoop()
