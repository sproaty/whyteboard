#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2009, 2010 by Steven Sproat
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

from __future__ import division

import os
import time
import math
import cStringIO
import ntpath
import copy
import wx

from dialogs import TextInput
from panels import MediaPanel, ShapePopup
from event_ids import *

_ = wx.GetTranslation

#----------------------------------------------------------------------

# constants for selection handles
HANDLE_SIZE   = 6  # square pixels
HANDLE_ROTATE = -1
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
    name = ""
    icon = ""
    hotkey = ""

    def __init__(self, board, colour, thickness, background=wx.TRANSPARENT,
                 cursor=wx.CURSOR_PENCIL, join=wx.JOIN_ROUND):
        self.board = board
        self.colour = colour
        self.background = background
        self.thickness = thickness
        self.cursor = cursor
        self.join = join
        self.brush = None
        self.selected = False
        self.drawing = False
        self.x = 0
        self.y = 0
        self.make_pen()

    def left_down(self, x, y):
        pass

    def left_up(self, x, y):
        pass

    def double_click(self, x, y):
        pass

    def right_up(self, x, y):
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

    def start_select_action(self, handle):
        """Do something before being resized/moved/scaled"""
        pass

    def end_select_action(self, handle):
        """
        Gives the shape a chance to do cleanup when it finishes moving/resizing
        """
        pass

    def make_pen(self, dc=None):
        """ Creates a pen, usually after loading in a save file """
        if self.background == wx.TRANSPARENT:
            self.brush = wx.TRANSPARENT_BRUSH
        else:
            self.brush = wx.Brush(self.background)

    def preview(self, dc, width, height):
        """ Tools' preview in the left-hand panel """
        pass

    def properties(self):
        """ Text description of this Tool's properties (for Shape Viewer) """
        pass

    def save(self):
        """ Defines how this class will pickle itself """
        self.board = None
        self.brush = None

    def load(self):
        """ Defines how this class will unpickle itself """
        if not hasattr(self, "background"):
            self.background = wx.TRANSPARENT
        if not hasattr(self, "drawing"):
            self.drawing = False
        if not hasattr(self, "join"):
            self.join = wx.JOIN_ROUND

#----------------------------------------------------------------------

