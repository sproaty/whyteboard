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
This module contains the Canvas class, a window that can be drawn upon. Each
Canvas panel gets added to a tab in the GUI, and each Canvas maintains
a list of undo/redo actions for itself; thus each Canvas tab on the GUI has
its own undo/redo.

The canvas to be drawn on is managed by a buffer bitmap, and the rest of the
area is flooded with a grey, to indicate it is the background. This background
can be grabbed with the mouse to resize the canvas' size. If the canvas is
larger than the client size, then scrollbars are displayed, and a slight
"border" is shown around the canvas - this can be grabbed to resize.
"""

import os
import copy

import wx
#import wx.lib.wxcairo as wxcairo

from lib.dragscroller import DragScroller
from lib.pubsub import pub

from functions import get_image_path
from tools import (Highlighter, Image, Line, Media, Note, OverlayShape, Polygon,
                   Select, Text, TOP_LEFT, TOP_RIGHT, BOTTOM_LEFT,
                   BOTTOM_RIGHT, CENTER_TOP, CENTER_RIGHT, CENTER_BOTTOM,
                   CENTER_LEFT, HANDLE_ROTATE, EDGE_TOP, EDGE_RIGHT, EDGE_LEFT,
                   EDGE_BOTTOM)

#----------------------------------------------------------------------

EDGE = 15    # distance from canvas edge before shape will scroll canvas
TO_MOVE = 5  # pixels shape will cause canvas to scroll

# area user clicked on canvas to resize
RIGHT = 1
DIAGONAL = 2
BOTTOM = 3

DRAG_LEFT = 1
DRAG_RIGHT = 2
DRAG_UP = 3
DRAG_DOWN = 4



class Canvas(wx.ScrolledWindow):
    """
    The drawing frame of the application. References to self.shape.drawing are
    for the Polygon tool, mainly avoiding isinstance() checks
    """
    CANVAS_BORDER = 15  # border pixels in size (overridable by user)

    def __init__(self, tab, gui, area):
        """
        Initalise the window, class variables and bind mouse/paint events
        """
        wx.ScrolledWindow.__init__(self, tab, style=wx.NO_FULL_REPAINT_ON_RESIZE | wx.CLIP_CHILDREN)
        self.SetVirtualSizeHints(2, 2)
        self.SetScrollRate(1, 1)
        self.SetBackgroundColour('Grey')
        self.SetDropTarget(CanvasDropTarget())

        if os.name == "nt":
            self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)  # no flicking on Win!
        else:
            self.ClearBackground()

        self.area = area
        self.scroller = DragScroller(self)
        self.overlay = wx.Overlay()
        self.buffer = wx.EmptyBitmap(*self.area)
        #self.hit_buffer = wx.EmptyBitmap(*self.area)  # used by pen for hit test
        #dc = wx.BufferedDC(None, self.hit_buffer, wx.BUFFER_VIRTUAL_AREA)
        #dc.SetBackground(wx.WHITE_BRUSH)
        #dc.Clear()

        self.gui = gui
        self.scale = (1.0, 1.0)
        self.shapes = []  # list of shapes for re-drawing/saving
        self.shape = None  # currently selected shape *to draw with*
        self.medias = []  # list of Media panels
        self.selected = None  # selected shape *with Select tool*
        self.text = None  # current Text object for redraw all
        self.copy = None  # BitmapSelect instance
        self.resizing = False
        self.cursor_control = False  # toggle resize canvas cursor on/off
        self.resize_direction = None
        self.undo_list = []
        self.redo_list = []
        self.drawing = False
        self.prev_drag = (0, 0)

        img = wx.Image(get_image_path(u"cursors", u"rotate"))
        self.rotate_cursor = wx.CursorFromImage(img)
        self.gui.change_tool(canvas=self)
        self.redraw_all()

        self.Bind(wx.EVT_SIZE, self.on_size)
        self.Bind(wx.EVT_LEFT_DOWN, self.left_down)
        self.Bind(wx.EVT_LEFT_UP, self.left_up)
        self.Bind(wx.EVT_RIGHT_UP, self.right_up)
        self.Bind(wx.EVT_LEFT_DCLICK, self.left_double)
        self.Bind(wx.EVT_MIDDLE_DOWN, self.middle_down)
        self.Bind(wx.EVT_MIDDLE_UP, self.middle_up)
        self.Bind(wx.EVT_MOTION, self.motion)
        self.Bind(wx.EVT_PAINT, self.on_paint)

        pub.subscribe(self.set_border, 'canvas.set_border')



    def left_down(self, event):
        """Starts drawing"""
        x, y = self.convert_coords(event)
        if os.name == "nt" and not isinstance(self.shape, Media) and not self.shape.drawing:
            self.CaptureMouse()
        if not self.shape.drawing and self.check_resize_direction(x, y):  # don't draw outside canvas
            self.resizing = True
            return

        if not isinstance(self.shape, Select) and self.selected:
            self.deselect_shape()

        self.shape.left_down(x, y)
        #  Crashes without the Text check
        if not isinstance(self.shape, (Text, Media)):
            self.drawing = True


    def motion(self, event):
        """
        Checks if the canvas can be updated, changes the cursor to show it can
        Updates the shape if the user is drawing. Indicate shape may be changed
        when using Select tool by changing the cursor
        """
        x, y = self.convert_coords(event)
        if self.resizing:
            self.resize((x, y), self.resize_direction)
            return
        else:
            if not self.check_mouse_for_resize(x, y):
                return

        self.gui.SetStatusText(u" %s, %s" % (x, y))

        if self.drawing or self.shape.drawing:
            self.shape.motion(x, y)
            if not self.shape.drawing:  # polygon
                self.draw_shape(self.shape)
        elif isinstance(self.shape, Select):  # change cursor to indicate action
            self.select_tool_cursor(x, y)


    def left_up(self, event):
        """
        Called when the left mouse button is released.
        """
        if os.name == "nt" and not self.shape.drawing:
            if self.HasCapture():
                self.ReleaseMouse()

        if self.resizing:
            self.resizing = False
            self.redraw_all(True)  # update thumb for new canvas size
            self.Layout()
            if self.copy:
                self.draw_shape(self.copy)  # draw back the GCDC
            return
        if self.drawing or isinstance(self.shape, Text):
            before = len(self.shapes)
            self.shape.left_up(*self.convert_coords(event))
            if not isinstance(self.shape, Media):
                if len(self.shapes) - before:
                    pub.sendMessage('canvas.change_tool')
                    pub.sendMessage('thumbs.update_current')
            self.drawing = False


    def right_up(self, event):
        """Called when the right mouse button is released - used for zoom"""
        self.shape.right_up(*self.convert_coords(event))


    def left_double(self, event):
        """Double click for the Select tool - edit text"""
        self.shape.double_click(*self.convert_coords(event))


    def set_border(self, border_size):
        self.CANVAS_BORDER = border_size
        self.resize(self.area)


    def select_tool_cursor(self, x, y):
        if self.selected:
            if self.select_tool_cursor_change(self.selected, x, y):
                return

        for shape in reversed(self.shapes):
            if self.select_tool_cursor_change(shape, x, y):
                break
        else:
            self.change_cursor()


    def select_tool_cursor_change(self, shape, x, y):
        res = shape.handle_hit_test(x, y)
        ret = True
        if res and isinstance(shape, (Line, Polygon)):
            if wx.GetKeyState(wx.WXK_SHIFT):
                self.set_cursor(wx.CURSOR_SIZENWSE)
            elif wx.GetKeyState(wx.WXK_CONTROL):
                self.SetCursor(self.rotate_cursor)
            else:
                self.set_cursor(wx.CURSOR_SIZING)

        elif res == HANDLE_ROTATE:
            self.SetCursor(self.rotate_cursor)
        elif res in [TOP_LEFT, BOTTOM_RIGHT]:
            self.set_cursor(wx.CURSOR_SIZENWSE)
        elif res in [TOP_RIGHT, BOTTOM_LEFT]:
            self.set_cursor(wx.CURSOR_SIZENESW)
        elif res in [CENTER_TOP, CENTER_BOTTOM]:
            self.set_cursor(wx.CURSOR_SIZENS)
        elif res in [CENTER_LEFT, CENTER_RIGHT]:
            self.set_cursor(wx.CURSOR_SIZEWE)
        elif shape.hit_test(x, y):
            self.set_cursor(wx.CURSOR_HAND)
        else:
            ret = False
        return ret

    def set_cursor(self, cursor):
        self.SetCursor(wx.StockCursor(cursor))


    def check_mouse_for_resize(self, x, y):
        """
        Sees if the user's mouse is outside of the canvas, and updates the
        cursor if it's in a different resizable area than it previously was
        Returns the cursor to its normal state if it's moved back in
        """
        direction = self.check_resize_direction(x, y)
        if not self.drawing and direction and not self.shape.drawing:
            if not self.resize_direction:
                self.resize_direction = direction
            if not self.cursor_control or direction != self.resize_direction:
                self.resize_direction = direction
                self.cursor_control = True
                self.set_resize_cursor(direction) # change cursor
            return False
        else:
            if self.cursor_control:
                self.change_cursor()
                self.cursor_control = False
                return False
        return True


    def check_resize_direction(self, x, y):
        """Which direction the canvas can be resized in, if any"""
        if x > self.area[0] and y > self.area[1]:
            return DIAGONAL
        elif x > self.area[0]:
            return RIGHT
        elif y > self.area[1]:
            return BOTTOM
        return False


    def set_resize_cursor(self, direction):
        cursors = {DIAGONAL: wx.CURSOR_SIZENWSE, RIGHT: wx.CURSOR_SIZEWE,
                   BOTTOM: wx.CURSOR_SIZENS}
        self.SetCursor(wx.StockCursor(cursors.get(direction)))



    def resize(self, size, direction=None):
        """ Performs the canvas resizing. Size = (w, h) tuple """
        if size[0] < 1 or size[1] < 1:
            return

        if direction == RIGHT:
            size = (size[0], self.area[1])
            self.Scroll(self.GetVirtualSizeTuple()[0], -1)
        elif direction == BOTTOM:
            size = (self.area[0], size[1])
            self.Scroll(-1, size[1])
        elif direction is not None:
            self.Scroll(*size)

        self.buffer = wx.EmptyBitmap(*size)
        self.area = size
        size = (size[0] + self.CANVAS_BORDER, size[1] + self.CANVAS_BORDER)
        self.SetVirtualSize(size)
        self.redraw_all(resizing=True)

#        self.buffer, self.oldbuffer = wx.EmptyBitmap(*size), self.buffer
#        dc = wx.BufferedDC(None, self.buffer)
#        dc.DrawBitmap(self.oldbuffer, 0, 0)
#
#        self.area = size
#        size = (size[0] + CANVAS_BORDER, size[1] + CANVAS_BORDER)# + 20)
#        self.SetVirtualSize(size)
#
#        x1, y1 = self.oldbuffer.GetSize()
#        x2, y2 = self.buffer.GetSize()
#        if x1 > x2 and y1 > y2:
#            self.Refresh()
#        else:
#            clip = wx.Region(0, 0, *size)
#            bufrect = wx.Rect(0, 0, *self.oldbuffer.GetSize())
#            clip.SubtractRect(bufrect)
#            dc.SetClippingRegionAsRegion(clip)
#            dc.Clear()
#            self.redraw_all(dc=dc)


    def redraw_dirty(self, dc):
        """ Figure out what part of the window to refresh. """
        x1, y1, x2, y2 = dc.GetBoundingBox()
        rect = wx.Rect()
        rect.SetTopLeft(self.CalcScrolledPosition(x1, y1))
        rect.SetBottomRight(self.CalcScrolledPosition(x2, y2))
        self.RefreshRect(rect.Inflate(2, 2))


    def redraw_all(self, update_thumb=False, dc=None, resizing=False):
        """
        Redraws all shapes that have been drawn. self.text is used to show text
        characters as they're being typed, as new Text/Note objects have not
        been added to self.shapes at this point.
        dc is used as the DC for printing.
        """
        if not dc:
            dc = wx.BufferedDC(None, self.buffer)
            dc.Clear()

        for s in self.shapes:
            if not resizing:
                s.draw(dc, True)
            else:
                if not isinstance(s, Highlighter):
                    s.draw(dc, True)

        if self.text:
            self.text.draw(dc, True)
        if self.copy:
            self.copy.draw(dc, True)
        self.Refresh()
        if update_thumb:
            pub.sendMessage('thumbs.update_current')


    def change_tool(self):
        if self.HasCapture():
            self.ReleaseMouse()
        self.change_cursor()


    def change_cursor(self):
        if isinstance(self.shape.cursor, wx.Cursor):
            self.SetCursor(self.shape.cursor)
        else:
            self.SetCursor(wx.StockCursor(self.shape.cursor))


    def add_shape(self, shape):
        """ Adds a shape to the "to-draw" list. """
        self.add_undo()
        self.shapes.append(shape)

        if self.selected:
            self.deselect_shape()
            self.redraw_all()
        if self.text:
            self.text = None
        if self.copy:
            self.copy = None
            self.redraw_all()


    def add_undo(self):
        """Creates an undo point. NEED to change this for memory improvements"""
        l = [copy.copy(x) for x in self.shapes]
        self.undo_list.append(l)

        if self.redo_list:
            self.redo_list = []
        pub.sendMessage('gui.mark_unsaved')


    def undo(self):
        """ Undoes an action, and adds it to the redo list. """
        self.perform(self.undo_list, self.redo_list)

    def redo(self):
        """ Redoes an action, and adds it to the undo list. """
        self.perform(self.redo_list, self.undo_list)


    def perform(self, list_a, list_b):
        """ perform undo/redo. list_a: to remove from / list b: append to """
        if not list_a:
            return
        list_b.append(list(self.shapes))
        self.shapes = list_a.pop()
        self.deselect_shape()
        self.redraw_all(True)

        pub.sendMessage('note.delete_sheet_items')  # lazy way of doing things...
        for x in self.shapes:
            if isinstance(x, Note):
                pub.sendMessage('note.add', note=x)
        pub.sendMessage('gui.mark_unsaved')


    def restore_sheet(self, shapes, undo_list, redo_list, size, medias, viewport):
        """
        Restores itself (e.g. from undoing closing a sheet.)
        """
        self.shapes = shapes
        self.undo_list = undo_list
        self.redo_list = redo_list
        self.medias = medias

        for media in medias:
            media.canvas = self
            media.make_panel()

        for shape in shapes:
            shape.canvas = self
            if isinstance(shape, Note):
                pub.sendMessage('note.add', note=shape)

        wx.Yield()
        self.resize(size)
        self.Scroll(viewport[0], viewport[1])
        pub.sendMessage('thumbs.update_current')


    def toggle_transparent(self):
        """Toggles the selected item's transparency"""
        if not self.selected or isinstance(self.selected, (Media, Image, Text)):
            return
        self.add_undo()
        val = wx.TRANSPARENT

        if self.selected.background == wx.TRANSPARENT:
            val = self.gui.get_background_colour()

        self.selected.background = val
        self.selected.make_pen()
        self.redraw_all(True)


    def delete_selected(self):
        """Deletes the selected shape"""
        if not self.selected:
            return

        if isinstance(self.selected, Media):
            self.selected.remove_panel()
        else:
            if isinstance(self.selected, Note):
                self.gui.notes.tree.Delete(self.selected.tree_id)
            self.add_undo()
            self.shapes.remove(self.selected)

        self.selected = None
        self.redraw_all(True)


    def clear(self, keep_images=False):
        """ Removes all shapes from the 'to-draw' list. """
        if not self.medias and not self.shapes:
            return

        for m in self.medias:
            m.remove_panel()
        self.medias = []
        images = []

        if self.shapes:
            self.add_undo()
            if keep_images:
                for x in self.shapes:
                    if isinstance(x, Image):
                        images.append(x)

        self.shapes = images
        self.redraw_all(update_thumb=True)


    def drag_direction(self, x, y):
        """
        Work out the direction a shape's being moved in so that we don't scroll
        the canvas as a shape is being dragged away from a canvas edge.
        """
        direction = []

        if self.prev_drag[0] > x:
            direction.append(DRAG_LEFT)
        elif self.prev_drag[0] < x:
            direction.append(DRAG_RIGHT)
        if self.prev_drag[1] < y:
            direction.append(DRAG_DOWN)
        elif self.prev_drag[1] > y:
            direction.append(DRAG_UP)

        self.prev_drag = (x, y)
        return direction


    def shape_near_canvas_edge(self, x, y, direction, moving=False):
        """
        Check that the x/y coords is within X pixels from the edge of the canvas
        and scroll the canvas accordingly. If the shape is being moved, we need
        to check specific edges of the shape (e.g. left/right side of rectangle)
        """
        size = self.GetClientSizeTuple()
        if not self.area > size:  # canvas is too small to need to scroll
            return

        # no point continuing if we're not near the canvas' border
        start = self.GetViewStart()
        end_x = self.GetClientSize()[0] + start[0]
        end_y = self.GetClientSize()[1] + start[1]

        rect = wx.Rect(start[0] + EDGE, start[1] + EDGE, end_x - EDGE, end_y - EDGE)

        if rect.ContainsXY(x, y):
            return

        scroll = (-1, -1)

        if moving:
            if self.selected.edges[EDGE_RIGHT] > start[0] + size[0] - EDGE and DRAG_RIGHT in direction:
                scroll = (start[0] + TO_MOVE, -1)
            if self.selected.edges[EDGE_BOTTOM] > start[1] + size[1] - EDGE and DRAG_DOWN in direction:
                scroll = (-1, start[1] + TO_MOVE)

            if self.selected.edges[EDGE_LEFT] < start[0] + EDGE and DRAG_LEFT in direction:
                scroll = (start[0] - TO_MOVE, -1)
            if self.selected.edges[EDGE_TOP] > start[1] + EDGE and DRAG_RIGHT in direction:
                scroll = (-1, start[1] - TO_MOVE)
        else:
            if x > start[0] + size[0] - EDGE:
                scroll = (start[0] + TO_MOVE, -1)
            if y > start[1] + size[1] - EDGE:
                scroll = (-1, start[1] + TO_MOVE)

            if x < start[0] + EDGE:  # x left
                scroll = start[0] - TO_MOVE, -1
            if y < start[1] + EDGE:  # y top
                scroll = (-1, start[1] - TO_MOVE)

        self.Scroll(*scroll)


    def check_move(self, pos):
        """
        Checks whether a selected shape can be moved in the shape order
        """
        if not self.selected or isinstance(self.selected, Media):
            return False
        if not self.selected in self.shapes:
            return False
        if pos in [u"top", u"up"]:
            length = len(self.shapes) - 1
            if length < 0:
                length = 0
            if self.shapes.index(self.selected) != length:
                return True
        elif pos in [u"down", u"bottom"]:
            if self.shapes.index(self.selected) != 0:
                return True
        return False


    def do_move(self, shape):
        """ Performs the move, by popping the item to be moved """
        self.add_undo()
        x = self.shapes.index(shape)
        return (x, self.shapes.pop(x))


    def move_shape(fn):
        def wrapper(self, shape, x=None, item=None):
            x, item = self.do_move(shape)
            fn(self, shape, x, item)
            self.redraw_all(True)
        return wrapper

    @move_shape
    def move_up(self, shape, x=None, item=None):
        self.shapes.insert(x + 1, item)

    @move_shape
    def move_down(self, shape, x=None, item=None):
        self.shapes.insert(x - 1, item)

    @move_shape
    def move_top(self, shape, x=None, item=None):
        self.shapes.append(item)

    @move_shape
    def move_bottom(self, shape, x=None, item=None):
        self.shapes.insert(0, item)


    def convert_coords(self, event):
        """ Translate mouse x/y coords to virtual scroll ones. """
        return self.CalcUnscrolledPosition(event.GetX(), event.GetY())

    def middle_down(self, event):
        """ Begin dragging the scroller to move around the panel """
        self.set_cursor(wx.CURSOR_SIZENESW)
        self.scroller.Start(event.GetPosition())

    def middle_up(self, event):
        """ Stop dragging the scroller. """
        self.scroller.Stop()
        self.change_cursor()  # bugfix with custom cursor

    def on_paint(self, event=None):
        """
        Called when the window is exposed. Paint the buffer, and then create a
        region, remove the buffer rectangle then clear it with grey.
        """
        wx.BufferedPaintDC(self, self.buffer, wx.BUFFER_VIRTUAL_AREA)
        #dc.SetUserScale(self.scale[0], self.scale[1])

