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

import wx
import time
import os

from dialogs import TextInput

#----------------------------------------------------------------------

class Tool(object):
    """ Abstract class representing a tool: Drawing board/colour/thickness """
    tooltip = ""

    def __init__(self, board, colour, thickness, cursor=wx.CURSOR_PENCIL):
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
        """ Left mouse button event """
        pass

    def button_up(self, x, y):
        """ Left button up. """
        pass
    
    def motion(self, x, y):
        """ Mouse in motion (usually while drawing) """
        pass

    def draw(self, dc, replay=True):
        """ Draws itself. """
        pass

    def hit_test(self, x, y):
        """ Returns true/false if a mouseclick in "inside" the shape """
        pass

    def make_pen(self):
        """ Creates a pen from the object after loading in a save file """
        self.pen = wx.Pen(self.colour, self.thickness, wx.SOLID)
        self.brush = wx.TRANSPARENT_BRUSH

    def preview(self, dc, width, height):
        """ Tools' preview for the left-hand panel """
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
    tooltip = "Draw strokes with a brush"

    def __init__(self, board, colour, thickness, cursor=wx.CURSOR_PENCIL):
        Tool.__init__(self, board, colour, thickness, cursor)
        self.points = []  # ALL x1, y1, x2, y2 coords to render
        self.time = []  # list of times for each point, for redrawing

    def button_down(self, x, y):
        self.x = x  # original mouse coords
        self.y = y
        self.motion(x, y)

    def button_up(self, x, y):
        if self.points:
            self.board.add_shape(self)
            self.board.draw(self) 
        
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
        points = ((52, 10), (51, 10), (50, 10), (49, 10), (49, 9), (48, 9), (47, 9), (46, 9), (46, 8), (45, 8), (44, 8), (43, 8), (42, 8), (41, 8), (40, 8), (39, 8), (38, 8), (37, 8), (36, 8), (35, 8), (34, 8), (33, 8), (32, 8), (31, 8), (30, 8), (29, 8), (28, 8), (27, 8), (27, 10), (26, 10), (26, 11), (26, 12), (26, 13), (26, 14), (26, 15), (26, 16), (28, 18), (30, 19), (31, 21), (34, 22), (36, 24), (37, 26), (38, 27), (40, 28), (40, 29), (40, 30), (40, 31), (38, 31), (37, 32), (35, 33), (33, 33), (31, 34), (28, 35), (25, 36), (22, 36), (20, 37), (17, 37), (14, 37), (12, 37), (10, 37), (9, 37), (8, 37), (7, 37))
        dc.DrawSpline(points)

#----------------------------------------------------------------------

class OverlayShape(Tool):
    """Contains methods for drawing an overlayed shape"""
    def __init__(self, board, colour, thickness, cursor=wx.CURSOR_CROSS):
        Tool.__init__(self, board, colour, thickness, cursor)
        self.selected = False        
            
    def button_down(self, x, y):
        self.x = x
        self.y = y
        self.board.overlay = wx.Overlay()

    def button_up(self, x, y):
        """ Only adds the shape if it was actually dragged out """
        if x != self.x and y != self.y:
            self.board.add_shape(self)
            self.board.draw(self)

    def draw(self, dc, replay=False, _type="Rectangle", pen=wx.SOLID):
        """
        Draws a shape polymorphically, using Python's introspection; can be
        called by its sub-classes.
        When called for a replay it renders itself; doesn't draw a temp outline.
        """
        args = self.get_args()
        self.make_pen()
        if not replay:
            odc = wx.DCOverlay(self.board.overlay, dc)
            odc.Clear()

        dc.SetPen(wx.Pen(self.colour, self.thickness, pen))
        dc.SetBrush(self.brush)
        dc.SetTextForeground(self.colour)  # forces text colour
        method = getattr(dc, "Draw" + _type)
        method(*args)
        if self.selected:
            self.draw_selected(dc)            
        if not replay:
            del odc
            
    def draw_selected(self, dc):
        pass

    def offset(self, x, y):
        """Used to move the shape, keeping the cursor in the same place"""
        return (x - self.x, y - self.y)
                        
    def get_args(self):
        pass
    
    def load(self):
        self.selected = False
                    
#----------------------------------------------------------------------