class OverlayShape(Tool):
    """
    Contains methods for drawing an overlayed shape. Has some general method
    implementations for drawing handles and drawing the shape.
    """
    def __init__(self, board, colour, thickness, background=wx.TRANSPARENT,
                 cursor=wx.CURSOR_CROSS, join=wx.JOIN_ROUND):
        Tool.__init__(self, board, colour, thickness, background, cursor, join)
        self.handles = []
        self.board.overlay = wx.Overlay()

    def left_down(self, x, y):
        self.x = x
        self.y = y

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

        self.make_pen(dc)  # Note object needs a DC to draw its outline here
        pen = wx.Pen(self.colour, self.thickness, wx.SOLID)
        pen.SetJoin(self.join)
        dc.SetPen(pen)
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

    def resize(self, x, y, handle=None):
        """When the shape is being resized with Select tool"""
        self.motion(x, y)

    def move(self, x, y, offset):
        """Being moved with Select. Offset is to keep the cursor centered"""
        self.x = x - offset[0]
        self.y = y - offset[1]


    def sort_handles(self):
        """Sets the shape's handles"""
        self.handles = []
        for x in self.get_handles():
            self.handles.append(wx.Rect(x[0], x[1], HANDLE_SIZE, HANDLE_SIZE))


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


    def anchor(self, handle):
        """
        Avoids an issue when resizing, anchors shape's x/y point to the opposite
        side of the handle that is being dragged
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
        super(OverlayShape, self).load()
        self.selected = False


#----------------------------------------------------------------------

class Polygon(OverlayShape):
    """
    Draws a polygon with [x] number of points, each of which can be repositioned
    Due to it working different to every other shape it has to do some canvas
    manipulation here
    """
    tooltip = _("Draw a polygon")
    name = _("Polygon")
    icon = "polygon"
    hotkey = "y"

    def __init__(self, board, colour, thickness, background=wx.TRANSPARENT,
                 cursor=wx.CURSOR_CROSS, join=wx.JOIN_ROUND):
        OverlayShape.__init__(self, board, colour, thickness, background,
                              cursor, join)
        self.points = []
        self.drawing = False  # class keeps track of its drawing, not whyteboard
        self.center = None
        self.bbox = None  # bounding box
        self.scale_factor = 0
        self.original_points = []  # when scaling, we scale vs these
        self.orig_click = None  # when scaling - x/y of original click

    def left_up(self, x, y):
        pass

    def left_down(self, x, y):
        if not self.drawing:
            if not self.board.HasCapture():
                self.board.CaptureMouse()

        self.drawing = True
        self.points.append((x, y))
        if not self.x or not self.y:
            self.x = x
            self.y = y
            self.points.append((x, y))
            self.board.draw_shape(self)


    def motion(self, x, y):
        if self.drawing:
            if self.points:
                pos = len(self.points) - 1
                if pos < 0:
                    pos = 0
                self.points[pos] = (x, y)
            self.board.draw_shape(self)


    def double_click(self, x, y):
        if len(self.points) == 2:
            return
        del self.points[len(self.points) - 1]  # dbl clicking fires 2 click evts
        self.right_up(x, y)


    def right_up(self, x, y):
        if len(self.points) > 2:
            self.drawing = False
            self.board.add_shape(self)
            self.sort_handles()
            self.board.select_tool()
            self.board.update_thumb()
            if self.board.HasCapture():
                self.board.ReleaseMouse()


    def start_select_action(self, handle):
        self.points = list(self.points)

    def end_select_action(self, handle):
        pass


    def center_and_bbox(self):
        """Get the bounding rectangle for the polygon"""
        xmin = min(x for x, y in self.points)
        ymin = min(y for x, y in self.points)
        xmax = max(x for x, y in self.points)
        ymax = max(y for x, y in self.points)
        self.bbox = (xmin, ymin, xmax,  ymax)

        a = sum([x for x, y in self.points]) / len(self.points)
        b = sum([y for x, y in self.points]) / len(self.points)
        self.center = (a, b)


    def hit_test(self, x, y):
        """http://ariel.com.au/a/python-point-int-poly.html"""
        if x < self.bbox[0] or x > self.bbox[2] or y < self.bbox[1] or y > self.bbox[3]:
            return False
        n = len(self.points)
        inside = False

        p1x, p1y = self.points[0]
        for i in range(n + 1):
            p2x, p2y = self.points[i % n]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y
        return inside


    def get_handles(self):
        d = lambda x, y: (x - 2, y - 2)
        handles = [d(x[0], x[1]) for x in self.points]
        return handles


    def handle_hit_test(self, x, y):
        for count, handle in enumerate(self.handles):
            if handle.ContainsXY(x, y):
                return count + 1
        return False  # nothing hit


    def resize(self, x, y, handle=None):
        pos = handle - 1
        if pos < 0:
            pos = 0
        #self.points[pos] = (x, y) # - MOVING A POINT
        #if pos == 0:  # first point
        #    self.x, self.y = x, y
        if wx.GetKeyState(wx.WXK_CONTROL) :
            self.rotate((x, y))
            self.x, self.y = self.points[0]  # for the correct offset when moving
        elif wx.GetKeyState(wx.WXK_SHIFT):
            self.rescale(x, y)
            self.x, self.y = self.points[0] 
        else:
            self.points[pos] = (x, y) 
            if pos == 0:  # first point
                self.x, self.y = x, y
        
    def rescale(self, x, y):
        """
        Thanks to Mark Ransom -- http://stackoverflow.com/questions/2014859/
        """
        if not self.orig_click:
            self.orig_click = (x, y)

        orig_click = self.orig_click
        original_distance = math.sqrt((orig_click[0] - self.center[0]) ** 2 + (orig_click[1] - self.center[1]) ** 2)
        current_distance = math.sqrt((x - self.center[0])**2 + (y - self.center[1])**2)
        self.scale_factor = current_distance / original_distance

        for count, point in enumerate(self.original_points):
            dist = (point[0] - self.center[0], point[1] - self.center[1])
            self.points[count] = (self.scale_factor * dist[0] + self.center[0], self.scale_factor * dist[1] + self.center[1])



    def rotate(self, position):
        """
        http://stackoverflow.com/questions/786472/rotate-a-point-by-an-angle
        """
        if not self.orig_click:
            self.orig_click = position

        knobangle = self.find_angle(self.orig_click, self.center)
        mouseangle = self.find_angle(position, self.center)

        angle = knobangle - mouseangle
        self.do_rotate(angle)


    def do_rotate(self, angle):
        """ Rotate the points. Can be called by Image as a rotate preview """
        for x, p in enumerate(self.original_points):
            a = (math.cos(angle) * (p[0] - self.center[0]) - math.sin(angle) *
                                    (p[1] - self.center[1]) + self.center[0])
            b = (math.sin(angle) * (p[0] - self.center[0]) + math.cos(angle) *
                                    (p[1] - self.center[1]) + self.center[1])
            self.points[x] = (a, b)



    def move(self, x, y, offset):
        """Gotta update every point relative to how much the first has moved"""
        super(Polygon, self).move(x, y, offset)
        diff = (x - self.points[0][0] - offset[0], y - self.points[0][1] - offset[1])

        for count, point in enumerate(self.points):
            self.points[count] = (point[0] + diff[0], point[1] + diff[1])


    def sort_handles(self):
        super(Polygon, self).sort_handles()
        self.points = [(float(x), float(y)) for x, y in self.points]
        self.center_and_bbox()
        self.original_points = list(self.points)
        self.orig_click = None

    def find_angle(self, a, b):
        return math.atan2((a[0] - b[0]) , (a[1] - b[1]))

    def get_args(self):
        return [self.points]

    def properties(self):
        return _("Number of points: %s") % len(self.points)

    def draw(self, dc, replay=False, _type="Polygon"):
        super(Polygon, self).draw(dc, replay, _type)

    def preview(self, dc, width, height):
        dc.DrawPolygon(((7, 13), (54, 9), (60, 38), (27, 34)))

    def load(self):
        super(Polygon, self).load()
        self.sort_handles()