#        if self.current_page:
#            dc = wx.PaintDC(self)
#            cr = wxcairo.ContextFromDC(dc)
#            cr.set_source_rgb(1, 1, 1)  # White background
#            if self.scale != 1:
#                cr.scale(self.scale[0], self.scale[1])
#            cr.rectangle(0, 0, self.area[0], self.area[1])
#            cr.fill()
#            self.current_page.render(cr)
        #else:
        #    dc = wx.BufferedPaintDC(self, self.buffer, wx.BUFFER_VIRTUAL_AREA)

        if os.name == "nt":
            relbuf = self.CalcScrolledPosition(self.area)
            cli = self.GetClientSize()

            if cli.x > relbuf[0] or cli.y > relbuf[1]:
                bkgregion = wx.Region(0, 0, cli.x, cli.y)
                bkgregion.SubtractRect(wx.Rect(0, 0, relbuf[0], relbuf[1]))
                dc = wx.ClientDC(self)
                dc.SetClippingRegionAsRegion(bkgregion)
                dc.SetBrush(wx.GREY_BRUSH)
                dc.Clear()
                dc.DestroyClippingRegion()


    def paste_image(self, bitmap, x, y, ignore=False):
        shape = Image(self, bitmap, None)
        shape.left_down(x, y)
        wx.Yield()
        if ignore:
            self.resize((bitmap.GetWidth(), bitmap.GetHeight()))
        self.redraw_all(True)


    def paste_text(self, text, x, y, colour):
        self.shape = Text(self, colour, 1)
        self.shape.text = text
        self.shape.left_down(x, y)
        self.shape.left_up(x, y)
        self.text = None
        pub.sendMessage('canvas.change_tool')
        self.redraw_all(True)


    def get_selection_bitmap(self):
        """
        If a rectangle selection is made, copy the selection as a bitmap.
        NOTE: The bitmap selection can be larger than the actual canvas bitmap,
        so we must only selection the region of the selection that is visible
        on the canvas
        """
        self.copy.update_rect()  # ensure w, h are correct
        bmp = self.copy
        area = self.area

        if bmp.x + bmp.width > area[0]:
            bmp.rect.SetWidth(area[0] - bmp.x)

        if bmp.y + bmp.height > area[1]:
            bmp.rect.SetHeight(area[1] - bmp.y)

        self.copy = None
        self.redraw_all()
            
        return self.buffer.GetSubBitmap(bmp.rect)


    def deselect_shape(self):
        """Deselects the currently selected shape"""
        for x in self.shapes:
            if isinstance(x, OverlayShape):
                x.selected = False
        if self.selected:
            self.selected = None
            self.redraw_all()


    def select_shape(self, shape):
        """Selects the selected shape"""
        self.overlay = wx.Overlay()
        if self.selected:
            self.deselect_shape()

        self.selected = shape
        shape.selected = True
        x = self.shapes.index(shape)
        self.shapes.pop(x)
        self.redraw_all()  # hide 'original'
        self.shapes.insert(x, shape)
        shape.draw(self.get_dc(), False)  # draw 'new'


    def get_mouse_position(self):
        x, y = self.ScreenToClient(wx.GetMousePosition())
        if x < 0 or y < 0 or x > self.area[0] or y > self.area[1]:
            x, y = 0, 0

        return self.CalcUnscrolledPosition(x, y)


    def get_dc(self):
        cdc = wx.ClientDC(self)
        self.PrepareDC(cdc)
        return wx.BufferedDC(cdc, self.buffer, wx.BUFFER_VIRTUAL_AREA)


    def draw_shape(self, shape, replay=False):
        """ Redraws a single shape efficiently"""
        dc = self.get_dc()
        #dc.SetUserScale(self.scale[0], self.scale[1])
        if replay:
            shape.draw(dc, replay)
        else:
            shape.draw(dc)
        self.redraw_dirty(dc)

    def can_swap_transparency(self):
        return self.selected and not isinstance(self.selected, (Media, Image, Text))

    def can_swap_colours(self):
        return (self.selected and not self.selected.background == wx.TRANSPARENT
                and not isinstance(self.selected, (Media, Image, Text)))

    def swap_colours(self):
        self.selected.colour, self.selected.background = self.selected.background, self.selected.colour
        self.redraw_all()

    def capture_mouse(self):
        if not self.HasCapture():
            self.CaptureMouse()

    def release_mouse(self):
        if self.HasCapture():
            self.ReleaseMouse()

    def resize_if_large_image(self, size):
        """ Check whether the canvas should be resized (for large images) """
        if size[0] > self.area[0] or size[1] > self.area[1]:
            self.resize(size)


    def on_size(self, event):
        """ Updates the scrollbars when the window is resized. """
        size = self.GetClientSize()

        if size[0] < self.area[0] or size[1] < self.area[1]:
            self.SetVirtualSize((self.area[0] + 20, self.area[1] + 20))


