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

Note: the list "items" at the bottom contains all the classes that can be drawn
with by the user (e.g. they can't draw an image directly)
"""

import os
import time
import math
import wx

from dialogs import TextInput

_ = wx.GetTranslation

#----------------------------------------------------------------------

# constants for selection handles
HANDLE_SIZE   = 6
TOP_LEFT      = 1
TOP_RIGHT     = 2
BOTTOM_LEFT   = 3
BOTTOM_RIGHT  = 4
CENTER_TOP    = 5
CENTER_RIGHT  = 6
CENTER_BOTTOM = 7
CENTER_LEFT   = 8


class Tool(object):
    """ Abstract class representing a tool: Drawing board/colour/thickness """
    tooltip = ""
    icon = ""
    def __init__(self, board, colour, thickness, cursor=wx.CURSOR_PENCIL):
        self.board = board
        self.colour = colour
        self.thickness = thickness
        self.cursor = cursor
        self.pen = None
        self.brush = None
        self.selected = False
        self.x = 0
        self.y = 0
        self.make_pen()

    def left_down(self, x, y):
        pass

    def left_up(self, x, y):
        pass

    def motion(self, x, y):
        pass

    def draw(self, dc, replay=True):
        """ Draws itself. """
        pass

    def hit_test(self, x, y):
        """ Returns True/False if a mouseclick in "inside" the shape """
        pass

    def handle_hit_test(self, x, y):
        """ Returns the position of the handle the user has clicked on """
        pass

    def make_pen(self, dc=None):
        """ Creates a pen, usually after loading in a save file """
        self.pen = wx.Pen(self.colour, self.thickness, wx.SOLID)
        self.brush = wx.TRANSPARENT_BRUSH

    def preview(self, dc, width, height):
        """ Tools' preview in the left-hand panel """
        pass

    def save(self):
        """ Defines how this class will pickle itself """
        self.board = None
        self.pen = None
        self.brush = None

    def load(self):
        """ Defines how this class will unpickle itself """
        pass

#----------------------------------------------------------------------

class Pen(Tool):
    """ A free-hand pen. """
    tooltip = _("Draw strokes with a brush")
    name = _("Pen")
    icon = "pen"

    def __init__(self, board, colour, thickness, cursor=wx.CURSOR_PENCIL):
        Tool.__init__(self, board, colour, thickness, cursor)
        self.points = []  # ALL x1, y1, x2, y2 coords to render
        self.time = []  # list of times for each point, for redrawing

    def left_down(self, x, y):
        self.x = x  # original mouse coords
        self.y = y
        self.motion(x, y)

    def left_up(self, x, y):
        if self.points:
            self.board.add_shape(self)
            if len(self.points) == 1:  # a single click
                self.board.redraw_all()

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
        """Points below make a curly line to show an example Pen drawing"""
        dc.DrawSpline([(52, 10), (51, 10), (50, 10), (49, 10), (49, 9), (48, 9),
                 (47, 9), (46, 9), (46, 8), (45, 8), (44, 8), (43, 8), (42, 8),
                 (41, 8), (40, 8), (39, 8), (38, 8), (37, 8), (36, 8), (35, 8),
                 (34, 8), (33, 8), (32, 8), (31, 8), (30, 8), (29, 8), (28, 8),
                 (27, 8), (27, 10), (26, 10), (26, 11), (26, 12), (26, 13),
                 (26, 14), (26, 15), (26, 16), (28, 18), (30, 19), (31, 21),
                 (34, 22), (36, 24), (37, 26), (38, 27), (40, 28), (40, 29),
                 (40, 30), (40, 31), (38, 31), (37, 32), (35, 33), (33, 33),
                 (31, 34), (28, 35), (25, 36), (22, 36), (20, 37), (17, 37),
                 (14, 37), (12, 37), (10, 37), (9, 37), (8, 37), (7, 37)])


#----------------------------------------------------------------------

class OverlayShape(Tool):
    """
    Contains methods for drawing an overlayed shape. Has some general method
    implementations for drawing handles and drawing the shape.
    """
    def __init__(self, board, colour, thickness, cursor=wx.CURSOR_CROSS):
        Tool.__init__(self, board, colour, thickness, cursor)
        self.handles = []

    def left_down(self, x, y):
        self.x = x
        self.y = y
        self.board.overlay = wx.Overlay()

    def left_up(self, x, y):
        """ Only adds the shape if it was actually dragged out """
        if x != self.x and y != self.y:
            self.board.add_shape(self)
            self.sort_handles()

    def draw(self, dc, replay=False, _type="Rectangle"):
        """
        Draws a shape polymorphically, using Python's introspection; is called
        by any sub-class that needs to be overlayed.
        When called with replay=True it doesn't draw a temp outline
        Avoids excess calls to make_pen - better performance
        """
        if not replay:
            odc = wx.DCOverlay(self.board.overlay, dc)
            odc.Clear()

        if not self.pen or self.selected or isinstance(self, Note):
            self.make_pen(dc)  # Note object needs a DC to draw its outline here
        dc.SetPen(self.pen)
        dc.SetBrush(self.brush)
        getattr(dc, "Draw" + _type)(*self.get_args())

        if self.selected:
            self.draw_selected(dc)
        if not replay:
            del odc

    def get_args(self):
        """The drawing arguments that this class uses to draw itself"""
        pass

    def get_handles(self):
        """Returns the handle positions: top-lef, top-rig, btm-lef, btm-rig"""
        pass

    def resize(self, x, y, direction=None):
        """When the shape is being resized with Select tool"""
        self.motion(x, y)

    def move(self, x, y, offset):
        """Being moved with Select. Offset is to keep the cursor centered"""
        self.x = x - offset[0]
        self.y = y - offset[1]

    def sort_handles(self):
        """Sets the shape's handles"""
        top_left, top_right, bottom_left, bottom_right = self.get_handles()[:4]
        size = HANDLE_SIZE
        rect1 = wx.Rect(top_left[0], top_left[1], size, size)
        rect2 = wx.Rect(top_right[0], top_right[1], size, size)
        rect3 = wx.Rect(bottom_left[0], bottom_left[1], size, size)
        rect4 = wx.Rect(bottom_right[0], bottom_right[1], size, size)
        self.handles = [rect1, rect2, rect3, rect4]

    def handle_hit_test(self, x, y):
        """Returns which handle has been clicked on"""
        if not hasattr(self, "handles"):
            self.sort_handles()
            self.handle_hit_test(x, y)

        if self.handles[0].InsideXY(x, y):
            return TOP_LEFT
        if self.handles[1].InsideXY(x, y):
            return TOP_RIGHT
        if len(self.handles) > 2:
            if self.handles[2].InsideXY(x, y):
                return BOTTOM_LEFT
            if self.handles[3].InsideXY(x, y):
                return BOTTOM_RIGHT
        return False  # nothing hit

    def anchor(self, direction):
        """
        Avoids an issue when resizing, anchors shape's x/y point to the opposite
        corner of the corner being dragged
        """
        pass


    def draw_selected(self, dc):
        """Draws each handle that an object has"""
        dc.SetBrush(find_inverse(self.colour))
        dc.SetPen(wx.Pen(wx.BLACK, 1, wx.SOLID))
        draw = lambda dc, x, y: dc.DrawRectangle(x, y, HANDLE_SIZE, HANDLE_SIZE)
        [draw(dc, x, y) for x, y in self.get_handles()]


    def offset(self, x, y):
        """Used when moving the shape, to keep the cursor in the same place"""
        return (x - self.x, y - self.y)

    def load(self):
        self.selected = False

#----------------------------------------------------------------------

class Rectangle(OverlayShape):
    """
    The rectangle and its descended classes (ellipse/rounded rect) use an
    overlay as a rubber banding method of drawing itself over other shapes.
    """
    tooltip = _("Draw a rectangle")
    name = _("Rectangle")
    icon = "rectangle"
    def __init__(self, board, colour, thickness):
        OverlayShape.__init__(self, board, colour, thickness)
        self.width = 0
        self.height = 0
        self.rect = None

    def motion(self, x, y):
        self.width =  x - self.x
        self.height = y - self.y

    def get_args(self):
        x, y, w, h = self.x, self.y, self.width, self.height
        args = [min(x, w + x), min(y, h + y), abs(w), abs(h)]
        return args

    def get_handles(self):
        t = round(self.thickness / 2)
        x, y, w, h = self.get_args()[:4]  # RoundedRect has 5 args
        return [(x - t - 5, y - t - 5),
                (x + w + t, y - t - 5),
                (x - t - 5, y + h + t),
                (x + w + t, y + h + t)] #,

                #(x - t - 5 + (w / 2), y - t - 5),  middle handles
                #(x + w + t, y - t - 5 + (h / 2)),
                #(x - t - 5 + (w / 2), y + h + t),
                #(x - t - 5, y + h + t - (h / 2) - 5)]

    def anchor(self, direction):
        """
        Avoids an issue when resizing, anchors shape's x/y point to the opposite
        corner of the corner being dragged
        """
        r = self.get_args()[:4]

        if direction == TOP_LEFT:
            self.x = r[0] + r[2]
            self.y =  r[1] + r[3]
            self.width = -(r[2] - r[0])
            self.height = -(r[1] - r[1])
        elif direction == BOTTOM_LEFT:
            self.x = r[0] + r[2]
            self.y = r[1]
            self.width = -r[0]
            self.height = -r[1]
        elif direction == TOP_RIGHT:
            self.x = r[0]
            self.y =  r[1] + r[3]
            self.width = -(r[2] - r[0])
            self.height = -(r[1] - r[1])
        elif direction == BOTTOM_RIGHT:
            self.x = r[0]
            self.y = r[1]
            self.width = r[2]
            self.height = r[3]

        self.sort_handles()

    def sort_handles(self):
        """
        Do some rectangle conversions instead of many if statements.
        Thickness is added to allow the Select tool to select the shape via
        its lines (as opposed to its x/y point)
        """
        super(Rectangle, self).sort_handles()
        self.update_rect()

    def update_rect(self):
        """Need to pad out the rectangle with the line thickness"""
        x, y, w, h = self.get_args()[:4]
        t = math.ceil(self.thickness / 2)
        w =  abs(w) + self.thickness
        h =  abs(h) + self.thickness
        self.rect = wx.Rect(x - t, y - t, w, h)

    def hit_test(self, x, y):
        if not hasattr(self, "rect"):
            self.sort_handles()
        return self.rect.InsideXY(x, y)

    def preview(self, dc, width, height):
        dc.DrawRectangle(5, 5, width - 15, height - 15)

#----------------------------------------------------------------------

class Ellipse(Rectangle):
    """
    Easily extends from Rectangle.
    """
    tooltip = _("Draw an oval shape")
    name = _("Ellipse")
    icon = "ellipse"
    def draw(self, dc, replay=False):
        super(Ellipse, self).draw(dc, replay, "Ellipse")

    def preview(self, dc, width, height):
        dc.DrawEllipse(5, 5, width - 12, height - 12)

    def hit_test(self, x, y):
        """ http://www.conandalton.net/2009/01/how-to-draw-ellipse.html """
        dx = (x - self.x) / self.width
        dy = (y - self.y) / self.height
        if dx * dx + dy * dy < 1:
            return True
        return False

#----------------------------------------------------------------------


class Circle(OverlayShape):
    """
    Draws a circle. Uses its radius to calculate handle position
    """
    tooltip = _("Draw a circle")
    name = _("Circle")
    icon = "circle"
    def __init__(self, board, colour, thickness):
        OverlayShape.__init__(self, board, colour, thickness)
        self.radius = 1

    def motion(self, x, y):
        self.radius = ((self.x - x) ** 2 + (self.y  - y) ** 2) ** 0.5

    def draw(self, dc, replay=False):
        super(Circle, self).draw(dc, replay, "Circle")

    def preview(self, dc, width, height):
        dc.DrawCircle(width/2, height/2, 15)

    def get_args(self):
        return [self.x, self.y, self.radius]

    def resize(self, x, y, direction=None):
        self.motion(x, y)

    def get_handles(self):
        d = lambda x, y: (x - 2, y - 2)
        x, y, r = self.get_args()
        return d(x - r, y - r), d(x- r, y + r), d(x + r, y - r), d(x + r, y + r)

    def hit_test(self, x, y):
        val = ((x - self.x) * (x - self.x)) + ((y - self.y) * (y - self.y))

        if val <= (self.radius * self.radius):
            return True
        return False

#----------------------------------------------------------------------

class RoundedRect(Rectangle):
    """
    Easily extends from Rectangle.
    """
    tooltip = _("Draw a rectangle with rounded edges")
    name = _("Rounded Rect")
    icon = "rounded-rect"
    def draw(self, dc, replay=False):
        super(RoundedRect, self).draw(dc, replay, "RoundedRectangle")

    def preview(self, dc, width, height):
        dc.DrawRoundedRectangle(5, 5, width - 10, height - 7, 8)

    def get_args(self):
        args = super(RoundedRect, self).get_args()
        args.append(35)
        return args

#----------------------------------------------------------------------


class Line(OverlayShape):
    """
    Draws a line - methods for its own handles, resizing/moving and line length
    """
    tooltip = _("Draw a straight line")
    name = _("Line")
    icon = "line"
    def __init__(self, board, colour, thickness):
        OverlayShape.__init__(self, board, colour, thickness)
        self.x2 = 0
        self.y2 = 0

    def left_down(self, x, y):
        super(Line, self).left_down(x, y)
        self.x2 = x
        self.y2 = y

    def motion(self, x, y):
        self.x2 = x
        self.y2 = y

    def left_up(self, x, y):
        """ Don't add a 'blank' line """
        if self.x != self.x2 or self.y != self.y2:
            self.board.add_shape(self)
            self.sort_handles()

    def offset(self, x, y):
        """Returns two tupples (unlike the others) - one for each point"""
        return ((x - self.x, y - self.y), (x - self.x2, y - self.y2))

    def sort_handles(self):
        handles = self.get_handles()
        size = HANDLE_SIZE
        rect1 = wx.Rect(handles[0][0], handles[0][1], size, size)
        rect2 = wx.Rect(handles[1][0], handles[1][1], size, size)
        self.handles = [rect1, rect2]

    def draw(self, dc, replay=False):
        super(Line, self).draw(dc, replay, "Line")

    def get_args(self):
        return [self.x, self.y, self.x2, self.y2]

    def move(self, x, y, offset):
        self.x = x - offset[0][0]
        self.y = y - offset[0][1]
        self.x2 = x - offset[1][0]
        self.y2 = y - offset[1][1]

    def resize(self, x, y, direction=None):
        if direction == TOP_LEFT:
            self.x = x
            self.y = y
        else:
            self.x2 = x
            self.y2 = y

    def get_handles(self):
        d = lambda x, y: (x - 2, y - 2)
        return d(self.x, self.y), d(self.x2, self.y2)

    def preview(self, dc, width, height):
        dc.DrawLine(10, height / 2, width - 10, height / 2)

    def point_distance(self, a, b, c):
        """Taken/reformatted from http://stackoverflow.com/questions/849211/"""
        t = b[0] - a[0], b[1] - a[1]                   # Vector ab
        dd = math.sqrt(t[0] ** 2 + t[1] ** 2)          # Length of ab
        t = t[0] / dd, t[1] / dd                       # unit vector of ab
        n = -t[1], t[0]                                # normal unit vect. to ab
        ac = c[0] - a[0], c[1] - a[1]                  # vector ac
        return math.fabs(ac[0] * n[0] + ac[1] * n[1])  # the minimum distance

    def hit_test(self, x, y):
        """
        The above function calculates further than the length of the line. This
        stops it from even performing that calculation
        """
        if self.x < self.x2:
            if x < self.x or x > self.x2:
                return False
        else:
            if x > self.x or x < self.x2:
                return False

        val = self.point_distance((self.x, self.y), (self.x2, self.y2), (x, y))
        if val < 3 + round(self.thickness / 2):
            return True
        return False

#---------------------------------------------------------------------

class Eraser(Pen):
    """
    Erases stuff. Has a custom cursor from a drawn rectangle on a DC, turned
    into an image then into a cursor.
    """
    tooltip = _("Erase a drawing to the background")
    name = _("Eraser")
    icon = "eraser"
    def __init__(self, board, colour, thickness):
        cursor = self.make_cursor(thickness)
        Pen.__init__(self, board, (255, 255, 255), thickness + 6, cursor)


    def make_cursor(self, thickness):
        cursor = wx.EmptyBitmap(thickness + 7, thickness + 7)
        memory = wx.MemoryDC()
        memory.SelectObject(cursor)

        if os.name == "posix":
            memory.SetPen(wx.Pen((255, 255, 255), 1))  # border
            memory.SetBrush(wx.Brush((0, 0, 0)))
        else:
            memory.SetPen(wx.Pen((0, 0, 0), 1))  # border
            memory.SetBrush(wx.Brush((255, 255, 255)))

        memory.DrawRectangle(0, 0, thickness + 7, thickness + 7)
        memory.SelectObject(wx.NullBitmap)
        img = wx.ImageFromBitmap(cursor)
        cursor = wx.CursorFromImage(img)
        return cursor


    def preview(self, dc, width, height):
        thickness = self.thickness + 1
        dc.SetPen(wx.Pen((0, 0, 0), 1, wx.SOLID))
        dc.DrawRectangle(15, 7, thickness + 1,  thickness + 1)

    def make_pen(self, dc=None):
        """ Creates a pen, usually after loading in a save file """
        super(Eraser, self).make_pen()
        self.pen = wx.Pen(self.colour, self.thickness + 4, wx.SOLID)

    def save(self):
        super(Eraser, self).save()
        self.cursor = None

#----------------------------------------------------------------------

class Eyedrop(Tool):
    """
    Selects the colour at the specified x,y coords
    """
    tooltip = _("Picks a color from the selected pixel")
    name = _("Eyedropper")
    icon = "eyedrop"
    def __init__(self, board, colour, thickness):
        Tool.__init__(self, board, colour, thickness, wx.CURSOR_CROSS)

    def left_down(self, x, y):
        dc = wx.BufferedDC(None, self.board.buffer)  # create tmp DC
        colour = dc.GetPixel(x, y)  # get colour
        board = self.board.gui
        board.control.colour.SetColour(colour)
        board.util.colour = colour
        board.control.preview.Refresh()

    def preview(self, dc, width, height):
        dc.SetBrush(wx.Brush(self.board.gui.util.colour))
        dc.DrawRectangle(20, 20, 5, 5)


#----------------------------------------------------------------------


class Text(OverlayShape):
    """
    Allows the input of text. When a save is pickled, the wx.Font and a string
    storing its values is stored. This string is then used to reconstruct the
    font.
    """
    tooltip = _("Input text")
    name = _("Text")
    icon = "text"
    def __init__(self, board, colour, thickness):
        OverlayShape.__init__(self, board, colour, thickness, wx.CURSOR_IBEAM)
        self.font = None
        self.text = ""
        self.font_data = ""
        self.extent = (0, 0)

    def handle_hit_test(self, x, y):
        pass

    def resize(self, x, y, direction=None):
        pass

    def left_down(self, x, y):
        super(Text, self).left_down(x, y)
        self.board.text = self

    def left_up(self, x, y):
        """
        Shows the text input dialog, creates a new Shape object if the cancel
        button was pressed, otherwise updates the object's text, checks that the
        text string contains any letters and if so, adds itself to the list
        """
        self.x = x
        self.y = y
        dlg = TextInput(self.board.gui)

        if dlg.ShowModal() == wx.ID_CANCEL:
            dlg.Destroy()
            self.board.text = None
            self.board.redraw_all()
            self.board.select_tool()
            return False

        dlg.transfer_data(self)  # grab font and text data
        self.font_data = self.font.GetNativeFontInfoDesc()

        if self.text:
            self.board.add_shape(self)
            self.update_scroll()
            return True
        self.board.text = None
        return False


    def edit(self, event=None):
        """Pops up the TextInput box to edit itself"""
        text = self.text  # restore to these if cancelled/blank
        font = self.font
        font_data = self.font_data
        colour = self.colour
        self.board.add_undo()

        dlg = TextInput(self.board.gui, self)
        if dlg.ShowModal() == wx.ID_CANCEL:
            dlg.Destroy()
            self.text = text  # restore attributes
            self.font = font
            self.colour = colour
            self.font_data = font_data
            self.find_extent()
            self.board.undo_list.pop()  # undo "undo point" :)
            self.board.redraw_all()  # get rid of any text
        else:

            dlg.transfer_data(self)  # grab font and text data
            self.font_data = self.font.GetNativeFontInfoDesc()

            if not self.text:
                self.text = text  # don't want a blank item
                return False
            self.update_scroll()
            return True


    def update_scroll(self, redraw=True):
        """
        Updates the scrollbars of a Whyteboard if the entered text plus its
        position is vertically or horizontally larger than its current size.
        """
        self.find_extent()
        width, height = self.extent

        size = (width + self.x, height + self.y)
        if self.board and not self.board.update_scrollbars(size) and redraw:
            self.board.redraw_all()  # force render if they don't update


    def draw(self, dc, replay=False):
        if not self.font:
            self.restore_font()
            self.update_scroll()
        dc.SetFont(self.font)
        dc.SetTextForeground(self.colour)
        super(Text, self).draw(dc, replay, "Label")


    def restore_font(self):
        """Updates the text's font to the saved font data"""
        self.font = wx.FFont(0, 0)
        self.font.SetNativeFontInfoFromString(self.font_data)


    def find_extent(self):
        """Finds the width/height of the object's text"""
        dc = wx.WindowDC(self.board.gui)
        x = dc.GetMultiLineTextExtent(self.text, self.font)
        self.extent = x[0], x[1]


    def get_handles(self):
        x, y, w, h = self.x, self.y, self.extent[0], self.extent[1]
        d = lambda x, y: (x - 2, y - 2)
        return d(x, y), d(x + w, y), d(x, y + h), d(x + w, y + h)


    def get_args(self):
        w = self.x + self.extent[0]
        h = self.y + self.extent[1]
        return [self.text, wx.Rect(self.x, self.y, w, h)]


    def hit_test(self, x, y):
        width = self.x + self.extent[0]
        height = self.y + self.extent[1]

        if x > self.x and x < width and y > self.y and y < height:
            return True
        return False


    def preview(self, dc, width, height):
        dc.SetTextForeground(self.colour)
        dc.DrawText("abcdef", 15, height / 2 - 10)


    def save(self):
        super(Text, self).save()
        self.font = None


    def load(self):
        super(Text, self).load()
        self.restore_font()
        self.update_scroll(False)


#----------------------------------------------------------------------

SIZE = 10  # border size for note

class Note(Text):
    """
    A special type of text input, in the style of a post-it/"sticky" notes.
    It is linked to the tab it's displayed on, and is drawn with a light
    yellow background (to show that it's a note). An overview of notes for each
    tab can be viewed on the side panel.
    """
    tooltip = _("Insert a note")
    name = _("Note")
    icon = "note"
    def __init__(self, board, colour, thickness):
        Text.__init__(self, board, colour, thickness)
        self.tree_id = None

    def left_up(self, x, y,):
        """ Don't add a blank note """
        if super(Note, self).left_up(x, y):
            self.board.gui.notes.add_note(self)
        else:
            self.board.redraw_all()

    def edit(self):
        """Edit a non-blank Note by changing the tree item's text"""
        if super(Note, self).edit():
            tree = self.board.gui.notes.tree
            text = self.text.replace("\n", " ")[:15]
            tree.SetItemText(self.tree_id, text)

    def find_extent(self):
        """Overrides to add extra spacing to the extent for the rectangle."""
        super(Note, self).find_extent()
        self.extent = (self.extent[0] + 20, self.extent[1] + 20)

    def make_pen(self, dc=None):
        """We first must draw the Note outline"""
        if dc:
            self.find_extent()
            dc.SetBrush(wx.Brush((255, 223, 120)))
            dc.SetPen(wx.Pen((0, 0, 0), 1))
            dc.DrawRectangle(self.x - SIZE, self.y - SIZE, *self.extent)
        super(Note, self).make_pen()

    def hit_test(self, x, y):
        width = self.x + self.extent[0] - SIZE
        height = self.y + self.extent[1] - SIZE

        if x > self.x - SIZE and x < width and y > self.y - SIZE and y < height:
            return True
        return False

    def get_handles(self):
        x, y, w, h = self.x, self.y, self.extent[0], self.extent[1]
        d = lambda x, y: (x - 2, y - 2)
        return (d(x - SIZE, y - SIZE), d(x + w - SIZE, y - SIZE),
                d(x - SIZE, y + h - SIZE), d(x + w - SIZE, y + h - SIZE))

    def preview(self, dc, width, height):
        dc.SetBrush(wx.Brush((255, 223, 120)))
        dc.SetPen(wx.Pen((0, 0, 0), 1))
        dc.FloodFill(0, 0, (255, 255, 255))
        dc.SetBrush(wx.TRANSPARENT_BRUSH)
        super(Note, self).preview(dc, width, height)

    def load(self, add_note=True):
        """Recreates the note in the tree"""
        super(Note, self).load()
        gui = self.board.gui
        if add_note:
            gui.notes.add_note(self, gui.tab_count - 1)

#----------------------------------------------------------------------

class Image(OverlayShape):
    """
    When being pickled, the image reference will be removed.
    """
    def __init__(self, board, image, path):
        OverlayShape.__init__(self, board, "Black", 1)
        self.image = image
        self.path = path  # used to restore image on load
        self.resizing = False

    def left_down(self, x, y):
        self.x = x
        self.y = y
        self.board.add_shape(self)
        size = (self.image.GetWidth(), self.image.GetHeight())
        self.board.update_scrollbars(size)
        self.sort_handles()

        dc = wx.BufferedDC(None, self.board.buffer)
        self.draw(dc)
        self.board.redraw_dirty(dc)

    #def handle_hit_test(self, x, y):
    #    pass
    def sort_handles(self):
        super(Image, self).sort_handles()
        if not self.resizing:
            print 'to image'
            self.img = wx.Bitmap.ConvertToImage(self.image)
            self.resizing = True
        else:
            print 'from image'
            self.image = wx.BitmapFromImage(self.img)


    def resize(self, x, y, direction=None):
        self.img.Rotate(1, (x, y))


    def draw(self, dc, replay=False):
        super(Image, self).draw(dc, replay, "Bitmap")

    def get_args(self):
        return [self.image, self.x, self.y]

    def get_handles(self):
        d = lambda x, y: (x - 2, y - 2)
        img = self.image
        x, y, w, h = self.x, self.y, img.GetWidth(), img.GetHeight()
        return d(x, y), d(x + w, y), d(x, y + h), d(x + w, y + h)

    def save(self):
        super(Image, self).save()
        self.image = None

    def load(self):
        super(Image, self).load()
        if os.path.exists(self.path):
            self.image = wx.Bitmap(self.path)
            size = (self.image.GetWidth(), self.image.GetHeight())
            self.board.update_scrollbars(size)
            self.colour = "Black"
        else:
            self.image = wx.EmptyBitmap(0, 0)
            wx.MessageBox("Path for the image %s not found." % self.path)


    def hit_test(self, x, y):
        width, height = self.image.GetSize()
        rect_x = self.x
        rect_y = self.y
        rect_x2 = rect_x + width
        rect_y2 = rect_y + height

        if x > rect_x and x < rect_x2 and y > rect_y and y < rect_y2:
            return True
        else:
            return False

#----------------------------------------------------------------------

class Select(Tool):
    """
    Select an item to move it around/resize/change colour/thickness/edit text
    Only create an undo point when an item is selected and been moved/resized
    """
    tooltip = _("Select a shape to move and resize it")
    name = _("Shape Select ")
    icon = "select"
    def __init__(self, board, image, path):
        Tool.__init__(self, board, (0, 0, 0), 1, wx.CURSOR_ARROW)
        self.shape = None
        self.dragging = False
        self.undone = False  # Adds an undo point once per class
        self.anchored = False  # Anchor shape's x point -once-, when resizing
        self.direction = None
        self.count = 0
        self.offset = (0, 0)

    def left_down(self, x, y):
        """
        Sees if a shape is underneath the mouse coords, and allows the shape to
        be re-dragged to place
        """
        shapes = self.board.shapes
        shapes.reverse()
        found = False
        for count, shape in enumerate(shapes):
            direction = shape.handle_hit_test(x, y)  # test handle before area

            if direction:
                self.direction = direction
                found = True
            elif shape.hit_test(x, y):
                found = True

            if found:
                self.board.overlay = wx.Overlay()
                self.shape = shapes[count]
                self.dragging = True
                self.count = count
                self.offset = self.shape.offset(x, y)
                self.x = shape.x
                self.y = shape.y
                if self.board.selected:
                    self.board.deselect()
                self.board.selected = shape
                shape.selected = True
                self.board.shapes.pop(count)
                self.board.redraw_all()  # hide 'original'
                self.board.shapes.insert(count, shape)
                self.draw(self.board.get_dc())  # draw 'new'
                break  # breaking is vital to selecting the correct shape
        else:
            self.board.deselect()

    def double_click(self, x, y):
        if isinstance(self.board.selected, Text):
            self.dragging = False
            self.board.selected.edit()

    def motion(self, x, y):
        if self.dragging:
            if not self.undone:  # add a single undo point, not one per call
                self.board.add_undo()
                self.undone = True
            if not self.direction:  # moving
                self.shape.move(x, y, self.offset)
            else:
                if not self.anchored:  # don't want to keep anchoring
                    self.shape.anchor(self.direction)
                    self.anchored = True
                self.shape.resize(x, y, self.direction)


    def draw(self, dc, replay=False):
        if self.dragging:
            self.shape.draw(dc, False)


    def left_up(self, x, y):
        if self.dragging:
            self.shape.sort_handles()

            if isinstance(self.shape, Image):
                image = self.shape.image
                size = (x + image.GetWidth(), y + image.GetHeight())
                self.board.update_scrollbars(size)
            elif isinstance(self.shape, Text):
                self.shape.update_scroll(False)

        self.board.redraw_all(update_thumb=True)
        self.board.select_tool()


#----------------------------------------------------------------------

class BitmapSelect(Rectangle):
    """
    Rectangle selection tool, used to select a region to copy/paste. When it
    is drawn it is stored inside the current tab, not in the shapes list
    """
    tooltip = _("Select a rectangle region to copy as a bitmap")
    name = _("Bitmap Select")
    icon = "select-rectangular"
    def __init__(self, board, image, path):
        Rectangle.__init__(self, board, (0, 0, 0), 2)

    def make_pen(self, dc=None):
        super(BitmapSelect, self).make_pen()
        self.pen = wx.Pen(self.colour, self.thickness, wx.SHORT_DASH)

    def left_down(self, x, y):
        super(BitmapSelect, self).left_down(x, y)
        self.board.copy = None
        self.board.redraw_all()
        self.board.copy = self

    def left_up(self, x, y):
        """ Doesn't affect the shape list """
        if not (x != self.x and y != self.y):
            self.board.copy = None

    def preview(self, dc, width, height):
        dc.SetPen(wx.BLACK_DASHED_PEN)
        dc.SetBrush(wx.TRANSPARENT_BRUSH)
        dc.DrawRectangle(10, 10, width - 20, height - 20)

#---------------------------------------------------------------------

def find_inverse(colour):
    """ Invert an RGB colour """
    if not isinstance(colour, wx.Colour):
        c = colour
        colour = wx.Colour()
        colour.SetFromName(c)
    r = 255 - colour.Red()
    g = 255 - colour.Green()
    b = 255 - colour.Blue()
    return wx.Brush((r, g, b))


#  Reference the correct classes for pickled files with old class names
class RoundRect:
    self = RoundedRect
class RectSelect:
    pass

RoundRect = RoundedRect
RectSelect = BitmapSelect

# items to draw with
items = [Pen, Eraser, Rectangle, RoundedRect, Line, Ellipse, Circle, Text, Note,
        Eyedrop, BitmapSelect, Select]