#----------------------------------------------------------------------


class Pen(Polygon):
    """
    A free-hand pen. Has been turned into an OverlayShape to allow it to be
    selected and moved.
    """
    tooltip = _("Draw strokes with a brush")
    name = _("Pen")
    icon = "pen"
    hotkey = "p"

    def __init__(self, board, colour, thickness, background=wx.TRANSPARENT,
                 cursor=wx.CURSOR_PENCIL, join=wx.JOIN_ROUND):
        Polygon.__init__(self, board, colour, thickness, background, cursor,
                         join)
        self.time = []  # list of times for each point, for redrawing
        self.background = None
        self.x_tmp = 0
        self.y_tmp = 0


    def left_down(self, x, y):
        self.x = x  # original mouse coords
        self.y = y
        self.x_tmp = x
        self.y_tmp = y


    def left_up(self, x, y):
        if self.points:
            self.board.add_shape(self)
            self.sort_handles()
            if len(self.points) == 1:  # a single click
                self.board.redraw_all()


    def motion(self, x, y):
        self.points.append( [self.x_tmp, self.y_tmp, x, y] )
        self.time.append(time.time())
        self.x_tmp = x
        self.y_tmp = y  # swap for the next call to this function

    def right_up(self, x, y):
        pass

    def sort_handles(self):
        pass#self.center_and_bbox()

    def handle_hit_test(self, x, y):
        pass

    def draw(self, dc, replay=True):
        super(Pen, self).draw(dc, replay, "LineList")

    def get_args(self):
        return [self.points]


    def move(self, x, y, offset):
        """Gotta update every point relative to how much the first has moved"""
        OverlayShape.move(self, x, y, offset)
        diff = (x - self.points[0][0] - offset[0], y - self.points[0][1] - offset[1])

        for count, point in enumerate(self.points):
            self.points[count] = [point[0] + diff[0], point[1] + diff[1],
                                  point[2] + diff[0], point[3] + diff[1]]


    def hit_test(self, x, y):

        bitmap = wx.EmptyBitmap(self.board.area[0], self.board.area[1])
        dc = wx.MemoryDC()
        dc.SelectObject(bitmap)
        dc.SetBackground(wx.WHITE_BRUSH)
        dc.Clear()
        dc.SetPen(wx.Pen(wx.BLACK, self.thickness + 2, wx.SOLID))
        dc.SetBrush(wx.BLACK_BRUSH)
        dc.DrawLineList(self.points)
        pixel = dc.GetPixel(x + 2, y + 2)

        if (pixel.Red() == 0) and (pixel.Green() == 0) and (pixel.Blue() == 0):
            return True
        else:
            return False



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

