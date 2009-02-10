#!/usr/bin/python

"""
This module contains the Whyteboard class, a window that can be drawn upon. Each
Whyteboard panel gets added to a tab in the GUI, and each Whyteboard maintains
a list of undo/redo actions for itself; thus each Whyteboard tab on the GUI has
its own undo/redo.
"""

import wx

from tools import Image

#----------------------------------------------------------------------

class Whyteboard(wx.ScrolledWindow):

    def __init__(self, tab):
        """
        Initalise the window, class variables and bind mouse/paint events
        """
        wx.ScrolledWindow.__init__(self, tab)#, style=wx.FULL_REPAINT_ON_RESIZE)
        self.SetVirtualSize((1000, 1000))
        self.SetScrollRate(20, 20)
        self.SetBackgroundColour("White")

        self.select_tool(1)  # tool ID used to generate Tool object
        self.shapes = []  # list of shapes for re-drawing/saving
        self._undo = []  # list of actions to undo
        self._redo = []  # list of actions to redo
        self.overlay = wx.Overlay()  # drawing "rubber bands"

        self.buffer = None
        self.redraw = False

        self.init_buffer()

        self.Bind(wx.EVT_LEFT_DOWN, self.left_down)
        self.Bind(wx.EVT_LEFT_UP, self.left_up)
        self.Bind(wx.EVT_MOTION, self.left_motion)
        self.Bind(wx.EVT_SIZE, self.on_size)
        self.Bind(wx.EVT_IDLE, self.on_idle)
        self.Bind(wx.EVT_PAINT, self.on_paint)
        #self.Bind(wx.EVT_SCROLL, self.on_scroll)


    def init_buffer(self):
        """
        Initialise the bitmap used for buffering the display.
        """
        size = self.GetClientSize()
        self.buffer = wx.EmptyBitmap(*size)
        dc = wx.BufferedDC(None, self.buffer)
        dc.Clear()
        dc.SetBackground(wx.Brush(self.GetBackgroundColour()))
        self.PrepareDC(dc)
        self.draw_shapes(dc)
        self.redraw = False


    def convert_coords(self, event):
        """
        Translate mouse x/y coords to virtual scroll ones.
        """
        xView, yView = self.GetViewStart()
        xDelta, yDelta = self.GetScrollPixelsPerUnit()
        return (event.GetX() + (xView * xDelta),
                event.GetY() + (yView * yDelta))


    def draw_shapes(self, dc):
        """
        Redraws all shapes that have been drawn already.
        """
        for s in self.shapes:
            pen = wx.Pen(s.colour, s.thickness, wx.SOLID)
            dc.SetPen(pen)
            dc.SetBrush(wx.TRANSPARENT_BRUSH)  # draw in unfilled shape
            s.draw(dc)  # call shape's polymorphic drawing method


    def left_down(self, event):
        """
        Called when the left mouse button is pressed..
        """
        x, y = self.convert_coords(event)
        self.shape.button_down(x, y)
        self.CaptureMouse()

    def left_up(self, event):
        """
        Called when the left mouse button is released.
        """
        x, y = self.convert_coords(event)
        self.shape.button_up(x, y)
        self.select_tool(self.GetParent().GetParent().util.tool)  # reset
        self.ReleaseMouse()

    def left_motion(self, event):
        """
        Called when the mouse is in motion.
        """
        if event.Dragging() and event.LeftIsDown():
            x, y = self.convert_coords(event)
            self.shape.motion(x, y)


    def select_tool(self, new):
        """
        Changes the users' tool (and cursor) they are drawing with. new is an
        int, corresponding to new - 1 = Tool ID in list below.
        Note: Whyteboard's parent = tabs; tabs' parent = GUI
        """
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
            self.redraw = True
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
            self.redraw = True
        except IndexError:
            pass


    def clear(self):
        """
        Removes all shapes from the "to-draw" list.
        """
        self.shapes = []
        self.redraw = True


    def on_size(self, event):
        """
        Called when the window is resized - redraw buffer.
        """
        self.redraw = True


    def on_idle(self, event):
        """
        If the window size changed, resize the bitmap to match the size.
        """
        if self.redraw:
            self.init_buffer()
            self.Refresh(False)


    def on_paint(self, event):
        """
        Called when the window is exposed.
        """
        dc = wx.BufferedPaintDC(self, self.buffer, wx.BUFFER_VIRTUAL_AREA)
        #self.PrepareDC(dc)



    def on_scroll(self, event):
        """
        Scroll window co-ordinates.
        """
        self.redraw = True


#----------------------------------------------------------------------

if __name__ == '__main__':
    from gui import WhyteboardApp
    app = WhyteboardApp()
    app.MainLoop()
