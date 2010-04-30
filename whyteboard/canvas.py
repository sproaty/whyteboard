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
import wx.lib.dragscroller

from lib.pubsub import pub

from tools import (Image, Text, Line, Note, Select, OverlayShape, Media,
                   Highlighter, Polygon, TOP_LEFT, TOP_RIGHT, BOTTOM_LEFT,
                   BOTTOM_RIGHT, CENTER_TOP, CENTER_RIGHT, CENTER_BOTTOM,
                   CENTER_LEFT, HANDLE_ROTATE, EDGE_TOP, EDGE_RIGHT, EDGE_LEFT,
                   EDGE_BOTTOM)

#----------------------------------------------------------------------

EDGE = 15    # distance from canvas edge before shape will scroll canvas
TO_MOVE = 5  # pixels shape will cause canvas to scroll
CANVAS_BORDER = 15  # border pixels in size (overridable by user)

# area user clicked on canvas to resize
RIGHT = 1
DIAGONAL = 2
BOTTOM = 3



class Canvas(wx.ScrolledWindow):
    """
    The drawing frame of the application. References to self.shape.drawing are
    for the Polygon tool, mainly avoiding isinstance() checks
    """
    def __init__(self, tab, gui):
        """
        Initalise the window, class variables and bind mouse/paint events
        """
        style = wx.NO_FULL_REPAINT_ON_RESIZE | wx.CLIP_CHILDREN
        wx.ScrolledWindow.__init__(self, tab, style=style)

        self.area = (gui.util.config['default_width'], gui.util.config['default_height'])
        self.SetVirtualSizeHints(2, 2)
        self.SetScrollRate(1, 1)
        self.SetBackgroundColour('Grey')
        self.file_drop = CanvasDropTarget(gui)
        self.SetDropTarget(self.file_drop)

        if os.name == "nt":
            self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)  # no flicking on Win!
        if os.name == "posix":
            self.ClearBackground()

        self.scroller = wx.lib.dragscroller.DragScroller(self)
        self.overlay = wx.Overlay()
        self.buffer = wx.EmptyBitmap(*self.area)
        #self.hit_buffer = wx.EmptyBitmap(*self.area)  # used by pen for hit test
        #dc = wx.BufferedDC(None, self.hit_buffer, wx.BUFFER_VIRTUAL_AREA)
        #dc.SetBackground(wx.WHITE_BRUSH)
        #dc.Clear()

        self.gui = gui
        self.tab = tab
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

        img = wx.Image(os.path.join(self.gui.util.get_path(), "images",
                                    "cursors", "") + "rotate.png")
        self.rotate_cursor = wx.CursorFromImage(img)
        self.change_current_tool()
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



    def left_down(self, event):
        """Starts drawing"""
        x, y = self.convert_coords(event)
        if os.name == "nt" and not isinstance(self.shape, Media) and not self.shape.drawing:
            self.CaptureMouse()
        if not self.shape.drawing and self.check_canvas_resize(x, y):  # don't draw outside canvas
            self.resizing = True
            return

        if not isinstance(self.shape, Select) and self.selected:
            self.deselect()

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
            self.resize_canvas((x, y), self.resize_direction)
            return
        else:
            if not self.check_mouse_for_resize(x, y):
                return

        if self.gui.bar_shown:
            self.gui.SetStatusText(" %s, %s" % (x, y))

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
            if self.copy:
                self.draw_shape(self.copy)  # draw back the GCDC
            return
        if self.drawing or isinstance(self.shape, Text):
            before = len(self.shapes)
            self.shape.left_up(*self.convert_coords(event))
            if not isinstance(self.shape, Media):
                if len(self.shapes) - before:
                    self.change_current_tool()
                    self.update_thumb()
            self.drawing = False


    def right_up(self, event):
        """Called when the right mouse button is released - used for zoom"""
        self.shape.right_up(*self.convert_coords(event))


    def left_double(self, event):
        """Double click for the Select tool - edit text"""
        self.shape.double_click(*self.convert_coords(event))



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
                self.SetCursor(wx.StockCursor(wx.CURSOR_SIZENWSE))
            elif wx.GetKeyState(wx.WXK_CONTROL):
                self.SetCursor(self.rotate_cursor)
            else:
                self.SetCursor(wx.StockCursor(wx.CURSOR_SIZING))
        elif res == HANDLE_ROTATE:

            self.SetCursor(self.rotate_cursor)
        elif res in [TOP_LEFT, BOTTOM_RIGHT]:
            self.SetCursor(wx.StockCursor(wx.CURSOR_SIZENWSE))
        elif res in [TOP_RIGHT, BOTTOM_LEFT]:
            self.SetCursor(wx.StockCursor(wx.CURSOR_SIZENESW))
        elif res in [CENTER_TOP, CENTER_BOTTOM]:
            self.SetCursor(wx.StockCursor(wx.CURSOR_SIZENS))
        elif res in [CENTER_LEFT, CENTER_RIGHT]:
            self.SetCursor(wx.StockCursor(wx.CURSOR_SIZEWE))
        elif shape.hit_test(x, y):
            self.SetCursor(wx.StockCursor(wx.CURSOR_HAND))
        else:
            ret = False
        return ret


    def check_mouse_for_resize(self, x, y):
        """
        Sees if the user's mouse is outside of the canvas, and updates the
        cursor if it's in a different resizable area than it previously was
        Returns the cursor to its normal state if it's moved back in
        """
        direction = self.check_canvas_resize(x, y)
        if not self.drawing and direction:
            if not self.shape.drawing:
                if not self.resize_direction:
                    self.resize_direction = direction
                if(not self.cursor_control or direction != self.resize_direction):
                    self.resize_direction = direction
                    self.cursor_control = True
                    self.resize_cursor(direction) # change cursor
                return False
        else:
            if self.cursor_control:
                self.change_cursor()
                self.cursor_control = False
                return False
        return True


    def check_canvas_resize(self, x, y):
        """Which direction the canvas can be resized in, if any"""
        if x > self.area[0] and y > self.area[1]:
            return DIAGONAL
        elif x > self.area[0]:
            return RIGHT
        elif y > self.area[1]:
            return BOTTOM
        return False


    def resize_cursor(self, direction):
        cursors = {DIAGONAL: wx.CURSOR_SIZENWSE, RIGHT: wx.CURSOR_SIZEWE,
                   BOTTOM: wx.CURSOR_SIZENS}
        self.SetCursor(wx.StockCursor(cursors.get(direction)))



    def resize_canvas(self, size, direction=None):
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
        size = (size[0] + CANVAS_BORDER, size[1] + CANVAS_BORDER)
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
            self.update_thumb()


    def change_current_tool(self, new=None):
        """
        Changes the users' tool (and cursor) they are drawing with. new is an
        int, corresponding to new - 1 = Tool ID in Utility.items
        Can be called with no new ID to reset itself with the current tool
        """
        if self.HasCapture():
            self.ReleaseMouse()
        if not new:
            new = self.gui.util.tool
        else:
            self.gui.util.tool = new

        colour = self.gui.util.colour
        thickness = self.gui.util.thickness
        params = [self, colour, thickness]  # Object constructor parameters

        if not self.gui.util.transparent:
            params.append(self.gui.util.background)

        self.shape = self.gui.util.items[new - 1](*params)  # create new Tool
        self.change_cursor()
        self.gui.control.preview.Refresh()


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
            self.deselect()
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
        if self.gui.util.saved:
            self.gui.util.saved = False


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
        shapes = list_a.pop()
        self.shapes = shapes
        self.deselect()
        self.redraw_all(True)

        # nicest (and laziest) way to sort the notes out at the moment
        notes = self.gui.notes
        notes.tree.DeleteChildren(notes.tabs[self.gui.tabs.GetSelection()])
        for x in shapes:
            if isinstance(x, Note):
                pub.sendMessage('note.add', note=x)


    def toggle_transparent(self):
        """Toggles the selected item's transparency"""
        if not self.selected or isinstance(self.selected, (Media, Image, Text)):
            return
        self.add_undo()
        val = wx.TRANSPARENT

        if self.selected.background == wx.TRANSPARENT:
            val = self.gui.control.background.GetColour()

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

        self.gui.util.saved = False
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

        self.gui.util.saved = False
        self.shapes = images
        self.redraw_all(update_thumb=True)


    def drag_direction(self, x, y):
        """
        Work out the direction a shape's being moved in so that we don't scroll
        the canvas as a shape is being dragged away from a canvas edge.
        """
        direction = None

        # left
        if self.prev_drag[0] > x:
            direction = 'left'
        if self.prev_drag[0] < x:
            direction = 'right'
        if self.prev_drag[1] > y:
            direction = 'up'
        if self.prev_drag[1] < y:
            direction = 'down'

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

        start = self.GetViewStart()
        scroll = (-1, -1)

        if moving:
            if self.selected.edges[EDGE_RIGHT] > start[0] + size[0] - EDGE and direction == "right":
                scroll = (start[0] + TO_MOVE, -1)
            if self.selected.edges[EDGE_BOTTOM] > start[1] + size[1] - EDGE and direction == "down":
                scroll = (-1, start[1] + TO_MOVE)

            if self.selected.edges[EDGE_LEFT] < start[0] + EDGE and direction == "left":
                scroll = (start[0] - TO_MOVE, -1)
            if self.selected.edges[EDGE_TOP] < start[1] + EDGE and direction == "up":
                print 'up'
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
        if pos in ["top", "up"]:
            length = len(self.shapes) - 1
            if length < 0:
                length = 0
            if self.shapes.index(self.selected) != length:
                return True
        elif pos in ["down", "bottom"]:
            if self.shapes.index(self.selected) != 0:
                return True
        return False


    def do_move(self, shape):
        """ Performs the move, by popping the item to be moved """
        self.add_undo()
        x = self.shapes.index(shape)
        return (x, self.shapes.pop(x))


    def move_up(self, shape):
        """ Move a shape up in the to-draw list. """
        x, item = self.do_move(shape)
        self.shapes.insert(x + 1, item)
        self.redraw_all(True)

    def move_down(self, shape):
        """ Move a shape up in the to-draw list. """
        x, item = self.do_move(shape)
        self.shapes.insert(x - 1, item)
        self.redraw_all(True)


    def move_top(self, shape):
        """ Move a shape to the top in the to-draw list. """
        item = self.do_move(shape)[1]
        self.shapes.append(item)
        self.redraw_all(True)

    def move_bottom(self, shape):
        """ Move a shape up in the to-draw list. """
        item = self.do_move(shape)[1]
        self.shapes.insert(0, item)
        self.redraw_all(True)


    def convert_coords(self, event):
        """ Translate mouse x/y coords to virtual scroll ones. """
        return self.CalcUnscrolledPosition(event.GetX(), event.GetY())

    def middle_down(self, event):
        """ Begin dragging the scroller to move around the panel """
        self.SetCursor(wx.StockCursor(wx.CURSOR_SIZENESW))
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



    def deselect(self):
        """Deselects the selected shape"""
        for x in self.shapes:
            if isinstance(x, OverlayShape):
                x.selected = False
        if self.selected:
            self.selected = None
            self.redraw_all()


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

    def swap_colours(self):
        self.selected.colour, self.selected.background = self.selected.background, self.selected.colour
        self.redraw_all()

    def get_tab(self):
        """ Returns the current tab number of this Canvas instance. """
        return self.tab.GetSelection()

    def capture_mouse(self):
        if not self.HasCapture():
            self.CaptureMouse()

    def release_mouse(self):
        if self.HasCapture():
            self.ReleaseMouse()

    def update_thumb(self):
        """ Updates this tab's thumb """
        self.gui.thumbs.update(self.get_tab())


    def check_resize(self, size):
        """ Check whether the canvas should be resized (for large images) """
        if size[0] > self.area[0] or size[1] > self.area[1]:
            self.resize_canvas(size)


    def on_size(self, event):
        """ Updates the scrollbars when the window is resized. """
        size = self.GetClientSize()

        if size[0] < self.area[0] or size[1] < self.area[1]:
            self.SetVirtualSize((self.area[0] + 20, self.area[1] + 20))


#----------------------------------------------------------------------

class CanvasDropTarget(wx.PyDropTarget):
    """Implements drop target functionality to receive files and text"""
    def __init__(self, gui):
        wx.PyDropTarget.__init__(self)
        self.gui = gui
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

                shape = tools.Text(self.gui.board, self.gui.util.colour, 1)
                shape.text = self.textdo.GetText()

                self.gui.board.shape = shape
                shape.left_down(x, y)
                shape.left_up(x, y)
                self.gui.board.text = None
                self.gui.board.change_current_tool()
                self.gui.board.redraw_all(True)

            elif df == wx.DF_FILENAME:
                for x, name in enumerate(self.filedo.GetFilenames()):
                    if x or self.gui.board.shapes:
                        self.gui.on_new_tab()

                    if name.endswith(".wtbd"):
                        self.gui.util.prompt_for_save(self.gui.do_open, args=[name])
                    else:
                        self.gui.do_open(name)

            elif df == wx.DF_BITMAP:
                bmp = self.bmpdo.GetBitmap()
                shape = tools.Image(self.gui.board, bmp, None)
                shape.left_down(x, y)
                wx.Yield()
                self.gui.board.redraw_all(True)

        return d