class Rectangle(OverlayShape):
    """
    The rectangle and its descended classes (ellipse/rounded rect) use an
    overlay as a rubber banding method of drawing itself over other shapes.
    """
    tooltip = _("Draw a rectangle")
    name = _("Rectangle")
    icon = "rectangle"
    hotkey = "r"

    def __init__(self, board, colour, thickness, background=wx.TRANSPARENT):
        OverlayShape.__init__(self, board, colour, thickness, background,
                              join=wx.JOIN_MITER)
        self.width = 0
        self.height = 0
        self.rect = None

    def motion(self, x, y):
        self.width =  x - self.x
        self.height = y - self.y

    def resize(self, x, y, handle=None):
        if handle < CENTER_TOP:
            self.motion(x, y)
        elif handle in [CENTER_TOP, CENTER_BOTTOM]:
            self.height = y - self.y
        elif handle in [CENTER_LEFT, CENTER_RIGHT]:
            self.width = x - self.x

    def get_args(self):
        x, y, w, h = self.x, self.y, self.width, self.height
        args = [min(x, w + x), min(y, h + y), abs(w), abs(h)]
        return args

    def get_handles(self):
        """ ugh. """
        t = round(self.thickness / 2)
        s = HANDLE_SIZE / 2
        x, y, w, h = self.get_args()[:4]  # RoundedRect has 5 args
        return [(x - t - 6, y - t - 6),               # top left
                (x + w + t - 2, y - t - 6),           # top right
                (x - t - 6, y + h + t - 2),           # bottom left
                (x + w + t - 2, y + h + t - 2),       # bottom right

                (x - t - s + (w / 2), y - t - 6),     # top center
                (x + w + t - 2, y - t - s + (h / 2)), # right center
                (x - t - s + (w / 2), y + h + t - 2), # bottom center
                (x - t - 6, y - t - s + (h / 2))]     # left center


    def handle_hit_test(self, x, y):
        """Returns which handle has been clicked on"""
        result = super(Rectangle, self).handle_hit_test(x, y)
        if not result:
            keys = {2: BOTTOM_LEFT, 3: BOTTOM_RIGHT, 4: CENTER_TOP,
                    5: CENTER_RIGHT, 6: CENTER_BOTTOM, 7: CENTER_LEFT}

            for k, v in keys.items():
                if self.handles[k].InsideXY(x, y):
                    return v
            return False
        return result


    def anchor(self, handle):
        """
        Avoids an issue when resizing, anchors shape's x/y point to the opposite
        corner of the corner being dragged.
        I'll be honest - I can't remember what's going on here - it just works!
        """
        r = self.get_args()[:4]

        if handle == TOP_LEFT:
            self.x = r[0] + r[2]
            self.y =  r[1] + r[3]
            self.width = -(r[2] - r[0])
            self.height = -(r[1] - r[1])
        elif handle == BOTTOM_LEFT:
            self.x = r[0] + r[2]
            self.y = r[1]
            self.width = -r[0]
            self.height = -r[1]
        elif handle == TOP_RIGHT:
            self.x = r[0]
            self.y =  r[1] + r[3]
            self.width = -(r[2] - r[0])
            self.height = -(r[1] - r[1])
        elif handle == BOTTOM_RIGHT:
            self.x = r[0]
            self.y = r[1]
            self.width = r[2]
            self.height = r[3]
        elif handle == CENTER_TOP:
            self.y =  r[1] + r[3]
            self.height = -(r[1] - r[1])
        elif handle == CENTER_BOTTOM:
            self.y = r[1]
            self.height = -r[1]
        elif handle == CENTER_LEFT:
            self.x = r[0] + r[2]
            self.width = -r[0]
        elif handle == CENTER_RIGHT:
            self.x = r[0]
            self.width = r[2]

        self.sort_handles()


    def sort_handles(self):
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


    def properties(self):
        return "X: %i, Y: %i, %s %i, %s %i" % (self.x, self.y, _("Width:"),
                                               self.width, _("Height:"), self.height)

    def load(self):
        super(Rectangle, self).load()
        self.sort_handles()

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
    hotkey = "o"
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
    hotkey = "c"

    def __init__(self, board, colour, thickness, background=wx.TRANSPARENT):
        OverlayShape.__init__(self, board, colour, thickness, background)
        self.radius = 1

    def motion(self, x, y):
        self.radius = ((self.x - x) ** 2 + (self.y  - y) ** 2) ** 0.5

    def draw(self, dc, replay=False):
        super(Circle, self).draw(dc, replay, "Circle")

    def preview(self, dc, width, height):
        dc.DrawCircle(width/2, height/2, 15)

    def get_args(self):
        return [self.x, self.y, self.radius]

    def get_handles(self):
        d = lambda x, y: (x - 2, y - 2)
        x, y, r = self.get_args()
        return d(x - r, y - r), d(x- r, y + r), d(x + r, y - r), d(x + r, y + r)

    def properties(self):
        r = _("Radius")
        return "X: %i, Y: %i, %s: %i" % (self.x, self.y, r, self.radius)

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
    hotkey = "u"

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
    hotkey = "l"

    def __init__(self, board, colour, thickness, background=wx.TRANSPARENT):
        OverlayShape.__init__(self, board, colour, thickness, background)
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


    def draw(self, dc, replay=False):
        super(Line, self).draw(dc, replay, "Line")

    def get_args(self):
        return [self.x, self.y, self.x2, self.y2]

    def properties(self):
        return "X: %i, Y: %i, X2: %i, Y2: %i" % (self.x, self.y, self.x2, self.y2)

    def move(self, x, y, offset):
        self.x = x - offset[0][0]
        self.y = y - offset[0][1]
        self.x2 = x - offset[1][0]
        self.y2 = y - offset[1][1]

    def resize(self, x, y, handle=None):
        if handle == TOP_LEFT:
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

class Arrow(Line):
    tooltip = _("Draw an arrow")
    name = _("Arrow")
    hotkey = "a"
    icon = "arrow"

    def draw(self, dc, replay=False):
        """
        From http://lifshitz.ucdavis.edu/~dmartin/teach_java/slope/arrows.html
        """
        if not replay:
            odc = wx.DCOverlay(self.board.overlay, dc)
            odc.Clear()
        dc.SetPen(wx.Pen(self.colour, self.thickness))
        dc.SetBrush(self.brush)

        x0, x1, y0, y1 = self.x, self.x2, self.y, self.y2
        deltaX = self.x2 - self.x
        deltaY = self.y2 - self.y
        frac = 0.05

        dc.DrawLine(*self.get_args())
        dc.DrawLine(x0 + ((.75 - frac) * deltaX + frac * deltaY),
                    y0 + ((.75 - frac) * deltaY - frac * deltaX), x1, y1)
        dc.DrawLine(x0 + ((.75 - frac) * deltaX - frac * deltaY),
                    y0 + ((.75 - frac) * deltaY + frac * deltaX), x1, y1)

        if self.selected:
            self.draw_selected(dc)
        if not replay:
            del odc


    def preview(self, dc, width, height):
        dc.DrawLine(10, height / 2, width - 10, height / 2)
        dc.DrawLine(width - 10, height / 2, width - 20, (height / 2) - 6)
        dc.DrawLine(width - 10, height / 2, width - 20, (height / 2) + 6)

