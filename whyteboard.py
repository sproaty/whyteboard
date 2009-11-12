# -*- coding: utf-8 -*-
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

The canvas to be drawn on is managed by a buffer bitmap, and the rest of the
area is flooded with a grey, to indicate it is the background. This background
can be grabbed with the mouse to resize the canvas' size. If the canvas is
larger than the client size, then scrollbars are displayed, and a slight
"border" is shown around the canvas - this can be grabbed to resize.
"""

import os
import copy
import wx
import wx.lib.dragscroller

from tools import (Image, Text, Line, Note, Select, OverlayShape, TOP_LEFT,
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

        self.area = (gui.util.config['default_width'], gui.util.config['default_height'])#(640, 480)
        self.SetVirtualSizeHints(2, 2)
        self.SetScrollRate(1, 1)
        self.SetBackgroundColour('Grey')
        if os.name == "nt":
            self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)  # no flicking on Win!
        if os.name == "posix":
            self.ClearBackground()

        self.scroller = wx.lib.dragscroller.DragScroller(self)
        self.overlay = wx.Overlay()
        self.buffer = wx.EmptyBitmap(*self.area)
        self.gui = gui
        self.tab = tab
        self.scale = (1.0, 1.0)
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
        self.select_tool()
        self.redraw_all()

        self.Bind(wx.EVT_SIZE, self.on_size)
        self.Bind(wx.EVT_LEFT_DOWN, self.left_down)
        self.Bind(wx.EVT_LEFT_UP, self.left_up)
        self.Bind(wx.EVT_RIGHT_UP, self.right_up)
        self.Bind(wx.EVT_LEFT_DCLICK, self.left_double)
        self.Bind(wx.EVT_MIDDLE_DOWN, self.middle_down)
        self.Bind(wx.EVT_MIDDLE_UP, self.middle_up)
        self.Bind(wx.EVT_MOTION, self.left_motion)
        self.Bind(wx.EVT_PAINT, self.on_paint)


    def left_down(self, event):
        """Starts drawing"""
        x, y = self.convert_coords(event)
        if os.name == "nt":
            self.CaptureMouse()
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

            if not self.drawing and direction:
                if not self.resize_direction:
                    self.resize_direction = direction
                if( not self.cursor_control or direction != self.resize_direction):
                    self.resize_direction = direction
                    self.cursor_control = True
                    self.resize_cursor(direction) # change cursor
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
        elif isinstance(self.shape, Select):  # change cursor to indicate action
            for shape in reversed(self.shapes):
                res = shape.handle_hit_test(x, y)
                if res and isinstance(shape, Line):
                    self.SetCursor(wx.StockCursor(wx.CURSOR_SIZING))
                    break
                if res and isinstance(shape, Image):
                    img = wx.Image(os.path.join(self.gui.util.get_path(), "images",
                                                "cursors", "") + "rotate.png")
                    self.SetCursor(wx.CursorFromImage(img))
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
        if os.name == "nt":
            if self.HasCapture():
                self.ReleaseMouse()
        if self.resizing:
            self.resizing = False
            self.redraw_all(True)  # update thumb for new canvas size
            if self.copy:
                self.draw_shape(self.copy)  # draw back the GCDC
            return
        if self.drawing or isinstance(self.shape, Text):
            before = len(self.shapes)
            self.shape.left_up(*self.convert_coords(event))

            if len(self.shapes) - before:
                self.select_tool()
                self.update_thumb()
            self.drawing = False

    def right_up(self, event):
        """Called when the right mouse button is released - used for zoom"""
        self.shape.right_up(*self.convert_coords(event))


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
            size = (size[0], self.area[1])
        #    self.Scroll(self.GetVirtualSizeTuple()[0], -1)
        elif direction == BOTTOM:
            size = (self.area[0], size[1])
        #    self.Scroll(-1, size[1])
        #elif direction is not None:
        #    self.Scroll(*size)

        self.buffer = wx.EmptyBitmap(*size)
        self.area = size
        size = (size[0] + CANVAS_BORDER, size[1] + CANVAS_BORDER)# + 20)
        self.SetVirtualSize(size)
        self.redraw_all()

        self.Scroll(*size)

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
            #dc.SetUserScale(self.scale[0], self.scale[1])

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

        if not self.gui.util.transparent:
            params.append(self.gui.util.background)

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
        self.add_undo()
        self.shapes.append(shape)

        if self.selected:
            self.deselect()
            self.redraw_all()
        if self.text:
            self.text = None
        if self.copy:
            self.copy = None
            self.redraw_all()


    def add_undo(self):
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


    def check_move(self, pos):
        if not self.selected:
            return False
        if pos == "top" or pos == "up":
            length = len(self.shapes) - 1
            if length < 0:
                length = 0
            if self.shapes.index(self.selected) != length:
                return True
        elif pos == "down" or pos == "bottom":
            #print self.selected, self.shapes.index(self.selected)
            if self.shapes.index(self.selected) != 0:
                return True
        return False


    def do_move(self, shape):
        """ Performs the move, by popping the item to be moved """
        self.add_undo()
        x = self.shapes.index(shape)
        return (x, self.shapes.pop(x))


    def move_up(self, shape):
        """ Move a shape up in the to-draw list. """
        x, item = self.do_move(shape)
        self.shapes.insert(x + 1, item)
        self.redraw_all(True)

    def move_down(self, shape):
        """ Move a shape up in the to-draw list. """
        x, item = self.do_move(shape)
        self.shapes.insert(x - 1, item)
        self.redraw_all(True)


    def move_top(self, shape):
        """ Move a shape to the top in the to-draw list. """
        x, item = self.do_move(shape)
        self.shapes.append(item)
        self.redraw_all(True)

    def move_bottom(self, shape):
        """ Move a shape up in the to-draw list. """
        x, item = self.do_move(shape)
        self.shapes.insert(0, item)
        self.redraw_all(True)


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
        """
        Called when the window is exposed. Paint the buffer, and then create a
        region, remove the buffer rectangle then clear it with grey.
        """
        wx.BufferedPaintDC(self, self.buffer, wx.BUFFER_VIRTUAL_AREA)
        #dc.SetUserScale(self.scale[0], self.scale[1])

        if os.name == "nt":
            relbuf = self.CalcScrolledPosition(self.area)
            cli = self.GetClientSize()

            if cli.x > relbuf[0] or cli.y > relbuf[1]:
                bkgregion = wx.Region(0, 0, cli.x, cli.y)
                bkgregion.SubtractRect(wx.Rect(0, 0, relbuf[0], relbuf[1]))
                dc = wx.ClientDC(self)
                dc.SetClippingRegionAsRegion(bkgregion)
                dc.SetBrush(wx.GREY_BRUSH)
                dc.Clear()


    def delete_selected(self):
        """Deletes the selected shape"""
        if not self.selected:
            return
        for x in self.shapes:
            if x == self.selected:
                self.add_undo()
                self.shapes.remove(x)
                self.selected = None
                self.redraw_all(True)


    def deselect(self):
        """Deselects the selected shape"""
        for x in self.shapes:
            if isinstance(x, OverlayShape):
                x.selected = False
        if self.selected:
            self.selected = None
            self.redraw_all()


    def get_dc(self):
        cdc = wx.ClientDC(self)
        self.PrepareDC(cdc)
        return wx.BufferedDC(cdc, self.buffer, wx.BUFFER_VIRTUAL_AREA)


    def draw_shape(self, shape, replay=False):
        """ Redraws a single shape efficiently"""
        dc = self.get_dc()
        #dc.SetUserScale(self.scale[0], self.scale[1])
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


    def check_resize(self, size):
        """ Check whether the canvas should be resized (for large images) """
        if size[0] > self.area[0] or size[1] > self.area[1]:
            self.resize_canvas(size)


    def on_size(self, event):
        """ Updates the scrollbars when the window is resized. """
        size = self.GetClientSize()

        if size[0] < self.area[0] or size[1] < self.area[1]:
            self.SetVirtualSize((self.area[0] + 20, self.area[1] + 20))


#----------------------------------------------------------------------

if __name__ == '__main__':
    from gui import WhyteboardApp
    app = WhyteboardApp()
    app.MainLoop()