class Rectangle(OverlayShape):
    """
    The rectangle and its descended classes (ellipse/rounded rect) use an
    overlay as a rubber banding method of drawing itself over other shapes.
    """
    tooltip = "Draw a rectangle"

    def __init__(self, board, colour, thickness):
        OverlayShape.__init__(self, board, colour, thickness)
        self.width = 0
        self.height = 0

    def button_down(self, x, y):
        super(Rectangle, self).button_down(x, y)

    def motion(self, x, y):
        self.width =  x - self.x
        self.height = y - self.y

    def get_args(self):
        return [self.x, self.y, self.width, self.height]        
    def preview(self, dc, width, height):
        dc.DrawRectangle(5, 5, width - 15, height - 15)

    def sort_args(self):
        """
        Do some rectangle conversions instead of having to deal with loads of 
        long-winded if statements.
        """        
        a = [self.x, self.width + self.x]
        b = [self.y, self.height + self.y]
        a.sort()
        b.sort()
        return [a[0], b[0], a[1] - a[0], b[1] - b[0]]        

    def hit_test(self, x, y):
        rect = wx.Rect(*self.sort_args())
        return rect.InsideXY(x, y)
    
    def offset(self, x, y):
        top, left = self.x, self.y#self.sort_args()[0], self.sort_args()[1]
        return (x - top, y - left)
        
    
    def draw_selected(self, dc):
        dc.SetBrush(wx.BLACK_BRUSH)
        dc.SetPen(wx.Pen(wx.BLACK, 3, wx.SOLID))
        x, y, width, height = self.get_args() 
        d = lambda dc, x, y: dc.DrawRectangle(x - 2, y - 2, 5, 5)
        
        d(dc, x, y)        
        d(dc, x + width, y)
        d(dc, x, y + height)
        d(dc, x + width, y + height)         
        

#----------------------------------------------------------------------


class Circle(OverlayShape):
    """
    Draws a circle. Extended from a Rectangle to save on repeated code.
    """
    tooltip = "Draw a circle"

    def __init__(self, board, colour, thickness):
        OverlayShape.__init__(self, board, colour, thickness)
        self.radius = 1

    def motion(self, x, y):
        self.radius = self.x - x

    def draw(self, dc, replay=False):
        super(Circle, self).draw(dc, replay, "Circle")       

    def get_args(self):
        return [self.x, self.y, self.radius]

    def preview(self, dc, width, height):
        dc.DrawCircle(width/2, height/2, 15)

    def hit_test(self, x, y):
        val = ((x - self.x) * (x - self.x)) + ((y - self.y) * (y - self.y))
        if val <= (self.radius * self.radius) + self.thickness:
            return True
        return False
            
    def draw_selected(self, dc):
        dc.SetBrush(wx.BLACK_BRUSH)
        dc.SetPen(wx.Pen(wx.BLACK, 3, wx.SOLID))
        x, y, radius = self.get_args() 
        d = lambda dc, x, y: dc.DrawRectangle(x - 2, y - 2, 5, 5)
        if radius < 0:
            radius = -radius
        
        d(dc, x - radius, y + radius)        
        d(dc, x - radius, y - radius)
        d(dc, x + radius, y + radius)
        d(dc, x + radius, y - radius)  
        
#----------------------------------------------------------------------


class Ellipse(Rectangle):
    """
    Easily extends from Rectangle.
    """
    tooltip = "Draw an oval shape"
    def draw(self, dc, replay=False):
        super(Ellipse, self).draw(dc, replay, "Ellipse")

    def preview(self, dc, width, height):
        dc.DrawEllipse(5, 5, width - 12, height - 12)

#----------------------------------------------------------------------

class RoundRect(Rectangle):
    """
    Easily extends from Rectangle.
    """
    tooltip = "Draw a rounded rectangle"
    def draw(self, dc, replay=False):
        super(RoundRect, self).draw(dc, replay, "RoundedRectangle")

    def preview(self, dc, width, height):
        dc.DrawRoundedRectangle(5, 5, width - 10, height - 7, 8)

    def get_args(self):
        args = super(RoundRect, self).get_args()
        args.append(35)
        return args

#----------------------------------------------------------------------


class Line(OverlayShape):
    """
    Draws a line. Extended from a Rectangle for outline code.
    """
    tooltip = "Draw a straight line"
    def __init__(self, board, colour, thickness):
        OverlayShape.__init__(self, board, colour, thickness)
        self.x2 = 0
        self.y2 = 0

    def button_down(self, x, y):
        super(Line, self).button_down(x, y)
        self.x2 = x
        self.y2 = y

    def motion(self, x, y):
        self.x2 = x
        self.y2 = y

    def button_up(self, x, y):
        """ Don't add a 'blank' line """
        if self.x2 != self.x or self.y2 != self.y:
            self.board.add_shape(self)
            self.board.draw(self)

    def draw(self, dc, replay=False):
        super(Line, self).draw(dc, replay, "Line")

    def get_args(self):
        return [self.x, self.y, self.x2, self.y2]

    def preview(self, dc, width, height):
        dc.DrawLine(10, height / 2, width - 10, height / 2)

    #def hit_test(self, x, y):
    #    rect = wx.Rect(*self.get_args())
    #    return rect.InsideXY(x, y)