#---------------------------------------------------------------------

class Media(Tool):
    tooltip = _("Insert media and audio")
    name = _("Media")
    hotkey = "m"
    icon = "media"

    def __init__(self, board, colour, thickness, background=wx.TRANSPARENT,
                 cursor=wx.CURSOR_ARROW):
        Tool.__init__(self, board, colour, thickness, background, cursor)
        self.filename = None
        self.mc = None  # media panel

    def left_down(self, x, y):
        self.x = x
        self.y = y
        self.board.medias.append(self)
        self.make_panel()
        self.board.select_tool()

    def make_panel(self):
        if not self.mc:
            self.mc = MediaPanel(self.board, (self.x, self.y), self)
            if self.filename:
                self.mc.do_load_file(self.filename)

    def properties(self):
        return _("Loaded file")+ ": " + str(self.filename)

    def save(self):
        super(Media, self).save()
        self.remove_panel()

    def remove_panel(self):
        if self.mc:
            self.mc.Destroy()
            self.mc = None

    def load(self):
        super(Media, self).load()
        self.make_panel()


#---------------------------------------------------------------------

class Eraser(Pen):
    """
    Erases stuff. Has a custom cursor from a drawn rectangle on a DC, turned
    into an image then into a cursor.
    """
    tooltip = _("Erase a drawing to the background")
    name = _("Eraser")
    icon = "eraser"
    hotkey = "e"

    def __init__(self, board, colour, thickness, background=wx.TRANSPARENT):
        cursor = self.make_cursor(thickness)
        Pen.__init__(self, board, (255, 255, 255), thickness + 6, background,
                     cursor)


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

        img.SetOptionInt(wx.IMAGE_OPTION_CUR_HOTSPOT_X, (thickness + 7) / 2)
        img.SetOptionInt(wx.IMAGE_OPTION_CUR_HOTSPOT_Y, (thickness + 7) / 2)

        cursor = wx.CursorFromImage(img)
        return cursor


    def preview(self, dc, width, height):
        thickness = self.thickness + 1
        dc.SetPen(wx.Pen((0, 0, 0), 1, wx.SOLID))
        dc.DrawRectangle(15, 7, thickness + 1,  thickness + 1)

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
    hotkey = "d"

    def __init__(self, board, colour, thickness, background=wx.TRANSPARENT):
        Tool.__init__(self, board, colour, thickness, background, wx.CURSOR_CROSS)

    def left_down(self, x, y):
        dc = wx.BufferedDC(None, self.board.buffer)  # create tmp DC
        colour = dc.GetPixel(x, y)  # get colour
        board = self.board.gui
        board.control.colour.SetColour(colour)
        board.util.colour = colour
        board.control.preview.Refresh()

    def right_up(self, x, y):
        dc = wx.BufferedDC(None, self.board.buffer)  # create tmp DC
        colour = dc.GetPixel(x, y)  # get colour
        board = self.board.gui
        board.control.background.SetColour(colour)
        board.util.background = colour
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
    hotkey = "t"

    def __init__(self, board, colour, thickness, background=wx.TRANSPARENT):
        OverlayShape.__init__(self, board, colour, thickness, background,
                              wx.CURSOR_IBEAM)
        self.font = None
        self.text = ""
        self.font_data = ""
        self.extent = (0, 0)

    def handle_hit_test(self, x, y):
        pass

    def resize(self, x, y, handle=None):
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
        dlg = TextInput(self.board.gui, text=self.text)

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
            return True


    def draw(self, dc, replay=False):
        if not self.font:
            self.restore_font()
        dc.SetFont(self.font)
        dc.SetTextForeground(self.colour)
        if self.background != wx.TRANSPARENT:
            dc.SetBackground(wx.Brush(self.background))
        super(Text, self).draw(dc, replay, "Label")


    def restore_font(self):
        """Updates the text's font to the saved font data"""
        self.font = wx.FFont(0, 0)
        self.font.SetNativeFontInfoFromString(self.font_data)
        if not self.font.IsOk():
            f = wx.SystemSettings.GetFont(wx.SYS_SYSTEM_FONT)
            self.font = wx.FFont(f.GetPointSize(), f.GetFamily())


    def find_extent(self):
        """Finds the width/height of the object's text"""
        dc = wx.WindowDC(wx.Frame(None))
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

    def properties(self):
        return "%s -- X: %i, Y: %i" % (self.text[:20], self.x, self.y)

    def preview(self, dc, width, height):
        dc.SetTextForeground(self.colour)
        dc.DrawText("abcdef", 15, height / 2 - 10)


    def save(self):
        super(Text, self).save()
        self.font = None


    def load(self):
        super(Text, self).load()
        self.restore_font()


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
    hotkey = "n"

    def __init__(self, board, colour, thickness, background=wx.TRANSPARENT):
        Text.__init__(self, board, colour, thickness, background)
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
        if add_note:
            self.board.gui.notes.add_note(self, self.board.gui.tab_count - 1)


