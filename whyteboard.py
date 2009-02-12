#!/usr/bin/python

"""
This module contains the Whyteboard class, a window that can be drawn upon. Each
Whyteboard panel gets added to a tab in the GUI, and each Whyteboard maintains
a list of undo/redo actions for itself; thus each Whyteboard tab on the GUI has
its own undo/redo.
"""

import wx
from tools import Text

#----------------------------------------------------------------------

class Whyteboard(wx.ScrolledWindow):
    """
    The drawing frame of the application.
    """

    def __init__(self, tab):
        """
        Initalise the window, class variables and bind mouse/paint events
        """
        wx.ScrolledWindow.__init__(self, tab, -1, (0, 0))
        self.virtual_size = (1280, 1024)
        self.SetVirtualSize(self.virtual_size)
        self.SetScrollRate(20, 20)
        self.SetBackgroundColour("White")

        self.select_tool()  # tool ID used to generate Tool object
        self.shapes = []  # list of shapes for re-drawing/saving
        self._undo = []  # list of actions to undo
        self._redo = []  # list of actions to redo
        self.overlay = wx.Overlay()  # drawing "rubber bands"
        self.drawing = False

        self.buffer = wx.EmptyBitmap(*self.virtual_size)
        dc = wx.BufferedDC(None, self.buffer)
        dc.SetBackground(wx.Brush(self.GetBackgroundColour()))
        dc.Clear()

        self.Bind(wx.EVT_LEFT_DOWN, self.left_down)
        self.Bind(wx.EVT_LEFT_UP, self.left_up)
        self.Bind(wx.EVT_MOTION, self.left_motion)
        self.Bind(wx.EVT_PAINT, self.on_paint)


    def redraw_dirty(self, dc):
        """
        Figure out what part of the window to refresh.
        """
        #dc.SetBrush(wx.TRANSPARENT_BRUSH)
        x1, y1, x2, y2 = dc.GetBoundingBox()
        x1, y1 = self.CalcScrolledPosition(x1, y1)
        x2, y2 = self.CalcScrolledPosition(x2, y2)
        # make a rectangle
        rect = wx.Rect()
        rect.SetTopLeft((x1, y1))
        rect.SetBottomRight((x2, y2))
        rect.Inflate(2, 2)
        # refresh it
        self.RefreshRect(rect)


    def redraw_all(self):
        """
        Redraws all shapes that have been drawn already.
        """
        dc = wx.BufferedDC(None, self.buffer)
        dc.Clear()
        for s in self.shapes:
            s.draw(dc)  # call shape's polymorphic drawing method

        self.redraw_dirty(dc)

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
            self.shape.draw(dc, False)
            self.redraw_dirty(dc)


    def left_up(self, event):
        """
        Called when the left mouse button is released.
        """
        if self.drawing:
            x, y = self.convert_coords(event)
            self.shape.button_up(x, y)
            self.drawing = False
            self.select_tool()  # reset


    def select_tool(self, new=None):
        """
        Changes the users' tool (and cursor) they are drawing with. new is an
        int, corresponding to new - 1 = Tool ID in list below.
        Can be called with no new ID to reset itself with the current tool
        Note: Whyteboard's parent = tabs; tabs' parent = GUI
        """
        if new is None:
            new = self.GetParent().GetParent().util.tool
        else:
            self.GetParent().GetParent().util.tool = new

        items = self.GetParent().GetParent().util.items
        colour = self.GetParent().GetParent().util.colour
        thickness = self.GetParent().GetParent().util.thickness

        params = [self, colour, thickness]
        self.shape = items[new - 1](*params)  # create new Tool object
        self.SetCursor(wx.StockCursor(self.shape.cursor) )


    def add_shape(self, shape):
        """
        Adds a shape to the "to-draw" list.
        """
        self.shapes.append(shape)


    def undo(self):
        """
        Undoes an action, and adds it to the redo list.
        """
        try:
            shape = self.shapes.pop()
            self._undo.append( shape )
            self._redo.append( shape )
            self.redraw_all()
        except IndexError:
            pass


    def redo(self):
        """
        Redoes an action, and adds it to the undo list.
        """
        try:
            item = self._redo.pop()
            self._undo.append(item)  # add item to be removed onto redo stack
            self.shapes.append(item)
            self.redraw_all()
        except IndexError:
            pass


    def clear(self):
        """
        Removes all shapes from the "to-draw" list.
        """
        self.shapes = []


    def on_paint(self, event):
        """
        Called when the window is exposed.
        """
        wx.BufferedPaintDC(self, self.buffer, wx.BUFFER_VIRTUAL_AREA)

#----------------------------------------------------------------------

if __name__ == '__main__':
    from gui import WhyteboardApp
    app = WhyteboardApp()
    app.MainLoop()