#---------------------------------------------------------------------

class Eraser(Pen):
    """
    Erases stuff. Has a custom cursor from a drawn rectangle on a DC, turned
    into an image then into a cursor.
    """
    tooltip = "Erase a painting to the background"

    def __init__(self, board, colour, thickness):
        cursor = wx.EmptyBitmap(thickness + 2, thickness + 2)
        memory = wx.MemoryDC()
        memory.SelectObject(cursor)
        memory.SetPen(wx.Pen((255, 255, 255), 1))  # border
        memory.SetBrush(wx.Brush((255, 255, 255)))
        memory.FloodFill(0, 0, (255, 255, 255), wx.FLOOD_BORDER)
        memory.SetPen(wx.Pen((0, 0, 0), 1))  # border
        memory.SetBrush(wx.TRANSPARENT_BRUSH)
        memory.DrawRectangle(0, 0, thickness + 2, thickness + 2)
        memory.SelectObject(wx.NullBitmap)

        img = wx.ImageFromBitmap(cursor)
        cursor = wx.CursorFromImage(img)
        Pen.__init__(self, board, (255, 255, 255), thickness + 1, cursor)

    def preview(self, dc, width, height):
        thickness = self.thickness + 1
        dc.SetPen(wx.Pen((0, 0, 0), 1, wx.SOLID))
        dc.DrawRectangle(20, 20, 5 + thickness, 5 + thickness)

#----------------------------------------------------------------------

class Eyedrop(Tool):
    """
    Selects the colour at the specified x,y coords
    """
    tooltip = "Picks a colour from the selected pixel"

    def __init__(self, board, colour, thickness):
        Tool.__init__(self, board, colour, thickness, wx.CURSOR_CROSS)

    def button_down(self, x, y):
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
    tooltip = "Input text"

    def __init__(self, board, colour, thickness):
        OverlayShape.__init__(self, board, colour, thickness, wx.CURSOR_CHAR)
        self.font = None
        self.text = ""
        self.font_data = ""
        self.extent = (0, 0)

    def button_up(self, x, y):
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
            self.board.redraw_all()
            self.board.select_tool()
            return False
        
        dlg.transfer_data(self)  # grab font and text data
        self.font_data = self.font.GetNativeFontInfoDesc()

        if self.text:
            self.board.add_shape(self)
            self.update_scroll()
            return True
        return False
    
    
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


    def find_extent(self):
        """Finds the width/height extent of the object's text"""
        dummy = wx.Frame(None)
        dummy.SetFont(self.font)
        self.extent = dummy.GetTextExtent(self.text)
        dummy.Destroy()
    
    def draw_selected(self, dc):
        d = lambda dc, x, y: dc.DrawRectangle(x - 2, y - 2, 2, 2)
        
        dc.SetBrush(wx.BLACK_BRUSH)
        dc.SetPen(wx.Pen(wx.BLACK, 3, wx.SOLID))        
        d(dc, self.x , self.y)        
        d(dc, self.x + self.extent[0], self.y)
        d(dc, self.x, self.y + self.extent[1])
        d(dc, self.x + self.extent[0], self.y + self.extent[1])   


    def restore_font(self):
        """Updates the text's font to the saved font data"""
        self.font = wx.FFont(0, 0)
        self.font.SetNativeFontInfoFromString(self.font_data)

    def draw(self, dc, replay=False):
        """Has to draw each line individually on Windows."""
        if not self.font:
            self.restore_font()
            self.update_scroll()
        dc.SetFont(self.font)

        if os.name == "nt":
            #  bugfix as DrawText can only draw one line
            text = self.text
            y = self.y

            for x, line in enumerate(self.text.split("\n")):
                self.text = line  # for get_args() in Rectangle.draw()

                if x != 0:
                    self.y += dc.GetTextExtent(line)[1] + 6

                super(Text, self).draw(dc, replay, "Text")
            self.text = text
            self.y = y
        else:
            super(Text, self).draw(dc, replay, "Text")


    def edit(self, event=None):
        """Pops up the TextInput box to edit itself"""
        text = self.text  # restore to these if cancelled/blank
        font = self.font
        font_data = self.font_data
        colour = self.colour
        
        dlg = TextInput(self.board.gui, self)    
        if dlg.ShowModal() == wx.ID_CANCEL:
            dlg.Destroy()
            self.text = text  # restore attributes
            self.font = font
            self.colour = colour
            self.font_data = font_data
            self.find_extent()  # update changed heights
            self.board.redraw_all()  # restore
        else:
            dlg.transfer_data(self)  # grab font and text data
            self.font_data = self.font.GetNativeFontInfoDesc()            
            
            if not self.text:
                self.text = text  # don't want a blank item
                return False
            self.update_scroll()
            return True
            

    def hit_test(self, x, y):
        width = self.x + self.extent[0]
        height = self.y + self.extent[1]

        if x > self.x and x < width and y > self.y and y < height:
            return True
        return False
        
    def get_args(self):
        return [self.text, self.x, self.y]

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

