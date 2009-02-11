#!/usr/bin/python

"""
This module contains classes which can be drawn onto a Whyteboard frame
"""

import time
import wx


#----------------------------------------------------------------------


class Tool(object):
    """Abstract class representing a tool: Drawing board/colour/thickness"""

    def __init__(self, board, colour, thickness, cursor = wx.CURSOR_PENCIL):
        self.board = board
        self.colour = colour
        self.thickness = thickness
        self.cursor = cursor
        self.pen = wx.Pen(self.colour, self.thickness, wx.SOLID)

    def button_down(self, x, y):
        pass

    def button_up(self, x, y):
        pass

    def motion(self, x, y):
        pass

    def draw(self, dc):
        pass


#----------------------------------------------------------------------


class Pen(Tool):

    def __init__(self, board, colour, thickness):
        Tool.__init__(self, board, colour, thickness)
        self.points = []  # ALL x1, y1, x2, y2 coords to render
        self.time = []  # list of times for each point, for redrawing

    def button_down(self, x, y):
        self.x = x  # original mouse coords
        self.y = y
        self.board.add_shape(self)

    def button_up(self, x, y):
        pass

    def motion(self, x, y):
        self.points.append( [self.x, self.y, x, y] )
        self.time.append(time.time() )
        self.x = x
        self.y = y  # swap for the next call to this function

        dc = wx.BufferedDC(wx.ClientDC(self.board), self.board.buffer)
        self.board.PrepareDC(dc)
        dc.SetPen(self.pen)
        self.draw(dc)


    def draw(self, dc):
        dc.DrawLineList(self.points)


#----------------------------------------------------------------------


class Rectangle(Tool):

    def __init__(self, board, colour, thickness):
        Tool.__init__(self, board, colour, thickness, wx.CURSOR_CROSS)

    def button_down(self, x, y):
        self.x = x
        self.y = y
        self.width = 2
        self.height = 2
        self.board.add_shape(self)

    def motion(self, x, y):
        self.width = x - self.x
        self.height = y - self.y
        self.draw_outline()


    def button_up(self, x, y):
        dc = wx.ClientDC(self.board)
        odc = wx.DCOverlay(self.board.overlay, dc)
        odc.Clear()
        self.board.overlay.Reset()
        self.board.Refresh()  # show on whyteboard

    def draw_outline(self):
        dc = wx.BufferedDC(wx.ClientDC(self.board), self.board.buffer)
        odc = wx.DCOverlay(self.board.overlay, dc)
        odc.Clear()
        self.board.PrepareDC(dc)
        dc.SetPen(self.pen)
        dc.SetBrush(wx.TRANSPARENT_BRUSH)
        self.draw(dc)


    def draw(self, dc):
        dc.DrawRectangle(self.x, self.y, self.width, self.height)


#----------------------------------------------------------------------


class Circle(Rectangle):
    """Draws a circle with an inverted background RGB "+" in its center"""

    def __init__(self, board, colour, thickness):
        Tool.__init__(self, board, colour, thickness, wx.CURSOR_CROSS)
        self.radius  = 4
        self.inMotion = False  # used to draw a cross at circle's center

    def button_down(self, x, y):
        self.x = x
        self.y = y
        self.board.add_shape(self)
        self.inMotion = True
        self.find_invert()

    def button_up(self, x, y):
        self.inMotion = False
        super(Circle, self).button_up(x, y)  # remove overlay
        self.board.redraw = True  # remove cross


    def motion(self, x, y):
        self.radius = self.x - x

        if self.radius <= 0:  # from moving down-left or down-right
            self.radius = -self.radius  # would be a negative number otherwise
        self.draw_outline()


    def draw(self, dc):
        dc.DrawCircle(self.x, self.y, self.radius)
        if self.inMotion:
            self.draw_cross(dc)


    def draw_cross(self, dc):
        """Draws a cross at the center of the circle whilst drawing
        the circle's outline"""
        pen = wx.Pen(self.invert, 1, wx.SOLID)
        dc.SetPen(pen)
        dc.DrawLine(self.x - 4, self.y, self.x + 5, self.y)
        dc.DrawLine(self.x, self.y + 4, self.x, self.y - 4)


    def find_invert(self):
        """Finds the inverted RGB value of a square pixel area"""
        dc = wx.BufferedDC(None, self.board.buffer)
        r, g, b, count = 0, 0, 0, 0

        for x in range( self.x - 4, self.x + 4):
            for y in range(self.y - 4, self.y + 4):
                colour = dc.GetPixel(x, y)
                r += colour.Red()
                g += colour.Green()
                b += colour.Blue()
                count += 1
            count += 1

        r = 255 - (r / count)
        g = 255 - (g /  count)
        b = 255 - (b / count)
        self.invert = wx.Colour(r, g, b)