#----------------------------------------------------------------------

class CanvasDropTarget(wx.PyDropTarget):
    """Implements drop target functionality to receive files and text"""
    def __init__(self):
        wx.PyDropTarget.__init__(self)
        self.do = wx.DataObjectComposite()
        self.filedo = wx.FileDataObject()
        self.textdo = wx.TextDataObject()
        self.bmpdo = wx.BitmapDataObject()
        self.do.Add(self.filedo)
        self.do.Add(self.bmpdo)
        self.do.Add(self.textdo)
        self.SetDataObject(self.do)


    def OnData(self, x, y, d):
        """
        Handles drag/dropping files/text or a bitmap
        """
        if self.GetData():
            df = self.do.GetReceivedFormat().GetType()

            if df in [wx.DF_UNICODETEXT, wx.DF_TEXT]:
                pub.sendMessage('canvas.paste_text', text=self.textdo.GetText(),
                                x=x, y=y)

            elif df == wx.DF_FILENAME:
                for x, name in enumerate(self.filedo.GetFilenames()):
                    pub.sendMessage('gui.open_file', filename=name)

            elif df == wx.DF_BITMAP:
                pub.sendMessage('canvas.paste_image', image=self.bmpdo.GetBitmap(),
                                x=x, y=y, ignore=True)
        return d