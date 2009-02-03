#!/usr/bin/python

"""
This module contains the Whiteboard class, a window that can be drawn upon.
"""

import wx
from tools import *

#----------------------------------------------------------------------

class Whiteboard(wx.ScrolledWindow):

    def __init__(self, parent, ID):
        """Initalise the window, class variables and bind mouse/paint events"""
        wx.ScrolledWindow.__init__(self, parent, ID)
        self.SetVirtualSize((1000, 1000))
        self.SetScrollRate(20,20)

        self.listeners = []
        self.thickness = 1
        self.tool      = 1    # tool ID used to generate Tool object
        self.shape     = None # current Tool
        self.shapes    = []   # list of shapes to draw
        self.undo      = []   # list of actions to undo
        self.redo      = []   # list of actions to redo

        self.SetBackgroundColour("White")
        self.SetColour("Black")

        size = self.GetClientSize()
        self.buffer = wx.EmptyBitmap(*size)

        self.InitBuffer()

        self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
        self.Bind(wx.EVT_MOTION, self.OnMotion)
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_IDLE, self.OnIdle)
        self.Bind(wx.EVT_PAINT, self.OnPaint)


    def InitBuffer(self):
        """Initialise the bitmap used for buffering the display."""
        dc = wx.BufferedDC(None, self.buffer)
        dc.SetBackground(wx.Brush(self.GetBackgroundColour()) )
        dc.Clear()
        self.PrepareDC(dc)
        self.DrawShapes(dc)
        self.reInitBuffer = False


    def ConvertEventCoords(self, event):
        """Translate mouse x/y coords to virtual scroll ones"""
        xView, yView = self.GetViewStart()
        xDelta, yDelta = self.GetScrollPixelsPerUnit()
        return (event.GetX() + (xView * xDelta),
                event.GetY() + (yView * yDelta))


    def DrawShapes(self, dc):
        """Redraws all shapes that have been drawn already."""
        dc.BeginDrawing()

        for s in self.shapes:
            pen = wx.Pen(s.colour, s.thickness, wx.SOLID)
            dc.SetPen(pen)
            dc.SetBrush(wx.TRANSPARENT_BRUSH)  # draw in unfilled shape
            s.draw(dc)  # call shape's polymorphic drawing method
        dc.EndDrawing()


    def OnLeftDown(self, event):
        """called when the left mouse button is pressed"""
        x, y = self.ConvertEventCoords(event)
        self.shape.button_down(x, y)


    def OnLeftUp(self, event):
        """called when the left mouse button is released"""
        x, y = self.ConvertEventCoords(event)
        self.shape.button_up(x, y)
        self.SelectTool(self.tool)  # reset


    def OnMotion(self, event):
        """Called when the mouse is in motion."""
        if event.Dragging() and event.LeftIsDown():
            x, y = self.ConvertEventCoords(event)
            self.shape.motion(x, y)


    def SelectTool(self, new):
        """Changes the users' tool (and cursor) they are drawing with"""
        self.tool  = new
        items      = [Pen, Rectangle, Triangle, Circle, Ellipse, RoundRect,
                      Text, Eyedropper, Fill, Arc]
        params     = [self, self.colour, self.thickness]
        self.shape = items[new-1](*params)  # create new Tool object
        self.SetCursor(wx.StockCursor(self.shape.cursor) )


    def AddShape(self, shape):
        """Adds a shape to the "to-draw" list, and to the undo list"""
        self.shapes.append(shape)


    def Undo(self):
        """Undoes an action, and adds it to the redo list"""
        try:
            shape = self.shapes.pop()
            self.undo.append( shape )  # pop newest item from shapes; add on undo stack
            self.redo.append( shape )
            self.reInitBuffer = True
        except IndexError:  # probably do some button disabling here later
            pass


    def Redo(self):
        """Redoes an action, and adds it to the undo list"""
        try:
            item = self.redo.pop()
            self.undo.append(item)  # add item to be removed onto redo stack
            self.shapes.append(item)
            self.reInitBuffer = True
        except IndexError:
            pass


    def Clear(self):
        """Removes all shapes from the "to-draw" list"""
        self.undo.append(self.shapes)
        self.shapes = []
        self.reInitBuffer = True

    def SetColour(self, colour):
        """Set a new colour, update ColourIndicator"""
        self.colour = colour
        self.Notify()


    def SetThickness(self, num):
        """Set a new line thickness, update ColourIndicator"""
        self.thickness = num
        self.Notify()


    def OnSize(self, event):
        """Called when the window is resized - redraw buffer."""
        size = self.GetClientSize()
        self.buffer = wx.EmptyBitmap(*size)
        self.reInitBuffer = True


    def OnIdle(self, event):
        """If the window size changed, resize the bitmap to match the size."""
        if self.reInitBuffer:
            self.InitBuffer()
            self.Refresh(True)


    def OnPaint(self, event):
        """Called when the window is exposed."""
        dc = wx.BufferedPaintDC(self, self.buffer)
        self.reInitBuffer = True  # redraw screen after scroll


    def AddListener(self, listener):
        """Observer pattern. Registers """
        self.listeners.append(listener)

    def Notify(self):
        """Registered Listeners are notified of colour and thickness change."""
        self.SelectTool(self.tool)  # update current shape's colour/thickness
        for other in self.listeners:
            other.Update(self.colour, self.thickness)


#----------------------------------------------------------------------

if __name__ == '__main__':
    from gui import *
    app = WhiteboardApp()
    app.MainLoop()