#----------------------------------------------------------------------


class Image(OverlayShape):
    """
    When being pickled, the image reference will be removed.
    """
    name = _("Image")
    def __init__(self, board, image, path):
        OverlayShape.__init__(self, board, wx.BLACK, 1)
        self.image = image  # of type wx.Bitmap
        self.path = path  # not really needed anymore
        self.filename = None  # used to restore image on load
        if path:
            self.filename = os.path.basename(path)
        self.resizing = False
        self.img = wx.ImageFromBitmap(image)  # original wx.Image to rotate/scale
        self.angle = 0
        self.img_size = None
        self.outline = None  # Rectangle/Polygon, used to rotate/resize
        self.dragging = False  # controls whether to draw the outline
        self.orig_click = None
        self.rotate_handle = None  # wx.Rect


    def left_down(self, x, y):
        self.x = x
        self.y = y
        self.board.add_shape(self)
        self.board.check_resize((self.image.GetWidth(), self.image.GetHeight()))
        self.sort_handles()

        dc = wx.BufferedDC(None, self.board.buffer)
        self.draw(dc)
        self.board.redraw_dirty(dc)


    def sort_handles(self):
        """Sets the internal image that will be used to rotate, and its mask"""
        super(Image, self).sort_handles()
        if not self.img:
            self.img = wx.ImageFromBitmap(self.image)

        self.rotate_handle = wx.Rect(self.x + self.image.GetWidth() / 2 - 6,
                                     self.y + self.image.GetHeight() / 2 - 6,
                                     HANDLE_SIZE, HANDLE_SIZE)

        if not self.img.HasAlpha():  # black background otherwise
            self.img.InitAlpha()


    def handle_hit_test(self, x, y):
        """Returns which handle has been clicked on"""
        result = super(Image, self).handle_hit_test(x, y)
        if not result:
            if self.rotate_handle.ContainsXY(x, y):
                return HANDLE_ROTATE
        return result  # nothing hit


    def draw_selected(self, dc):
        super(Image, self).draw_selected(dc)
        dc.SetBrush(wx.Brush((0, 255, 0)))
        dc.DrawCircle(self.x + self.image.GetWidth() / 2,
                      self.y + self.image.GetHeight() / 2, 6)


    def resize(self, x, y, handle=None):
        """Rotate the image"""
        if handle == HANDLE_ROTATE:
            self.rotate((x, y))
        else:
            self.rescale(x, y, handle)


    def rescale(self, x, y, handle):
        self.outline.resize(x, y, handle)
        if self.outline.width < 10:
            self.outline.width = 10
        if self.outline.height < 10:
            self.outline.height = 10


    def rotate(self, position):
        """Rotate the outline."""
        if not self.orig_click:
            self.orig_click = position

        knob_angle = self.outline.find_angle(self.orig_click, self.outline.center)
        mouse_angle = self.outline.find_angle(position, self.outline.center)
        self.angle = knob_angle - mouse_angle

        self.outline.do_rotate(self.angle)


    def start_select_action(self, handle):
        if handle:
            self.dragging = True
        if not handle:
            overlay = self.board.overlay  # init.ing the rect resets the overlay

        if handle == HANDLE_ROTATE:
            self.outline = Polygon(self.board, wx.BLACK, 2)
            self.outline.x = self.x
            self.outline.y = self.y
            self.outline.points.append((self.x, self.y))
            self.outline.points.append((self.x + self.image.GetWidth(), self.y))
            self.outline.points.append((self.x + self.image.GetWidth(), self.y + + self.image.GetHeight()))
            self.outline.points.append((self.x, self.y + self.image.GetHeight()))
        elif handle in [TOP_LEFT, TOP_RIGHT, BOTTOM_LEFT, BOTTOM_RIGHT]:
            self.outline = Rectangle(self.board, wx.BLACK, 2)
            self.outline.x = self.x
            self.outline.y = self.y
            self.outline.width = self.image.GetWidth()
            self.outline.height = self.image.GetHeight()

        if not handle:
            self.board.overlay = overlay  # so restore it
        else:
            self.outline.sort_handles()



    def end_select_action(self, handle):
        """Performs the rescale/rotation, resets attributes"""
        if self.outline and self.dragging:
            if handle == HANDLE_ROTATE:
                img = self.img.Rotate(-self.angle, self.outline.center)
            else:
                img = wx.BitmapFromImage(self.img)
                img = wx.ImageFromBitmap(img)
                img.Rescale(self.outline.width, self.outline.height, wx.IMAGE_QUALITY_HIGH)

            self.image = wx.BitmapFromImage(img)

        self.dragging = False
        self.orig_click = None
        self.angle = 0
        self.outline = None
        self.sort_handles()
        self.board.redraw_all()


    def draw(self, dc, replay=False):
        super(Image, self).draw(dc, replay, "Bitmap")
        if self.dragging:
            self.outline.draw(dc, replay)


    def get_args(self):
        return [self.image, self.x, self.y]


    def properties(self):
        a, b = "", ""
        if self.filename:
            a, b = _("Filename:"), self.filename
        return "X: %i, Y: %i %s %i %s %i %s %s" % (self.x, self.y, _("Width:"),
                                            self.image.GetWidth(), _("Height:"),
                                            self.image.GetHeight(), a, b)

    def get_handles(self):
        d = lambda x, y: (x - 2, y - 2)
        img = self.image
        x, y, w, h = self.x, self.y, img.GetWidth(), img.GetHeight()
        return d(x, y), d(x + w, y), d(x, y + h), d(x + w, y + h)


    def save(self):
        super(Image, self).save()
        self.image = None
        self.img = None


    def load(self):
        super(Image, self).load()
        if not hasattr(self, "outline"):
            self.outline = None
        if not hasattr(self, "dragging"):
            self.dragging = False

        if not hasattr(self, "filename") or not self.filename:
            self.filename = os.path.basename(self.path)
            if self.filename.find("\\"):  # loading windows file on linux
                self.filename = ntpath.basename(self.path)

        if not self.board.gui.util.is_zipped:
            if self.path and os.path.exists(self.path):
                self.image = wx.Bitmap(self.path)
            else:
                self.image = wx.EmptyBitmap(0, 0)
                wx.MessageBox(_("Path for the image %s not found.") % self.path)
        else:
            try:
                data = self.board.gui.util.zip.read("data/" + self.filename)
                stream = cStringIO.StringIO(data)
                self.image = wx.BitmapFromImage(wx.ImageFromStream(stream))

            except KeyError:
                self.image = wx.EmptyBitmap(0, 0)
                wx.MessageBox(_("File %s not found in the save") % self.filename)

        self.img = wx.ImageFromBitmap(self.image)
        self.colour = wx.BLACK
        self.sort_handles()


    def hit_test(self, x, y):
        width, height = self.image.GetSize()
        rect = wx.Rect(self.x, self.y, width, height)

        if rect.ContainsXY(x, y):
            return True
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
    hotkey = "s"

    def __init__(self, board, colour, thickness, background=wx.TRANSPARENT):
        Tool.__init__(self, board, (0, 0, 0), 1, background, cursor=wx.CURSOR_ARROW)
        self.shape = None
        self.dragging = False
        self.undone = False  # Adds an undo point once per class
        self.anchored = False  # Anchor shape's x point -once-, when resizing
        self.handle = None  # handle that was clicked on (if any)
        self.offset = (0, 0)


    def left_down(self, x, y):
        """
        First, check the selected shape (which will be drawn on top of the 
        others) so that's selected first.
        """
        self.board.redraw_all()
        if self.board.selected:
            if self.check_for_hit(self.board.selected, x, y):
                return
        
        for shape in reversed(self.board.shapes):
            if self.check_for_hit(shape, x, y):
                break  # breaking is vital to selecting the correct shape
        else:
            self.board.deselect()


    def check_for_hit(self, shape, x, y):
        """
        Sees if a shape is underneath the mouse coords, and allows the shape to
        be re-dragged to place
        """        
        found = False
        handle = shape.handle_hit_test(x, y)  # test handle before area

        if handle:
            self.handle = handle
            found = True
        elif shape.hit_test(x, y):
            found = True

        if found:
            self.board.overlay = wx.Overlay()
            self.shape = shape
            self.dragging = True
            self.offset = self.shape.offset(x, y)

            if self.board.selected:
                self.board.deselect()
            self.board.selected = shape
            shape.selected = True

            x = self.board.shapes.index(shape)
            self.board.shapes.pop(x)
            self.board.redraw_all()  # hide 'original'
            self.board.shapes.insert(x, shape)
            shape.draw(self.board.get_dc(), False)  # draw 'new'

            if shape.background == wx.TRANSPARENT:
                self.board.gui.control.transparent.SetValue(True)
                self.board.gui.menu.Check(ID_TRANSPARENT, True)
            else:
                self.board.gui.control.transparent.SetValue(False)
                self.board.gui.menu.Check(ID_TRANSPARENT, False)
            
        return found
    

    def right_up(self, x, y):
        """Pops up a shape menu if a shape was clicked on"""
        found = None
        for shape in reversed(self.board.shapes):
            if shape.handle_hit_test(x, y):
                found = shape
            elif shape.hit_test(x, y):
                found = shape
            if found:
                break
            
        if not found:
            return

        selected = None
        if self.board.selected:
            selected = self.board.selected
        self.board.selected = found
        self.board.gui.PopupMenu(ShapePopup(self.board, self.board.gui, found))

        if selected:
            self.board.selected = selected
        if not found.selected:
            self.board.selected = None


    def double_click(self, x, y):
        if isinstance(self.board.selected, Text):
            self.dragging = False
            self.board.selected.edit()


    def motion(self, x, y):
        if self.dragging:
            if not self.undone:  # add a single undo point, not one per call
                self.board.add_undo()
                self.undone = True
                self.shape.start_select_action(self.handle)
            if not self.handle:  # moving
                self.shape.move(x, y, self.offset)
            else:
                if not self.anchored:  # don't want to keep anchoring
                    self.shape.anchor(self.handle)
                    self.anchored = True
                self.shape.resize(x, y, self.handle)


    def draw(self, dc, replay=False):
        if self.dragging:
            self.shape.draw(dc, False)


    def left_up(self, x, y):
        if self.dragging:
            self.shape.sort_handles()
            self.shape.end_select_action(self.handle)

        self.board.update_thumb()
        self.board.select_tool()

    def preview(self, dc, width, height):
        dc.DrawBitmap(wx.Bitmap(os.path.join(self.board.gui.util.get_path(), "images",
                                   "icons", "cursor.png")), width / 2 - 5, 12)


