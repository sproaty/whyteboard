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
    line thickness and a ColourPicker for choosing the drawing colour. A
    preview of what the tool will look like is also shown.

    It is contained within a collapsed pane, to give extra screen space when in
    full screen mode
    """
    def __init__(self, gui):
        """
        Stores a reference to the drawing preview and the toggled drawing tool.
        """
        wx.Panel.__init__(self, gui)
        self.cp = wx.CollapsiblePane(self, style=wx.CP_DEFAULT_STYLE |
                                     wx.CP_NO_TLW_RESIZE)
        self.gui = gui
        pane = self.cp.GetPane()  # every widget's parent
        sizer = wx.BoxSizer(wx.VERTICAL)
        csizer = wx.BoxSizer(wx.VERTICAL)
        self.SetFocusIgnoringChildren()

        self.toggled = 1  # Pen, initallly
        self.preview = DrawingPreview(pane, self.gui)
        self.tools = {}
        toolsizer = wx.GridSizer(cols=1, hgap=1, vgap=2)

        # Get list of class names as strings for each drawable tool
        items = [i.__name__ for i in gui.util.items]

        for x, name in enumerate(items):
            b = wx.ToggleButton(pane, x + 1, name)
            b.SetToolTipString(gui.util.items[x].tooltip)
            b.Bind(wx.EVT_TOGGLEBUTTON, self.change_tool, id=x + 1)
            toolsizer.Add(b, 0)
            self.tools[x + 1] = b

        self.tools[self.toggled].SetValue(True)
        width = wx.StaticText(pane, label="Thickness:")
        prev = wx.StaticText(pane, label="Preview:")

        self.colour = wx.ColourPickerCtrl(pane)
        self.colour.SetToolTipString("Select a custom colour")

        self.colour_list = ['Black', 'Yellow', 'Green', 'Red', 'Blue', 'Purple',
                            'Cyan', 'Orange', 'Light Grey']

        grid = wx.GridSizer(cols=3, hgap=2, vgap=2)
        for colour in self.colour_list:
            bmp = self.make_bitmap(colour)
            b = wx.BitmapButton(pane, bitmap=bmp)
            method = lambda evt, col = colour: self.change_colour(evt, col)
            b.Bind(wx.EVT_BUTTON, method)
            grid.Add(b, 0)

        choices = ''.join(str(i) + " " for i in range(1, 26) ).split()

        self.thickness = wx.ComboBox(pane, choices=choices, size=(25, 25),
                                        style=wx.CB_READONLY)
        self.thickness.SetSelection(0)
        self.thickness.SetToolTipString("Sets the drawing thickness")

        spacing = 4
        box = wx.BoxSizer(wx.VERTICAL)
        box.Add(toolsizer, 0, wx.ALL, spacing)
        box.Add(wx.StaticLine(self), 0, wx.EXPAND | wx.ALL, spacing)
        box.Add(grid, 0, wx.EXPAND | wx.ALL, spacing)
        box.Add(self.colour, 0, wx.EXPAND | wx.ALL, spacing)
        box.Add(width, 0, wx.ALL | wx.ALIGN_CENTER, spacing)
        box.Add(self.thickness, 0, wx.EXPAND | wx.ALL, spacing)
        box.Add(prev, 0, wx.ALL | wx.ALIGN_CENTER, spacing)
        box.Add(self.preview, 0, wx.EXPAND | wx.ALL, spacing)

        csizer.Add(box, 1, wx.EXPAND)
        sizer.Add(self.cp, 1, wx.EXPAND)

        self.SetSizer(sizer)
        self.cp.GetPane().SetSizer(csizer)
        self.cp.Expand()
        self.Bind(wx.EVT_COLLAPSIBLEPANE_CHANGED, self.toggle)
        self.Bind(wx.EVT_MOUSEWHEEL, self.scroll)
        self.colour.Bind(wx.EVT_COLOURPICKER_CHANGED, self.change_colour)
        self.thickness.Bind(wx.EVT_COMBOBOX, self.change_thickness)


    def toggle(self, evt):
        """Toggles the pane and its widgets"""
        frame = self.GetTopLevelParent()
        frame.Layout()


    def scroll(self, event):
        """Scrolls the thickness drop-down box (for Windows)"""
        box = self.thickness
        val = box.GetSelection()
        if event.GetWheelRotation() > 0:  # mousewheel down
            val -= 1
            if val <= 0:
                val = 0
        else:
            val += 1

        box.SetSelection(val)
        self.change_thickness()


    def make_bitmap(self, colour):
        """Draws a small coloured bitmap for a colour grid button"""
        bmp = wx.EmptyBitmap(15, 15)
        dc = wx.MemoryDC()
        dc.SelectObject(bmp)
        dc.SetBackground(wx.Brush(colour))
        dc.Clear()
        dc.SelectObject(wx.NullBitmap)
        return bmp

    def change_tool(self, event=None, _id=None):
        """
        Toggles the tool buttons on/off and calls select_tool on the drawing
        panel.
        """
        new = self.gui.util.tool
        if event:
            new = int(event.GetId() )  # get widget ID
        elif _id:
            new = _id        
            
        self.tools[self.toggled].SetValue(True)
        if new != self.toggled:  # toggle old button
            self.tools[self.toggled].SetValue(False)
            self.tools[new].SetValue(True)           

        self.toggled = new
        if self.gui.board:
            self.gui.board.select_tool(new)


    def change_colour(self, event=None, colour=None):
        """
        Changes colour and updates the preview window.
        event can also be a string representing a colour for the grid
        """
        if event and not colour:
            colour = event.GetColour()  # from the colour button
        self.gui.util.colour = colour
        self.colour.SetColour(colour)            
        if self.gui.board.selected:
            selected = self.gui.board.selected
            selected.colour = colour
            self.gui.board.draw(selected)  # no need to redraw all
        self.update()
        
    def change_thickness(self, event=None):
        """Changes thickness and updates the preview window."""
        thickness = self.thickness.GetSelection()
        self.gui.util.thickness = thickness 
        if self.gui.board.selected:
            item = copy(self.gui.board.selected)
            item.thickness = thickness
            #self.gui.board.shapes.remove(self.gui.board.selected)
            self.gui.board.add_shape(item) 
            self.gui.board.redraw_all(True)  # causes a bug if drawn as above
        self.update()

    def update(self):
        """Small method to save repeating code"""
        self.gui.board.select_tool()
        self.preview.Refresh()     
            
#----------------------------------------------------------------------


class DrawingPreview(wx.Window):
    """
    Shows a sample of what the current tool's drawing will look like.
    Pane is the collapsible pane, its new parent.
    """
    def __init__(self, pane, gui):
        """
        Stores gui reference to access utility colour/thickness attributes.
        """
        wx.Window.__init__(self, pane, style=wx.RAISED_BORDER)
        self.gui = gui
        self.SetBackgroundColour(wx.WHITE)
        self.SetSize((45, 45))
        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.SetToolTipString("A preview of your drawing")

    def on_paint(self, event=None):
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

            dc.SetPen(wx.Pen((0, 0, 0), 1, wx.SOLID))
            width, height = self.GetClientSize()
            dc.DrawRectangle(0, 0, width, height)  # draw a border..


#----------------------------------------------------------------------

class SidePanel(wx.Panel):
    """
    The side panel contains a tabbed window, allowing the user to switch
    between thumbnails and notes. It can be toggled on and off.
    """
    def __init__(self, gui):
        wx.Panel.__init__(self, gui, style=wx.RAISED_BORDER)
        self.cp = wx.CollapsiblePane(self, style=wx.CP_DEFAULT_STYLE |
                                     wx.CP_NO_TLW_RESIZE)

        sizer = wx.BoxSizer(wx.VERTICAL)
        csizer = wx.BoxSizer(wx.VERTICAL)

        self.tabs = wx.Notebook(self.cp.GetPane())
        self.thumbs = Thumbs(self.tabs, gui)
        self.notes = Notes(self.tabs, gui)
        self.tabs.AddPage(self.thumbs, "Thumbnails")
        self.tabs.AddPage(self.notes, "Notes")

        csizer.Add(self.tabs, 1, wx.EXPAND)
        sizer.Add(self.cp, 1, wx.EXPAND)

        self.SetSizer(sizer)
        self.cp.GetPane().SetSizer(csizer)
        self.cp.Expand()
        self.Bind(wx.EVT_COLLAPSIBLEPANE_CHANGED, self.toggle)


    def toggle(self, evt):
        """Toggles the pane and its widgets"""
        frame = self.GetTopLevelParent()
        frame.Layout()


#----------------------------------------------------------------------


class Notes(wx.Panel):
    """
    Contains a Tree which shows an overview of all tabs' notes.
    Notes can be clicked upon to be edited
    """
    def __init__(self, parent, gui):
        wx.Panel.__init__(self, parent, size=(170, -1), style=wx.RAISED_BORDER)
        self.gui = gui
        self.tree = wx.TreeCtrl(self, size=(170, -1), style=wx.TR_HAS_BUTTONS)
        self.root = self.tree.AddRoot("Whyteboard")
        self.tabs = []
        self.notes = []
        self.add_tab()
        self.tree.Expand(self.root)

        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.tree, 1, wx.EXPAND)
        self.SetSizer(self.sizer)
        self.tree.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.on_click)
        self.tree.Bind(wx.EVT_TREE_ITEM_RIGHT_CLICK, self.pop_up)


    def add_tab(self):
        """Adds a new tab as a child to the root element"""
        _id = len(self.tabs)
        if not _id:
            _id = 0
        data = wx.TreeItemData(_id)
        t = self.tree.AppendItem(self.root, "Sheet " + str(_id + 1), data=data)
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
        
        note.tree_id = self.tree.AppendItem(_id, text, data=wx.TreeItemData(note))
        self.tree.Expand(_id)


    def remove(self, note):
        """Removes a tab and its children."""
        item = self.tabs[note]
        self.tree.DeleteChildren(item)
        self.tree.Delete(item)
        del self.tabs[note]

        # now ensure all nodes are linked to the right tab
        for x in range(self.gui.current_tab, len(self.tabs)):
            self.tree.SetItemData(self.tabs[x], wx.TreeItemData(x))
            self.tree.SetItemText(self.tabs[x], "Sheet " + str(x + 1))


    def remove_all(self):
        """Removes all tabs."""
        self.tree.DeleteChildren(self.root)
        self.tabs = []


    def on_click(self, event):
        """
        Changes to the selected tab is a tab node is double clicked upon,
        otherwise pops up the text edit dialog, passing it the note object.
        """
        item = self.tree.GetPyData(event.GetItem())

        if item is None:
            return  # clicked on the root node
        if isinstance(item, int):
            self.gui.tabs.SetSelection(item)
        else:
            item.edit()

    def pop_up(self, event):
        """Brings up the context menu on right click"""
        self.PopupMenu(NotesPopup(self, event))

#----------------------------------------------------------------------

class NotesPopup(wx.Menu):
    """
    A context pop-up menu for notes, allowing the editing of a note or switching
    the tab selection to a particular sheet. The event is passed around, coming
    from a TreeCtrlEvent. No popup menu happens for the root node.
    """
    def __init__(self, parent, event):
        wx.Menu.__init__(self)
        self.parent = parent
        item = parent.tree.GetPyData(event.GetItem())
        ID = wx.NewId()

        if item is None:
            return  # root node
        if isinstance(item, int):  # sheet node
            menu = wx.MenuItem(self, ID, "Switch to")
        else:
            menu = wx.MenuItem(self, ID, "Edit")

        self.AppendItem(menu)
        method = lambda x: parent.on_click(event)
        self.Bind(wx.EVT_MENU, method, id=ID)

#----------------------------------------------------------------------

class SheetsPopup(wx.Menu):
    """
    A context pop-up menu for sheets, allowing to close and rename sheets.
    """
    def __init__(self, parent, pos):
        wx.Menu.__init__(self)

        self.parent = parent
        sheet = self.parent.tabs.HitTest(pos)
        rename = wx.NewId()
        export = wx.NewId()

        if sheet[0] < 0:
            self.sheet = self.parent.current_tab
        else:
            self.sheet = sheet[0]

        self.AppendItem(wx.MenuItem(self, wx.ID_NEW, "New Sheet"))
        self.AppendItem(wx.MenuItem(self, wx.ID_CLOSE, "Close Sheet"))
        self.AppendSeparator()
        self.AppendItem(wx.MenuItem(self, rename, "Rename Sheet"))
        self.AppendItem(wx.MenuItem(self, export, "Export Sheet"))

        self.Bind(wx.EVT_MENU, self.rename, id=rename)
        self.Bind(wx.EVT_MENU, self.export, id=export)
        self.Bind(wx.EVT_MENU, self.close, id=wx.ID_CLOSE)


    def rename(self, event):
        """Rename the selected sheet"""
        dlg = wx.TextEntryDialog(self.parent, "Rename this sheet to:",
                                                        "Rename sheet")
        dlg.SetValue(self.parent.tabs.GetPageText(self.sheet))

        if dlg.ShowModal() == wx.ID_CANCEL:
            dlg.Destroy()
        else:
            if dlg.GetValue():
                self.parent.tabs.SetPageText(self.sheet, dlg.GetValue())

    def close(self, event):
        """
        The close event uses current_tab to know which sheet to close, so set
        it to the selected tab from the menu
        """
        self.parent.current_tab = self.sheet
        self.parent.on_close_tab()

    def export(self, event):
        """Export the selected tab"""
        board = self.parent.board
        self.parent.board = self.parent.tabs.GetPage(self.sheet)
        self.parent.on_export()
        self.parent.board = board


#----------------------------------------------------------------------

class Thumbs(scrolled.ScrolledPanel):
    """
    Thumbnails of all tabs' drawings.
    """
    def __init__(self, parent, gui):
        scrolled.ScrolledPanel.__init__(self, parent, size=(170, -1),
                                        style=wx.VSCROLL | wx.RAISED_BORDER)
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer)
        self.SetScrollRate(0, 150)

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

            bmp = wx.EmptyBitmap(150, 150)
            memory = wx.MemoryDC()
            memory.SelectObject(bmp)
            memory.SetPen(wx.Pen((255, 255, 255), 1))
            memory.SetBrush(wx.Brush((255, 255, 255)))
            memory.Clear()
            memory.FloodFill(0, 0, (255, 255, 255), wx.FLOOD_BORDER)
            memory.SelectObject(wx.NullBitmap)

        text = wx.StaticText(self, label="Sheet " + str(_id + 1))
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
            self.text[x].SetLabel("Sheet " + str(x + 1))


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
        self.SetBackgroundColour(wx.WHITE)


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
        gcdc.SetBrush(wx.Brush(wx.Color(0, 0, 255, 65)))  # light blue
        gcdc.SetPen(wx.Pen((0, 0, 0), 1, wx.TRANSPARENT))
        gcdc.DrawRectangle(0, 0, 150, 150)

        dc.SelectObject(wx.NullBitmap)
        self.SetBitmapLabel(_copy)


#----------------------------------------------------------------------

if __name__ == '__main__':
    from gui import WhyteboardApp
    app = WhyteboardApp(True)
    app.MainLoop()
