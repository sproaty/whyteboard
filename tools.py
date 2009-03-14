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
This module contains classes which can be drawn onto a Whyteboard frame
"""

import wx
import time

from dialogs import TextInput

#----------------------------------------------------------------------


class Tool(object):
    """Abstract class representing a tool: Drawing board/colour/thickness"""

    def __init__(self, board, colour, thickness, cursor = wx.CURSOR_PENCIL):
        self.board = board
        self.colour = colour
        self.thickness = thickness
        self.cursor = cursor
        self.pen = None
        self.brush = None
        self.x = 0
        self.y = 0

        self.make_pen()

    def button_down(self, x, y):
        """
        Left mouse button event
        """
        pass

    def button_up(self, x, y):
        """
        Left button up.
        """
        pass

    def motion(self, x, y):
        """
        Mouse in motion (usually while drawing)
        """
        pass

    def draw(self, dc, replay=True):
        """
        Draws itself.
        """
        pass

    def make_pen(self):
        """
        Creates a pen from the object after loading in a save file
        """
        self.pen = wx.Pen(self.colour, self.thickness, wx.SOLID)
        self.brush = wx.TRANSPARENT_BRUSH

    def preview(self, dc, width, height):
        """
        Tools' preview for the left-hand panel
        """
        pass


#----------------------------------------------------------------------


class Pen(Tool):
    """
    A free-hand pen.
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
        if not self.pen:
            self.make_pen()
        dc.SetPen(self.pen)
        dc.DrawLineList(self.points)


    def preview(self, dc, width, height):
        """
        Points below make a curly line to show an example Pen drawing
        """
        points = [[4, 31, 4, 28], [4, 28, 4, 27], [4, 27, 4, 26], [4, 26, 4, 24], [4, 24, 4, 23], [4, 23, 4, 21], [4, 21, 7, 19], [7, 19, 8, 17], [8, 17, 8, 16], [8, 16, 9, 14], [9, 14, 9, 13], [9, 13, 10, 12], [10, 12, 11, 10], [11, 10, 12, 9], [12, 9, 13, 9], [13, 9, 13, 12], [13, 12, 13, 13], [13, 13, 13, 16], [13, 16, 14, 18], [14, 18, 14, 21], [14, 21, 14, 23], [14, 23, 14, 24], [14, 24, 15, 24], [15, 24, 16, 24], [16, 24, 18, 21], [18, 21, 20, 19], [20, 19, 21, 17], [21, 17, 23, 14], [23, 14, 24, 12], [24, 12, 25, 11], [25, 11, 26, 10], [26, 10, 26, 13], [26, 13, 26, 14], [26, 14, 26, 16], [26, 16, 26, 18], [26, 18, 26, 19], [26, 19, 26, 21], [26, 21, 27, 21], [27, 21, 28, 21], [28, 21, 29, 21], [29, 21, 31, 17], [31, 17, 32, 15], [32, 15, 34, 13], [34, 13, 35, 12], [35, 12, 36, 11], [36, 11, 36, 10], [36, 10, 37, 10], [37, 10, 37, 13], [37, 13, 37, 16], [37, 16, 37, 19], [37, 19, 37, 23], [37, 23, 37, 27], [37, 27, 38, 29], [38, 29, 38, 31], [38, 31, 38, 32], [38, 32, 38, 33], [38, 33, 39, 33], [39, 33, 40, 33], [40, 33, 42, 33], [42, 33, 45, 29], [45, 29, 48, 25], [48, 25, 51, 21], [51, 21, 55, 18], [55, 18, 57, 15], [57, 15, 60, 13], [60, 13, 61, 12], [61, 12, 61, 11], [61, 11, 61, 14], [61, 14, 61, 15], [61, 15, 62, 15], [62, 15, 62, 16], [62, 16, 63, 17], [63, 17, 63, 19], [63, 19, 65, 22]]
        dc.DrawLineList(points)

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
        Clears the created overlay for rubber banding, draws the rectangle onto
        the screen and adds it to the shape list if the rectangle was actually
        drawn out, not just a single mouse click-realease.
        """
        dc = wx.BufferedDC(None, self.board.buffer)
        odc = wx.DCOverlay(self.board.overlay, dc)
        odc.Clear()
        del odc
        self.board.overlay.Reset()

        if x != self.x and y != self.y:
            self.board.add_shape(self)
            self.draw(dc, True)
            self.board.redraw_dirty(dc)

    def draw_outline(self, dc):
        odc = wx.DCOverlay(self.board.overlay, dc)
        odc.Clear()
        del odc


    def draw(self, dc, replay=False, _type="Rectangle", args=[]):
        """
        Draws a shape polymorphically, using Python's introspection; can be
        called by its sub-classes.
        When called for a replay it renders itself; doesn't draw a temp outline.
        """
        if not args:
            args = [self.x, self.y, self.width, self.height]
        if not self.pen:
            self.make_pen()
        if replay:
            self.make_pen()

        dc.SetPen(self.pen)
        dc.SetBrush(self.brush)
        dc.SetTextForeground(self.colour)  # forces text colour
        if not replay:
            self.draw_outline(dc)

        method = getattr(dc, "Draw" + _type)(*args)
        method


    def preview(self, dc, width, height):
        dc.DrawRectangle(5, 5, width - 15, height - 15)


#----------------------------------------------------------------------


class Circle(Rectangle):
    """
    Draws a circle. Extended from a Rectangle to save on repeated code.
    """

    def __init__(self, board, colour, thickness):
        Rectangle.__init__(self, board, colour, thickness)
        self.radius  = 1

    def button_down(self, x, y):
        self.x = x
        self.y = y

    def motion(self, x, y):
        self.radius = self.x - x

    def draw(self, dc, replay=False):
        super(Circle, self).draw(dc, replay, "Circle", [self.x, self.y,
              self.radius])

    def preview(self, dc, width, height):
        dc.DrawCircle(width/2, height/2, 15)

#----------------------------------------------------------------------


class Ellipse(Rectangle):
    """
    Easily extends from Rectangle.
    """
    def draw(self, dc, replay=False):
        super(Ellipse, self).draw(dc, replay, "Ellipse")

    def preview(self, dc, width, height):
        dc.DrawEllipse(5, 5, width - 12, height - 12)

#----------------------------------------------------------------------


class RoundRect(Rectangle):
    """
    Easily extends from Rectangle.
    """
    def draw(self, dc, replay=False):
        super(RoundRect, self).draw(dc, replay, "RoundedRectangle", [self.x,
              self.y, self.width, self.height, 45])

    def preview(self, dc, width, height):
        dc.DrawRoundedRectangle(5, 5, width - 15, height - 15, 45)

#----------------------------------------------------------------------


class Line(Rectangle):
    """
    Draws a line. Extended from a Rectangle for outline code.
    """

    def __init__(self, board, colour, thickness):
        Rectangle.__init__(self, board, colour, thickness)
        self.x2 = 0
        self.y2 = 0

    def motion(self, x, y):
        self.x2 = x
        self.y2 = y

    def draw(self, dc, replay=False):
        super(Line, self).draw(dc, replay, "Line", [self.x, self.y, self.x2,
                                                    self.y2])
    def preview(self, dc, width, height):
        dc.DrawLine(10, height / 2, width - 10, height / 2)

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


class Text(Rectangle):
    """
    Allows the input of text. When a save is pickled, the wx.Font and a string
    storing its values is stored. This string is then used to reconstruct the
    font.
    """

    def __init__(self, board, colour, thickness):
        Rectangle.__init__(self, board, colour, thickness)
        self.cursor = wx.CURSOR_CHAR
        self.font = None
        self.text = ""
        self.font_data = ""
        self.extent = (0, 0)


    def motion(self, x, y):
        self.x = x
        self.y = y

    def button_up(self, x, y):
        self.x = x
        self.y = y
        dlg = TextInput(self.board.GetParent().GetParent())  # GUI

        if dlg.ShowModal() == wx.ID_CANCEL:
            dlg.Destroy()
            self.board.select_tool()
            return

        dlg.transfer_data(self)  # grab font and text data
        self.font_data = self.font.GetNativeFontInfoDesc()
        self.board.add_shape(self)
        self.update_scroll()
        return True


    def update_scroll(self):
        """
        Updates the scrollbars of a Whyteboard if the entered text plus its
        position is vertically or horizontally larger than its current size.
        """
        self.find_extent()
        width, height = self.extent

        if not self.board.update_scrollbars((width + self.x, height + self.y)):
            self.board.redraw_all()  # force render if they don't update

    def find_extent(self):
        """
        Finds the width/height extent of the inputted string
        """
        dummy = wx.Frame(None)
        dummy.SetFont(self.font)
        self.extent = dummy.GetTextExtent(self.text)
        dummy.Destroy()


    def restore_font(self):
        self.font = wx.Font(0, 0, 0, 0)
        self.font.SetNativeFontInfoFromString(self.font_data)

    def draw(self, dc, replay=False):
        if not self.font:
            self.restore_font()
        dc.SetFont(self.font)
        super(Text, self).draw(dc, replay, "Text", [self.text, self.x, self.y])

    def preview(self, dc, width, height):
        dc.SetTextForeground(self.colour)
        dc.DrawText("abcdef", 15, height / 2 - 10)


#----------------------------------------------------------------------

class Note(Text):
    """
    A special type of text input, in the style of a post-it/"sticky" notes.
    It is linked to the tab it's displayed on, and is drawn with a light
    yellow background (to show that it's a note). An overview of notes for each
    tab can be viewed on the side panel.
    """
    def button_up(self, x, y,):
        # don't add a blank note
        if super(Note, self).button_up(x, y):
            self.board.tab.GetParent().notes.add_note(self)

    def find_extent(self):
        """
        Overrides to add extra spacing to the extent for the rectangle.
        """
        dummy = wx.Frame(None)
        dummy.SetFont(self.font)
        extent = dummy.GetTextExtent(self.text)
        x, y = extent[0] + 20, extent[1] + 20
        self.extent = (x, y)
        dummy.Destroy()


    def draw(self, dc, replay=False):
        if not self.font:
            self.restore_font()

        dc.SetBrush(wx.Brush((255, 223, 120)))
        dc.SetPen(wx.Pen((0, 0, 0), 1))
        dc.DrawRectangle(self.x - 10, self.y - 10, *self.extent)
        dc.SetFont(self.font)
        super(Note, self).draw(dc, replay,)


    def preview(self, dc, width, height):
        dc.SetBrush(wx.Brush((255, 223, 120)))
        dc.SetTextForeground(self.colour)
        dc.SetPen(wx.Pen((0, 0, 0), 1))
        dc.DrawRectangle(3, 3, width - 10, height - 10)
        dc.DrawText("abcdef", 15, height / 2 - 10)

#----------------------------------------------------------------------


class Fill(Tool):
    """
    Sort of working, but it isn't being saved to the list of shapes to-draw,
    and gets erased
    """
    def __init__(self, board, colour, thickness):
        Tool.__init__(self, board, colour, thickness)

    def button_down(self, x, y):
        self.x = x
        self.y = y
        dc = wx.ClientDC(self.board)  # create tmp DC
        self.draw(dc)
        #self.board.add_shape(self)

    def draw(self, dc, replay=False):
        dc.SetPen(self.pen)
        dc.SetBrush(wx.Brush(self.colour))
        dc.FloodFill(self.x, self.y, (255, 255, 255), wx.FLOOD_SURFACE)

    def preview(self, dc, width, height):
        dc.SetBrush(wx.Brush(self.colour))
        dc.DrawRectangle(10, 10, width - 20, height - 20)


#----------------------------------------------------------------------


class Image(Tool):
    """
    When being pickled, the image reference will be removed.
    """

    def __init__(self, board, image, path):
        Tool.__init__(self, board, (0, 0, 0), 1)
        self.image = image
        self.path = path  # used to restore image on load

    def button_down(self, x, y):
        self.x = x
        self.y = y
        self.board.add_shape(self)
        #self.board.shapes.insert(0, self)  # add as "first" image
        size = (self.image.GetWidth(), self.image.GetHeight())
        self.board.update_scrollbars(size)

        dc = wx.BufferedDC(None, self.board.buffer)
        self.draw(dc)
        self.board.redraw_dirty(dc)

    def draw(self, dc, replay=False):
        dc.DrawBitmap(self.image, self.x, self.y)


#----------------------------------------------------------------------

class Zoom(Tool):
    """
    Zooms in on the current Whyteboard tab
    """
    def __init__(self, board, image, path):
        Tool.__init__(self, board, (0, 0, 0), 1)


    def button_down(self, x, y):
        x = self.board.zoom
        new = (x[0] + 0.1, x[1] + 0.1)
        self.board.zoom = new

#----------------------------------------------------------------------


class Select(Tool):
    """
    Select an item to move it around/edit text
    """
    def __init__(self, board, image, path):
        Tool.__init__(self, board, (0, 0, 0), 1)
        self.shape = None
        self.dragging = False
        self.count = None


    def button_down(self, x, y):
        print '-------'
        print x, y
        print '-------'
        for count, shape in enumerate(self.board.shapes):
            if isinstance(shape, Rectangle):
                rect_x2_1 = shape.width + shape.x
                rect_y2_1 = shape.height + shape.y
                print str(count) +": " + str(shape.x)+", "+str(rect_x2_1)+" | "+str(shape.y)+", "+str(rect_y2_1)

                rect_x2_2 = shape.x - shape.width
                #rect_y2_2 = shape.y - shape.height

                print str(count) +": " + str(shape.x)+", "+str(rect_x2_2)+" | "+str(shape.y)+", "+str(rect_y2_1)

                if ( ((x > rect_x2_1 and x < shape.x)
                    and (y < rect_y2_1 and y > shape.y))
                or ((x > rect_x2_2 and x > shape.x)
                    and (y < rect_y2_1 and y > shape.y)) ):
                    self.shape = self.board.shapes[count]
                    self.dragging = True
                    self.count = count


    def motion(self, x, y):
        if self.dragging:
            self.shape.x = x
            self.shape.y = y

    def draw(self, dc, replay=False):
        if self.dragging:
            self.shape.draw(dc)


    def button_up(self, x, y):
        """
        need to add pop(x) to remove current shape for proper undoing
        !!!!!
        """
        if self.dragging:
            del self.board.shapes[self.count]
            self.board.add_shape(self)
            self.board.redraw_all()
            self.dragging = False

#---------------------------------------------------------------------

if __name__ == '__main__':
    from gui import WhyteboardApp
    app = WhyteboardApp(redirect=True)
    app.MainLoop()