class Note(Text):
    """
    A special type of text input, in the style of a post-it/"sticky" notes.
    It is linked to the tab it's displayed on, and is drawn with a light
    yellow background (to show that it's a note). An overview of notes for each
    tab can be viewed on the side panel.
    """
    tooltip = "Insert a note"
    def __init__(self, board, colour, thickness):
        Text.__init__(self, board, colour, thickness)
        self.tree_id = None
        
    def button_up(self, x, y,):
        """ Don't add a blank note """
        if super(Note, self).button_up(x, y):
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
        dummy = wx.Frame(None)
        dummy.SetFont(self.font)

        if os.name == "nt":
            height = 0
            width = 0
            for x, line in enumerate(self.text.split("\n")):
                ex = dummy.GetTextExtent(line)
                if x == 0:
                    height += ex[1]
                else:
                    height += ex[1] + 6

                if ex[0] > width:
                    width = ex[0]

            extent = (width, height)
        else:
            extent = dummy.GetTextExtent(self.text)

        x, y = extent[0] + 20, extent[1] + 20
        self.extent = (x, y)
        dummy.Destroy()


    def draw(self, dc, replay=False):
        """Draws a light backgrounded rectangle behind the text"""
        if not self.font:
            self.restore_font()

        self.find_extent()
        dc.SetBrush(wx.Brush((255, 223, 120)))
        dc.SetPen(wx.Pen((0, 0, 0), 1))
        dc.DrawRectangle(self.x - 10, self.y - 10, *self.extent)
        dc.SetFont(self.font)
        super(Note, self).draw(dc, replay)

    def draw_selected(self, dc):
        """Need to offset the 'handles' differently to text"""
        d = lambda dc, x, y: dc.DrawRectangle(x - 2, y - 2, 2, 2)
        
        dc.SetBrush(wx.BLACK_BRUSH)
        dc.SetPen(wx.Pen(wx.BLACK, 3, wx.SOLID))        
        d(dc, self.x - 11, self.y - 10)        
        d(dc, self.x + self.extent[0] - 6, self.y - 10)
        d(dc, self.x - 11, self.y + self.extent[1] - 10)
        d(dc, self.x + self.extent[0] - 6, self.y + self.extent[1] - 10)  
        
        
    def preview(self, dc, width, height):
        dc.SetBrush(wx.Brush((255, 223, 120)))
        dc.SetPen(wx.Pen((0, 0, 0), 1))
        dc.DrawRectangle(3, 3, width - 10, height - 10)
        dc.SetTextForeground(self.colour)
        dc.DrawText("abcdef", 15, height / 2 - 10)

    def load(self, add_note=True):
        """Recreates the note in the tree"""
        super(Note, self).load()
        gui = self.board.gui
        if add_note:
            gui.notes.add_note(self, gui.tab_count - 1)

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
        cdc = wx.ClientDC(self.board)
        dc = wx.BufferedDC(cdc, self.board.buffer)  # create tmp DC
        self.draw(dc)
        self.board.add_shape(self)

    def draw(self, dc, replay=False):
        dc.SetPen(self.pen)
        dc.SetBrush(wx.Brush(self.colour))
        dc.FloodFill(self.x, self.y, (255, 255, 255), wx.FLOOD_SURFACE)

    def preview(self, dc, width, height):
        dc.SetBrush(wx.Brush(self.colour))
        dc.DrawRectangle(10, 10, width - 20, height - 20)

#----------------------------------------------------------------------

