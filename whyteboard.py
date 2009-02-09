#!/usr/bin/python

"""
This module contains the Whyteboard class, a window that can be drawn upon. Each
Whyteboard panel gets added to a tab in the GUI, and each Whyteboard maintains
a list of undo/redo actions for itself; thus each Whyteboard tab on the GUI has
its own undo/redo.
"""

import wx
from tools import (Pen, Rectangle, Circle, Ellipse, RoundRect,
                  Text, Eyedropper, Fill, Arc)

#----------------------------------------------------------------------

class Whyteboard(wx.ScrolledWindow):

    def __init__(self, tab):
        """Initalise the window, class variables and bind mouse/paint events"""
        wx.ScrolledWindow.__init__(self, tab)
        self.SetVirtualSize((1000, 1000))
        self.SetScrollRate(20, 20)
        self.SetBackgroundColour("White")

        self.colour = "Black"
        self.thickness = 1
        self.select_tool(1)  # tool ID used to generate Tool object
        self.shapes = []  # list of shapes for re-drawing/saving
        self._undo = []  # list of actions to undo
        self._redo = []  # list of actions to redo
        self.overlay = wx.Overlay()

        self.init_buffer()

        self.Bind(wx.EVT_LEFT_DOWN, self.left_down)
        self.Bind(wx.EVT_LEFT_UP, self.left_up)
        self.Bind(wx.EVT_MOTION, self.left_motion)
        self.Bind(wx.EVT_SIZE, self.on_size)
        self.Bind(wx.EVT_IDLE, self.on_idle)
        self.Bind(wx.EVT_PAINT, self.on_paint)
        #self.Bind(wx.EVT_ERASE_BACKGROUND, self.on_erase)
        self.Bind(wx.EVT_SCROLLWIN, self.on_scroll)


    def init_buffer(self):
        """Initialise the bitmap used for buffering the display."""
        size = self.GetClientSize()
        self.buffer = wx.EmptyBitmap(*size)
        dc = wx.BufferedDC(None, self.buffer)
        #dc.SetBackground(wx.Brush(self.GetBackgroundColour()) )
        dc.Clear()
        self.PrepareDC(dc)
        self.draw_shapes(dc)
        self.redraw = False


    def convert_coords(self, event):
        """Translate mouse x/y coords to virtual scroll ones"""
        xView, yView = self.GetViewStart()
        xDelta, yDelta = self.GetScrollPixelsPerUnit()
        return (event.GetX() + (xView * xDelta),
                event.GetY() + (yView * yDelta))


    def draw_shapes(self, dc):
        """Redraws all shapes that have been drawn already."""
        for s in self.shapes:
            pen = wx.Pen(s.colour, s.thickness, wx.SOLID)
            dc.SetPen(pen)
            dc.SetBrush(wx.TRANSPARENT_BRUSH)  # draw in unfilled shape
            s.draw(dc)  # call shape's polymorphic drawing method


    def left_down(self, event):
        """called when the left mouse button is pressed"""
        x, y = self.convert_coords(event)
        self.shape.button_down(x, y)


    def left_up(self, event):
        """called when the left mouse button is released"""
        x, y = self.convert_coords(event)
        self.shape.button_up(x, y)
        self.select_tool(self.tool)  # reset


    def left_motion(self, event):
        """Called when the mouse is in motion."""
        if event.Dragging() and event.LeftIsDown():
            x, y = self.convert_coords(event)
            self.shape.motion(x, y)


    def select_tool(self, new):
        """
        Changes the users' tool (and cursor) they are drawing with. new is an
        int, corresponding to new - 1 = Tool ID in list below.
        """
        self.tool = new
        items = [Pen, Rectangle, Circle, Ellipse, RoundRect, Text,
                 Eyedropper, Fill, Arc]

        params = [self, self.colour, self.thickness]
        self.shape = items[new - 1](*params)  # create new Tool object
        self.SetCursor(wx.StockCursor(self.shape.cursor) )


    def add_shape(self, shape):
        """Adds a shape to the "to-draw" list, and to the undo list"""
        self.shapes.append(shape)


    def undo(self):
        """Undoes an action, and adds it to the redo list"""
        try:
            shape = self.shapes.pop()
            self._undo.append( shape )
            self._redo.append( shape )
            self.redraw = True
        except IndexError:
            pass


    def redo(self):
        """Redoes an action, and adds it to the undo list"""
        try:
            item = self._redo.pop()
            self._undo.append(item)  # add item to be removed onto redo stack
            self.shapes.append(item)
            self.redraw = True
        except IndexError:
            pass


    def clear(self):
        """Removes all shapes from the "to-draw" list"""
        self.shapes = []
        self.redraw = True

    def on_size(self, event):
        """Called when the window is resized - redraw buffer."""
        self.redraw = True


    def on_idle(self, event):
        """If the window size changed, resize the bitmap to match the size."""
        if self.redraw:
            self.init_buffer()
            self.Refresh(False)


    def on_paint(self, event):
        """Called when the window is exposed."""
        dc = wx.BufferedPaintDC(self, self.buffer)
        #self.redraw = True  # redraw screen after scroll

    def on_erase(self, event):
        pass

    def on_scroll(self, event):
        self.redraw = True


#----------------------------------------------------------------------

if __name__ == '__main__':
    from gui import WhyteboardApp
    app = WhyteboardApp()
    app.MainLoop()
