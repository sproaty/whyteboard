#!/usr/bin/python

"""
This module contains the Whiteboard class, a window that can be drawn upon.
"""

import wx                  # This module uses the new wx namespace
from tools import *

#----------------------------------------------------------------------

class Whiteboard(wx.Window):

    def __init__(self, parent, ID):
        """Initalise the window, class variables and bind mouse/paint events"""
        wx.Window.__init__(self, parent, ID, style=wx.FULL_REPAINT_ON_RESIZE)

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
        self.DrawShapes(dc)
        self.reInitBuffer = False


    def DrawShapes(self, dc):
        """Redraws all shapes that have been drawn already."""
        dc.BeginDrawing()

        for s in self.shapes:
            pen = wx.Pen(s.colour, s.thickness, wx.SOLID)
            dc.SetPen(pen)
            dc.SetBrush(wx.TRANSPARENT_BRUSH) # draw in unfilled shape
            s.draw(dc) # call shape's polymorphic drawing method
        dc.EndDrawing()


    def OnLeftDown(self, event):
        """called when the left mouse button is pressed"""
        pos = event.GetPosition()
        self.shape.button_down(pos.x, pos.y)


    def OnLeftUp(self, event):
        """called when the left mouse button is released"""
        pos = event.GetPosition()
        self.shape.button_up(pos.x, pos.y)
        self.SelectTool(self.tool) # reset


    def OnMotion(self, event):
        """Called when the mouse is in motion."""
        if event.Dragging() and event.LeftIsDown():
            pos = event.GetPosition()
            self.shape.motion(pos.x, pos.y)
            self.reInitBuffer = True


    def SelectTool(self, new):
        """Changes the users' tool (and cursor) they are drawing with"""
        self.tool  = new
        items      = [Pen, Rectangle, Circle, Ellipse, RoundRect, Eyedropper, Text2, Fill, Arc]
        params     = [self, self.colour, self.thickness]
        self.shape = items[new-1](*params) # who would have thought this would work
        self.SetCursor(wx.StockCursor(self.shape.cursor) )


    def AddShape(self, shape):
        """Adds a shape to the "to-draw" list, and to the undo list"""
        self.shapes.append(shape)
        #if len(self.shapes) > 1:
        #    self.undo.append(shape)


    def Undo(self):
        """Undoes an action, and adds it to the redo list"""
        try:
            #if len(self.shapes) == 0: # cleared screen
            #    pass#self.shapes.append(self.undo.pop() )
            #else:
            shape = self.shapes.pop()
            self.undo.append( shape ) # pop newest item off the shapes list; add onto undo stack
            #index = self.undo[ len(self.undo) - 1]
            self.redo.append( shape )
            self.reInitBuffer = True
        except IndexError: # probably do some button disabling here later
            pass


    def Redo(self):
        """Redoes an action, and adds it to the undo list"""
        try:
            item = self.redo.pop()
            self.undo.append(item) # add item to be removed onto redo stack
            self.shapes.append(item)
            self.reInitBuffer = True
        except IndexError:
            pass


    def Clear(self):
        """Removes all shapes from the "to-draw" list"""
        self.undo.append(self.shapes)
        self.shapes = []
        self.reInitBuffer = True

        #self.undo.append(shape)

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
            #self.Refresh(False) - dunno what it's doing...
            self.Refresh()


    def OnPaint(self, event):
        """Called when the window is exposed."""
        dc = wx.BufferedPaintDC(self, self.buffer)


    def AddListener(self, listener):
        """Observer pattern. Registers """
        self.listeners.append(listener)

    def Notify(self):
        """Registered Listeners are notified of colour and thickness change."""
        self.SelectTool(self.tool) # update current shape's colour/thickness
        for other in self.listeners:
            other.Update(self.colour, self.thickness)


#----------------------------------------------------------------------

if __name__ == '__main__':
    from gui import *
    app = WhiteboardApp()
    app.MainLoop()