#----------------------------------------------------------------------

class BitmapSelect(Rectangle):
    """
    Rectangle selection tool, used to select a region to copy/paste. When it
    is drawn it is stored inside the current tab as an instance attribute,
    not in the shapes list. It is then drawn separately from other shapes
    """
    tooltip = _("Select a rectangle region to copy as a bitmap")
    name = _("Bitmap Select")
    icon = "select-rectangular"
    hotkey = "b"

    def __init__(self, board, colour, thickness, background=wx.TRANSPARENT):
        Rectangle.__init__(self, board, (0, 0, 0), 1)

    def left_down(self, x, y):
        super(BitmapSelect, self).left_down(x, y)
        self.board.deselect()
        self.board.copy = None
        self.board.redraw_all()
        self.board.copy = self


    def draw(self, dc, replay=False):
        if not replay:
            odc = wx.DCOverlay(self.board.overlay, dc)
            odc.Clear()

        if not replay and self.board.gui.util.config['bmp_select_transparent']:
            dc = wx.GCDC(dc)
            dc.SetBrush(wx.Brush(wx.Color(0, 0, 255, 50)))  # light blue
            dc.SetPen(wx.Pen(self.colour, self.thickness, wx.SOLID))
        else:
            dc.SetPen(wx.Pen(self.colour, self.thickness, wx.SHORT_DASH))
            dc.SetBrush(wx.TRANSPARENT_BRUSH)
        dc.DrawRectangle(*self.get_args())

        if not replay:
            del odc


    def left_up(self, x, y):
        """ Doesn't affect the shape list """
        if not (x != self.x and y != self.y):
            self.board.copy = None

    def preview(self, dc, width, height):
        dc.SetPen(wx.BLACK_DASHED_PEN)
        dc.SetBrush(wx.TRANSPARENT_BRUSH)
        dc.DrawRectangle(10, 10, width - 20, height - 20)