class Image(OverlayShape):
    """
    When being pickled, the image reference will be removed.
    """
    def __init__(self, board, image, path):
        OverlayShape.__init__(self, board, (0, 0, 0), 1)
        self.image = image
        self.path = path  # used to restore image on load

    def button_down(self, x, y):
        self.x = x
        self.y = y
        self.board.add_shape(self)
        size = (self.image.GetWidth(), self.image.GetHeight())
        self.board.update_scrollbars(size)

        dc = wx.BufferedDC(None, self.board.buffer)
        self.draw(dc)
        self.board.redraw_dirty(dc)

    def draw(self, dc, replay=False):
        super(Image, self).draw(dc, replay, "Bitmap")
                      
    def get_args(self):
        return [self.image, self.x, self.y]

    def save(self):
        super(Image, self).save()
        self.image = None

    def load(self):
        self.selected = False
        self.image = wx.Bitmap(self.path)
        size = (self.image.GetWidth(), self.image.GetHeight())
        self.board.update_scrollbars(size)

    def hit_test(self, x, y):
        width, height = self.image.GetSize()
        rect_x = self.x
        rect_y = self.y
        rect_x2 = rect_x + width
        rect_y2 = rect_y + height

        if x > rect_x and x < rect_x2 and y > rect_y and y < rect_y2:
            #img = self.image.ConvertToImage()
            #img = img.Rotate90()
            #self.image = wx.BitmapFromImage(img)
            return True
        else:
            return False

#----------------------------------------------------------------------

class Zoom(Tool):
    """
    Zooms in on the current Whyteboard tab
    """
    def __init__(self, board, image, path):
        Tool.__init__(self, board, (0, 0, 0), 1)

    def button_down(self, x, y):
        x = self.board.zoom
        new = (x[0] + 0.3, x[1] + 0.3)
        self.board.zoom = new

#----------------------------------------------------------------------

class Select(Tool):
    """
    Select an item to move it around/edit text
    """
    tooltip = "Select a shape to move and resize it"
    
    def __init__(self, board, image, path):
        Tool.__init__(self, board, (0, 0, 0), 1, wx.CURSOR_ARROW)
        self.shape = None
        self.dragging = False
        self.count = 0

    def button_down(self, x, y):
        """
        Sees if a shape is underneath the mouse coords, and allows the shape to
        be re-dragged to place
        """
        #self.board.deselect()
        self.board.overlay = wx.Overlay()
        shapes = self.board.shapes
        shapes.reverse()
        for count, shape in enumerate(shapes):
            if shape.hit_test(x, y):              
                self.shape = shapes[count]

                self.board.selected = shape
                self.shape.selected = True
                self.dragging = True
                self.count = count
                self.offset = self.shape.offset(x, y)
                self.x = shape.x
                self.y = shape.y
                break
        
    def double_click(self, x, y):
        if isinstance(self.board.selected, Text):
            self.dragging = False
            self.board.selected.edit()

    def motion(self, x, y):
        if self.dragging:
            self.shape.x = x - self.offset[0]
            self.shape.y = y - self.offset[1]

    def draw(self, dc, replay=False):
        if self.dragging:
            self.shape.draw(dc, False)   
            
            
    def button_up(self, x, y):
        if self.dragging:
            if isinstance(self.shape, Image):
                size = (x + self.shape.image.GetWidth(), y + self.shape.image.GetHeight())
                self.board.update_scrollbars(size)
                self.dragging = False

        if not self.shape:
            self.board.deselect()  # reset selection to nothing            
        self.board.overlay.Reset()
        self.board.redraw_all(update_thumb=True)
        self.board.select_tool()
       

#----------------------------------------------------------------------

class RectSelect(Rectangle):
    """
    Rectangle selection tool, used to select a region to copy/paste
    """
    tooltip = "Select a rectangular region for copying"
    def __init__(self, board, image, path):
        Rectangle.__init__(self, board, (0, 0, 0), 2)

    def draw(self, dc, replay=False):
        super(RectSelect, self).draw(dc, replay, "Rectangle", wx.SHORT_DASH)

    def button_up(self, x, y):
        """ Important: appends the shape, but not to the undo list """
        if x != self.x and y != self.y:
            self.board.gui.GetStatusBar().SetStatusText("You can now copy this region")
            self.board.shapes.append(self)
            #self.board.draw(self)

    def preview(self, dc, width, height):
        dc.SetPen(wx.BLACK_DASHED_PEN)
        dc.SetBrush(wx.TRANSPARENT_BRUSH)
        dc.DrawRectangle(10, 10, width - 20, height - 20)

    def hit_test(self, x, y):
        pass

#---------------------------------------------------------------------

def find_inverse(colour):
    """ Invert an RGB colour """
    r = 255 - colour.Red()
    g = 255 - colour.Green()
    b = 255 - colour.Blue()
    return wx.Colour(r, g, b)

# items to draw with
items = [Pen, Rectangle, Line, Eraser, Text, Note, Ellipse, Circle, RoundRect,
        Eyedrop, RectSelect, Select]

if __name__ == '__main__':
    from gui import WhyteboardApp
    app = WhyteboardApp(redirect=True)
    app.MainLoop()
