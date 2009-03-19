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
This module contains classes for the GUI side panels.
"""

import wx
from wx.lib import scrolledpanel as scrolled
from copy import copy

from dialogs import TextInput

#----------------------------------------------------------------------

class ControlPanel(wx.Panel):
    """
    This class implements a control panel for the GUI. It creates buttons for
    each tool that can be drawn upon the Whyteboard, a drop-down menu for the
    line thickness and a ColourPicker for choosing the drawing colour. A preview
    of what the tool will look like is also shown.
    """
    def __init__(self, gui):
        """
        Stores a reference to the drawing preview and the toggled drawing tool.
        """
        wx.Panel.__init__(self, gui)

        self.gui = gui
        self.toggled = 1  # Pen initallly
        self.preview = DrawingPreview(self.gui)

        self.tools = {}
        sizer = wx.GridSizer(cols=1, hgap=1, vgap=2)

        # Get list of class names as strings for each drawable tool
        items = [i.__name__ for i in gui.util.items]

        for x, name in enumerate(items):
            b = wx.ToggleButton(self, x + 1, name)
            b.Bind(wx.EVT_TOGGLEBUTTON, self.change_tool, id=x + 1)
            sizer.Add(b, 0)
            self.tools[x + 1] = b

        self.tools[self.toggled].SetValue(True)
        spacing = 4

        self.colour = wx.ColourPickerCtrl(self)
        self.colour.SetToolTip(wx.ToolTip("Sets the drawing colour"))
        self.colour.Bind(wx.EVT_COLOURPICKER_CHANGED, self.change_colour)


        choices = ''.join(str(i) + " " for i in range(1, 16) ).split()

        self.thickness = wx.ComboBox(self, choices=choices, size=(25, 25),
                                        style=wx.CB_READONLY)
        self.thickness.SetSelection(0)
        self.thickness.SetToolTip(wx.ToolTip("Sets the drawing thickness"))
        self.thickness.Bind(wx.EVT_COMBOBOX, self.change_thickness)

        box = wx.BoxSizer(wx.VERTICAL)
        box.Add(sizer, 0, wx.ALL, spacing)
        box.Add(wx.StaticLine(self), 0, wx.EXPAND | wx.ALL, spacing)
        box.Add(self.colour, 0, wx.EXPAND | wx.ALL, spacing)
        box.Add(self.thickness, 0, wx.EXPAND | wx.ALL, spacing)
        box.Add(wx.StaticLine(self), 0, wx.EXPAND | wx.ALL, spacing)
        box.Add(self.preview, 0, wx.EXPAND | wx.ALL, spacing)
        self.SetSizer(box)
        self.SetAutoLayout(True)
        box.Fit(self)


    def change_tool(self, event=None, _id=None):
        """
        Toggles the tool buttons on/off and calls select_tool on the drawing
        panel.
        """
        if event:
            new = int(event.GetId() )  # get widget ID (set in method above)
        elif _id:
            new = _id
        else:
            new = self.gui.util.tool

        if new != self.toggled:  # toggle old button
            self.tools[self.toggled].SetValue(False)
        else:
            self.tools[self.toggled].SetValue(True)

        self.toggled = new
        if self.gui.board:
            self.gui.board.select_tool(new)


    def change_colour(self, event=None):
        """
        Changes colour and updates the preview window.
        """
        self.gui.util.colour = event.GetColour()
        self.gui.board.select_tool()
        self.preview.Refresh()

    def change_thickness(self, event=None):
        """
        Changes thickness and updates the preview window.
        """
        self.gui.util.thickness = event.GetSelection()
        self.gui.board.select_tool()
        self.preview.Refresh()


#----------------------------------------------------------------------


class DrawingPreview(wx.Window):
    """
    Shows a sample of what the current tool's drawing will look like.
    """
    def __init__(self, gui):
        """
        Stores gui reference to access utility colour/thickness attributes.
        """
        wx.Window.__init__(self, gui, style=wx.RAISED_BORDER)
        self.gui = gui
        self.SetBackgroundColour(wx.WHITE)
        self.SetSize((45, 45))
        self.Bind(wx.EVT_PAINT, self.paint)
        self.SetToolTip(wx.ToolTip("A preview of your drawing"))


    def paint(self, event=None):
        """
        Draws the tool inside the box when tool/colour/thickness
        is changed
        """
        if self.gui.board:
            dc = wx.PaintDC(self)
            dc.SetPen(self.gui.board.shape.pen)
            dc.SetBrush(self.gui.board.shape.brush)
            width, height = self.GetClientSize()
            self.gui.board.shape.preview(dc, width, height)


#----------------------------------------------------------------------

class SidePanel(wx.Panel):
    """
    The side panel contains a tabbed window, allowing the user to switch
    between thumbnails and notes. It can be toggled on and off.
    """
    def __init__(self, gui):
        wx.Panel.__init__(self, gui, style=wx.RAISED_BORDER)
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.gui = gui

        self.tabs = wx.Notebook(self)
        self.thumbs = Thumbs(self.tabs, gui)
        self.notes = Notes(self.tabs, gui)
        self.tabs.AddPage(self.thumbs, "Thumbnails")
        self.tabs.AddPage(self.notes, "Notes")
        self.sizer.Add(self.tabs, 1)
        self.SetSizer(self.sizer)

#----------------------------------------------------------------------


class Notes(wx.Panel):
    """
    Contains a Tree which shows an overview of all tabs' notes.
    Notes can be clicked upon to be edited
    """
    def __init__(self, parent, gui):
        wx.Panel.__init__(self, parent, style=wx.RAISED_BORDER)
        self.gui = gui
        #height = gui.GetClientSize()[1]
        self.tree = wx.TreeCtrl(self, size=(170, -1), style=wx.TR_HAS_BUTTONS)
        self.root = self.tree.AddRoot("Whyteboard")
        self.tabs = []
        self.notes = []
        self.add_tab()
        self.tree.Expand(self.root)
        self.tree.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.on_click)

        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer)
        self.sizer.Add(self.tree, 1)
        #self.SetAutoLayout(True)
        #self.sizer.Fit(self)



    def add_tab(self):
        """
        Adds a new tab as a child to the root element
        """
        _id = len(self.tabs)
        if not _id:
            _id = 0
        data = wx.TreeItemData(_id)
        t = self.tree.AppendItem(self.root, "Tab " + str(_id + 1), data=data)
        self.tabs.insert(_id, t)


    def add_note(self, note, _id=None):
        """
        Adds a note to the current tab tree element. The notes' text is the
        element's text is the tree, newlines are replaced to stop the tree's
        formatting being messed up.
        """
        text = note.text.replace("\n", " ")[:15]
        if not _id:
            _id = self.tabs[self.gui.tabs.GetSelection()]
        else:
            _id = self.tabs[_id]

        self.tree.AppendItem(_id, text, data=wx.TreeItemData(note))
        self.tree.Expand(_id)


    def remove(self, note):
        """
        Removes a tab and its children.
        """
        item = self.tabs[note]
        self.tree.DeleteChildren(item)
        self.tree.Delete(item)
        del self.tabs[note]

        # now ensure all nodes are linked to the right tab
        for x in range(self.gui.current_tab, len(self.tabs)):
            self.tree.SetItemData(self.tabs[x], wx.TreeItemData(x))
            self.tree.SetItemText(self.tabs[x], "Tab " + str(x + 1))


    def remove_all(self):
        """
        Removes all tabs.
        """
        self.tree.DeleteChildren(self.root)
        self.tabs = []


    def on_click(self, event):
        """
        Changes to the selected tab is a tab node is double clicked upon,
        otherwise pops up the text edit dialog, passing it the note object.
        """
        item = self.tree.GetPyData(event.GetItem())

        if type(item) == None:
            return  # clicked on the root node

        if isinstance(item, int):
            self.gui.tabs.SetSelection(item)
        else:
            dlg = TextInput(self.gui, item)

            if dlg.ShowModal() == wx.ID_CANCEL:
                dlg.Destroy()
            else:
                dlg.transfer_data(item)  # grab font and text data
                item.font_data = item.font.GetNativeFontInfoDesc()
                item.update_scroll()
                self.tree.SetItemText(event.GetItem(),
                                      item.text.replace("\n", " ")[:15])

#----------------------------------------------------------------------


class Thumbs(scrolled.ScrolledPanel):
    """
    Thumbnails of all tabs' drawings.
    """
    def __init__(self, parent, gui):
        scrolled.ScrolledPanel.__init__(self, parent, style=wx.VSCROLL |
                                                            wx.RAISED_BORDER)
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer)
        self.SetScrollRate(0, 200)

        self.gui = gui
        self.thumbs  = []
        self.text = []
        self.new_thumb()  # inital thumb
        self.thumbs[0].current = True



    def new_thumb(self, _id=0):
        """
        Creates a new thumbnail button and manages its ID, along with a label.
        """
        if _id:
            bmp = self.redraw(_id)
        else:
            if len(self.thumbs):
                _id = len(self.thumbs)
            img = wx.ImageFromBitmap(wx.EmptyBitmapRGBA(150, 150, 255, 255,
                                                                    255, 0))
            img.ConvertColourToAlpha(255, 255, 255)
            bmp = wx.BitmapFromImage(img)

        text = wx.StaticText(self, label="Tab " + str(_id + 1))
        btn = ThumbButton(self, _id, bmp)
        self.text.insert(_id, text)
        self.thumbs.insert(_id, btn)

        for x in self.thumbs:
            if x is not btn:
                x.current = False
                x.SetBitmapLabel(x.buffer)

        self.sizer.Add(text, flag=wx.ALIGN_CENTER | wx.TOP, border=5)
        self.sizer.Add(btn, flag=wx.TOP | wx.LEFT, border=6)
        self.SetVirtualSize(self.GetBestVirtualSize())


    def remove(self, _id):
        """
        Removes a thumbnail/label from the sizer and the managed widgets list.
        """
        self.sizer.Remove(self.thumbs[_id])
        self.sizer.Remove(self.text[_id])
        self.thumbs[_id].Hide()  # 'visibly' remove
        self.text[_id].Hide()

        del self.thumbs[_id]  # 'physically' remove
        del self.text[_id]
        self.SetVirtualSize(self.GetBestVirtualSize())

        # now ensure all thumbnail classes are pointing to the right tab
        for x in range(0, len(self.thumbs)):
            self.thumbs[x].thumb_id = x
            self.text[x].SetLabel("Tab " + str(x + 1))


    def remove_all(self):
        """
        Removes all thumbnails.
        """
        for x in range(0, len(self.thumbs)):
            self.sizer.Remove(self.thumbs[x])
            self.sizer.Remove(self.text[x])
            self.thumbs[x].Hide()  # 'visibly' remove
            self.text[x].Hide()
            self.sizer.Layout()  # update sizer

        self.thumbs = []
        self.text = []
        self.SetVirtualSize(self.GetBestVirtualSize())


    def redraw(self, _id):
        """
        Create a thumbnail by grabbing the currently selected Whyteboard's
        contents and creating a bitmap from it. This bitmap is then converted
        to an image to rescale it, and converted back to a bitmap to be
        displayed on the button as the thumbnail.
        """
        board = self.gui.tabs.GetPage(_id)
        context = wx.BufferedDC(None, board.buffer)
        memory = wx.MemoryDC()
        x, y = board.GetClientSizeTuple()
        bitmap = wx.EmptyBitmap(x, y)
        memory.SelectObject(bitmap)
        memory.Blit(0, 0, x, y, context, 0, 0)
        memory.SelectObject(wx.NullBitmap)

        img = wx.ImageFromBitmap(bitmap)
        img.Rescale(150, 150)
        bmp = wx.BitmapFromImage(img)
        return bmp


    def update(self, _id):
        """
        Updates a single thumbnail.
        """
        bmp = self.redraw(_id)
        thumb = self.thumbs[_id]
        thumb.SetBitmapLabel(bmp)
        self.thumbs[_id].buffer = bmp

        #if thumb.current:
        #    thumb.highlight()


    def update_all(self):
        """
        Updates all thumbnails (i.e. upon loading a Whyteboard file).
        """
        for x in range(0, len(self.thumbs)):
            self.update(x)

#----------------------------------------------------------------------

class ThumbButton(wx.BitmapButton):
    """
    This class has an extra attribute, storing its related tab ID so that when
    the button is pressed, it can switch to the proper tab.
    """
    def __init__(self, parent, _id, bitmap):
        wx.BitmapButton.__init__(self, parent, size=(150, 150))
        self.thumb_id  = _id
        self.parent = parent
        self.SetBitmapLabel(bitmap)
        self.buffer = bitmap
        self.current = False  # active thumb?
        self.Bind(wx.EVT_BUTTON, self.on_press)


    def on_press(self, event):
        """
        Changes the tab to the selected button.
        """
        #if not self.current:
        #    self.highlight()
        self.parent.gui.tabs.SetSelection(self.thumb_id)


    def highlight(self):
        """
        Highlights the current thumbnail with a light overlay.
        """
        _copy = copy(self.buffer)
        dc = wx.MemoryDC()
        dc.SelectObject(_copy)

        gcdc = wx.GCDC(dc)
        gcdc.SetBrush(wx.Brush(wx.Color(0, 0, 255, 30)))
        gcdc.SetPen(wx.Pen((0, 0, 0), 1, wx.TRANSPARENT))
        gcdc.DrawRectangle(0, 0, 150, 150)

        dc.SelectObject(wx.NullBitmap)
        self.SetBitmapLabel(_copy)


#----------------------------------------------------------------------

if __name__ == '__main__':
    from gui import WhyteboardApp
    app = WhyteboardApp(True)
    app.MainLoop()
