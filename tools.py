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
        self.make_pen()

    def button_down(self, x, y):
        pass

    def button_up(self, x, y):
        pass

    def motion(self, x, y):
        pass

    def draw(self, dc, replay=True):
        pass

    def make_pen(self):
        self.pen = wx.Pen(self.colour, self.thickness, wx.SOLID)
        self.brush = wx.TRANSPARENT_BRUSH



#----------------------------------------------------------------------


class Pen(Tool):
    """
    A free-hand pen.
    TODO: possible pen styles: dashed, slanted etc.
    """

    def __init__(self, board, colour, thickness):
        Tool.__init__(self, board, colour, thickness)
        self.points = []  # ALL x1, y1, x2, y2 coords to render
        self.time = []  # list of times for each point, for redrawing

    def button_down(self, x, y):
        self.x = x  # original mouse coords
        self.y = y

    def button_up(self, x, y):
        if self.points:
            self.board.add_shape(self)

    def motion(self, x, y):
        self.points.append( [self.x, self.y, x, y] )
        self.time.append(time.time() )
        self.x = x
        self.y = y  # swap for the next call to this function

    def draw(self, dc, replay=True):
        dc.SetPen(self.pen)
        dc.DrawLineList(self.points)


#----------------------------------------------------------------------


class Rectangle(Tool):
    """
    The rectangle and its descended classes (ellipse/rounded rect) use an
    overlay as a rubber banding method of drawing itself over other shapes.
    """

    def __init__(self, board, colour, thickness):
        Tool.__init__(self, board, colour, thickness, wx.CURSOR_CROSS)

    def button_down(self, x, y):
        self.x = x
        self.y = y
        self.width = 2
        self.height = 2

    def motion(self, x, y):
        self.width = x - self.x
        self.height = y - self.y

    def button_up(self, x, y):
        """
        Clears the created overlay for rubber banding.
        """
        dc = wx.ClientDC(self.board)
        odc = wx.DCOverlay(self.board.overlay, dc)
        odc.Clear()
        self.board.overlay.Reset()
        self.board.Refresh()  # show on whyteboard

        if x != self.x and y != self.y:
            self.board.add_shape(self)

    def draw_outline(self, dc):
        odc = wx.DCOverlay(self.board.overlay, dc)
        odc.Clear()


    def draw(self, dc, replay=True, _type="Rectangle", args=[]):
        """
        Draws a shape, can be called by its sub-classes. Draws a shape
        polymorphically by using Python's introspection.
        When called for a replay it renders itself, not draw a temp. outline.
        """
        if not args:
            args = [self.x, self.y, self.width, self.height]
        dc.SetPen(self.pen)
        dc.SetBrush(wx.TRANSPARENT_BRUSH)

        if not replay:
            self.draw_outline(dc)

        method = getattr(dc, "Draw" + _type)(*args)
        method

#----------------------------------------------------------------------


class Circle(Rectangle):
    """
    Draws a circle. Extended from a Rectangle to save on repeated code.
    """

    def __init__(self, board, colour, thickness):
        Tool.__init__(self, board, colour, thickness, wx.CURSOR_CROSS)
        self.radius  = 1

    def button_down(self, x, y):
        self.x = x
        self.y = y

    def motion(self, x, y):
        self.radius = self.x - x

    def draw(self, dc, replay=True):
        super(Circle, self).draw(dc, replay, "Circle", [self.x, self.y,
              self.radius])

#----------------------------------------------------------------------


class Ellipse(Rectangle):
    """
    Easily extends from Rectangle.
    """
    def draw(self, dc, replay=True):
        super(Ellipse, self).draw(dc, replay, "Ellipse")

#----------------------------------------------------------------------


class RoundRect(Rectangle):
    """
    Easily extends from Rectangle.
    """
    def draw(self, dc, replay=True):
        super(RoundRect, self).draw(dc, replay, "RoundedRectangle", [self.x,
              self.y, self.width, self.height, 45])

#----------------------------------------------------------------------


class Eyedropper(Tool):
    """
    Selects the colour at the specified x,y coords
    """

    def __init__(self, board, colour, thickness):
        Tool.__init__(self, board, colour, thickness, wx.CURSOR_CROSS)

    def button_down(self, x, y):
        dc = wx.BufferedDC(None, self.board.buffer)  # create tmp DC
        colour = dc.GetPixel(x, y)  # get colour
        self.board.GetParent().GetParent().util.colour = colour
        self.board.GetParent().GetParent().control.preview.Refresh()


#----------------------------------------------------------------------


class Text(Tool):
    """
    Allows the input of text. When a save is pickled, the wx.TextCtrl is removed
    and its value is saved to a class attribute, where the TextCtrl is restored
    upon loading the file.
    """

    def __init__(self, board, colour, thickness):
        Tool.__init__(self, board, colour, thickness, wx.CURSOR_CHAR)

    def button_down(self, x, y):
        self.x = x
        self.y = y
        self.text = ""
        self.make_control()
        self.txt_ctrl.SetFocus()
        self.board.add_shape(self)

    def make_control(self):
        self.txt_ctrl = wx.TextCtrl(self.board, pos=(self.x, self.y),
                                    style=wx.NO_BORDER)
        self.txt_ctrl.SetValue(self.text)

        self.txt_ctrl.SetMaxLength(50)
        #self.txt.SetBackgroundColour((255,255,255,100))
        #self.board.Bind(wx.EVT_TEXT, self.on_type, self.txt_ctrl)

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
        dc.FloodFill(self.x, self.y, self.invert)

    #def draw(self, dc, replay=True):



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

    def draw(self, dc, replay=True):
        dc.DrawArc(self.x, self.y, self.x2, self.y2, self.c1, self.x2)


#----------------------------------------------------------------------


class Image(Tool):
    """
    When being pickled, the image reference will be removed.
    """

    def __init__(self, board, image, path):
        Tool.__init__(self, board, "Black", 1)
        self.image = image
        self.path = path  # used to restore image on load

    def button_down(self, x, y):
        self.x = x
        self.y = y
        self.board.add_shape(self)
        self.update_scrollbars()

        dc = wx.BufferedDC(None, self.board.buffer)
        self.draw(dc)
        self.board.redraw_dirty(dc)

    def draw(self, dc, replay=True):
        dc.DrawBitmap(self.image, self.x, self.y)


    def update_scrollbars(self):
        """
        Updates the Whyteboard's scrollbars if the loaded image is bigger than
        the scrollbar's current size.
        """
        if self.image.GetWidth() > self.board.virtual_size[0]:
            x = self.image.GetWidth()
        else:
            x = self.board.virtual_size[0]

        if self.image.GetHeight() > self.board.virtual_size[1]:
            y = self.image.GetHeight()
        else:
            y =  self.board.virtual_size[1]

        #  update the scrollbars and the board's buffer size
        if (x, y) is not self.board.virtual_size:
            self.board.virtual_size = (x, y)
            self.board.SetVirtualSize((x, y))
            self.board.buffer = wx.EmptyBitmap(*(x, y))
            dc = wx.BufferedDC(None, self.board.buffer)
            dc.SetBackground(wx.Brush(self.board.GetBackgroundColour()))
            dc.Clear()

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

    def draw(self, dc, replay=True):
        pass


#----------------------------------------------------------------------


if __name__ == '__main__':
    from gui import WhyteboardApp
    app = WhyteboardApp(redirect=True)
    app.MainLoop()