#----------------------------------------------------------------------


class Ellipse(Rectangle):
    """Easily extends from Rectangle."""
    def draw(self, dc):
        dc.DrawEllipse(self.x, self.y, self.width, self.height)

#----------------------------------------------------------------------


class RoundRect(Rectangle):
    """Easily extends from Rectangle."""
    def draw(self, dc):
        dc.DrawRoundedRectangle(self.x, self.y, self.width, self.height, 45)

#----------------------------------------------------------------------


class Eyedropper(Tool):
    """Selects the colour at the specified x,y coords"""

    def __init__(self, board, colour, thickness):
        Tool.__init__(self, board, colour, thickness, wx.CURSOR_CROSS)

    def button_down(self, x, y):
        dc = wx.BufferedDC(None, self.board.buffer)  # create tmp DC
        colour = dc.GetPixel(x, y)  # get colour
        self.board.SetColour(colour)


#----------------------------------------------------------------------


class Text(Tool):
    """Currently draws a random string. Will be extended for user text input"""

    def __init__(self, board, colour, thickness):
        Tool.__init__(self, board, colour, thickness, wx.CURSOR_CHAR)

    def button_down(self, x, y):
        self.x = x
        self.y = y
        self.board.add_shape(self)
        self.txt = wx.TextCtrl(self.board, pos=(x, y), style=wx.NO_BORDER)
        self.board.Bind(wx.EVT_TEXT, self.on_type, self.txt)
        self.txt.SetFocus()
        #self.txt.SetBackgroundColour((255,255,255,100))
        self.txt.SetMaxLength(50)

    def motion(self, x, y):
        self.x = x
        self.y = y

    def on_type(self, event):
        pass


#----------------------------------------------------------------------


class Fill(Tool):
    """Not working, buggy etc."""
    def __init__(self, board, colour, thickness):
        Tool.__init__(self, board, colour, thickness)

    def button_down(self, x, y):
        self.x = x
        self.y = y
        dc = wx.BufferedDC(None, self.board.buffer)  # create tmp DC

        colour = dc.GetPixel(x, y)  # get colour
        r = colour.Red()
        g = colour.Green()
        b = colour.Blue()
        r /= 255
        b /= 255
        g /= 255
        self.invert = wx.Colour(r, g, b)
        self.board.add_shape(self)

    def draw(self, dc):
        dc.FloodFill(self.x, self.y, self.invert)


#----------------------------------------------------------------------


class Arc(Tool):
    """Buggy."""
    def __init__(self, board, colour, thickness):
        Tool.__init__(self, board, colour, thickness)

    def button_down(self, x, y):
        self.x = x
        self.y = y
        self.x2 = x
        self.y2 = y        self.c1 = 300
        self.c2 = 300
        self.board.add_shape(self)

    def motion(self, x, y):
        self.x2 = x
        self.y2 = y        self.c1 = 300
        self.c2 = 300

    def draw(self, dc):
        dc.DrawArc(self.x, self.y, self.x2, self.y2, self.c1, self.x2)


#----------------------------------------------------------------------


class Image(Tool):
    """When being pickled, the image reference will be removed."""

    def __init__(self, board, colour=(0, 0, 0), thickness=1, image=None):
        Tool.__init__(self, board, colour, thickness)
        self.image = image

    def button_down(self, x, y):
        self.x = x
        self.y = y
        self.board.add_shape(self)

    def draw(self, dc):
        dc.DrawBitmap(self.image, self.x, self.y)


#----------------------------------------------------------------------


class Note(Tool):
    """Blank template for a post-it style note
    e.g. http://www.bit10.net/images/post-it.jpg"""

    def __init__(self, board, colour=(0, 0, 0), thickness=1):
        Tool.__init__(self, board, colour, thickness)

    def button_down(self, x, y):
        self.x = x
        self.y = y
        self.text = ""

    def motion(self, x, y):
        pass

    def draw(self, dc):
        pass


#----------------------------------------------------------------------


if __name__ == '__main__':
    from gui import WhyteboardApp
    app = WhyteboardApp(redirect=True)
    app.MainLoop()