#----------------------------------------------------------------------

class Zoom(Tool):
    """
    Zooms in and out on the canvas, by setting the user scale in the Whyteboard
    tab
    """
    tooltip = _("Zoom in and out of the canvas")
    name = _("Zoom")
    icon = "zoom"
    hotkey = "z"

    def __init__(self, board, colour, thickness, background=wx.TRANSPARENT):
        Tool.__init__(self, board, (0, 0, 0), 1, background, wx.CURSOR_MAGNIFIER)


    def left_up(self, x, y):
        x = self.board.scale
        new = (x[0] - 0.1, x[1] - 0.1)
        self.board.scale = new
        self.board.redraw_all()

    def right_up(self, x, y):
        x = self.board.scale
        new = (x[0] + 0.1, x[1] + 0.1)
        self.board.scale = new
        self.board.redraw_all()

#---------------------------------------------------------------------

class Flood(Tool):
    """
    Zooms in and out on the canvas, by setting the user scale in the Whyteboard
    tab
    """
    tooltip = _("Flood fill an area")
    name = _("Flood Fill")
    icon = "flood"
    hotkey = "f"

    def __init__(self, board, colour, thickness):
        Tool.__init__(self, board, colour, 1)


    def left_down(self, x, y):
        self.x = x
        self.y = y
        self.board.draw_shape(self)
        self.board.add_shape(self)

    def draw(self, dc, replay=False):
        dc.SetPen(self.pen)
        dc.SetBrush(wx.Brush(self.colour))
        dc.FloodFill(self.x, self.y, dc.GetPixel(self.x, self.y), wx.FLOOD_SURFACE)

    def preview(self, dc, width, height):
        dc.SetBrush(wx.Brush(self.colour))
        dc.DrawRectangle(10, 10, width - 20, height - 20)

#---------------------------------------------------------------------

def find_inverse(colour):
    """ Invert an RGB colour """
    if not isinstance(colour, wx.Colour):
        c = colour
        colour = wx.Colour()
        try:
            colour.SetFromName(c)
        except TypeError:
            colour.Set(*c)
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
items = [Pen, Eraser, Rectangle, RoundedRect, Ellipse, Circle, Polygon, Line, Arrow, Text,
         Note, Media, Eyedrop, BitmapSelect, Select]