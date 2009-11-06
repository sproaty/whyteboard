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
This module contains classes for the GUI side panels and pop-up menus.
"""

import os

import wx
import wx.lib.colourselect as csel
from wx.lib import scrolledpanel as scrolled
from wx.lib.buttons import GenBitmapToggleButton

from copy import copy

from functions import make_bitmap

_ = wx.GetTranslation


#----------------------------------------------------------------------


class ControlPanel(wx.Panel):
    """
    This class implements a control panel for the GUI. It creates buttons or
    icons for each tool that can be drawn with on the Whyteboard; a drop-down
    menu for the line thickness and a ColourPicker for choosing the drawing
    colour. A preview of what the tool will look like is also shown.

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
        self.pane = self.cp.GetPane()  # every widget's parent
        self.gui = gui
        self.toggled = 1  # Pen, initallly
        self.preview = DrawingPreview(self.pane, self.gui)
        self.tools = {}

        sizer = wx.BoxSizer(wx.VERTICAL)
        csizer = wx.BoxSizer(wx.VERTICAL)

        cols = 1
        if gui.util.config['toolbox'] == 'icon':
            cols = 2

        self.toolsizer = wx.GridSizer(cols=cols, hgap=1, vgap=2)
        self.make_toolbox(gui.util.config['toolbox'])

        width = wx.StaticText(self.pane, label=_("Thickness:"))
        prev = wx.StaticText(self.pane, label=_("Preview:"))
        #self.colour = wx.ColourPickerCtrl(self.pane)
        #self.colour.SetToolTipString(_("Select a custom color"))
        colour = self.colour_buttons()

        self.grid = wx.GridSizer(cols=3, hgap=2, vgap=2)
        self.make_colour_grid()

        choices = ''.join(str(i) + " " for i in range(1, 26) ).split()

        self.thickness = wx.ComboBox(self.pane, choices=choices, size=(25, 25),
                                        style=wx.CB_READONLY)
        self.thickness.SetSelection(0)
        self.thickness.SetToolTipString(_("Sets the drawing thickness"))

        spacing = 4
        box = wx.BoxSizer(wx.VERTICAL)
        box.Add(self.toolsizer, 0, wx.ALIGN_CENTER | wx.ALL, spacing)
        box.Add(wx.StaticLine(self), 0, wx.EXPAND | wx.ALL, spacing)
        box.Add(self.grid, 0, wx.EXPAND | wx.ALL, spacing)
        box.Add(colour, 0, wx.EXPAND | wx.ALL, spacing)
        box.Add((5, 10))
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

        self.thickness.Bind(wx.EVT_COMBOBOX, self.change_thickness)


    def colour_buttons(self):
        panel = wx.Panel(self.pane)
        self.colour = csel.ColourSelect(panel, pos=(0, 0), size=(60, 60))
        parent = panel
        if os.name == "nt":
            parent = self.colour

        self.background = csel.ColourSelect(parent, pos=(0, 30), size=(30, 30))
        self.background.SetValue("White")
        self.transparent = wx.CheckBox(panel, label=_("Transparent"), pos=(0, 69))
        self.transparent.SetValue(True)

        self.colour.Bind(csel.EVT_COLOURSELECT, self.change_colour)
        self.background.Bind(csel.EVT_COLOURSELECT, self.change_background)
        self.transparent.Bind(wx.EVT_CHECKBOX, self.on_transparency)
        self.colour.SetToolTipString(_("Set the foreground colour"))
        self.background.SetToolTipString(_("Set the background colour"))
        self.transparent.SetToolTipString(_("Ignores the background colour"))

        return panel


    def make_toolbox(self, _type="text"):
        """Creates a toolbox made from toggleable text or icon buttons"""
        items = [_(i.name) for i in self.gui.util.items]
        if _type == "icon":
            items = [_(i.icon) for i in self.gui.util.items]

        for x, val in enumerate(items):
            if _type == "icon":
                path = os.path.join(self.gui.util.get_path(), "images",
                                    "tools", val + ".png")
                b = GenBitmapToggleButton(self.pane, x + 1, wx.Bitmap(path))
                evt = wx.EVT_BUTTON
            else:
                b = wx.ToggleButton(self.pane, x + 1, val)
                evt = wx.EVT_TOGGLEBUTTON

            b.SetToolTipString(_(self.gui.util.items[x].tooltip)+"\n"+_("Shortcut Key:")
                               + " " + self.gui.util.items[x].hotkey.upper())
            b.Bind(evt, self.change_tool, id=x + 1)
            self.toolsizer.Add(b, 0, wx.EXPAND | wx.RIGHT, 2)
            self.tools[x + 1] = b
        self.tools[self.toggled].SetValue(True)


    def make_colour_grid(self):
        """Builds a colour grid from the user's preferred colours"""
        colours = []
        for x in range(1, 10):
            col = self.gui.util.config["colour"+str(x)]
            colours.append([int(c) for c in col])

        for colour in colours:
            method = lambda evt, col = colour: self.change_colour(evt, col)
            method2 = lambda evt, col = colour: self.change_background(evt, col)

            b = wx.BitmapButton(self.pane, bitmap=make_bitmap(colour))
            self.grid.Add(b, 0)
            b.Bind(wx.EVT_BUTTON, method)
            b.Bind(wx.EVT_RIGHT_UP, method2)



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


    def change_tool(self, event=None, _id=None):
        """
        Toggles the tool buttons on/off and calls select_tool on the drawing
        panel.
        """
        new = self.gui.util.tool
        if event and not _id:
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


    def on_transparency(self, event):
        """Toggles the pane and its widgets"""
        if event.Checked() and not self.gui.board.selected:
            self.gui.util.transparent = True
        else:
            self.gui.util.transparent = False

        if self.gui.board.selected:
            self.gui.board.add_undo()
            val = wx.TRANSPARENT

            if self.gui.board.selected.background == wx.TRANSPARENT:
                val = self.background.GetColour()

            self.gui.board.selected.background = val

            self.gui.board.selected.make_pen()
            self.gui.board.redraw_all(True)
        self.gui.board.select_tool()



    def change_colour(self, event=None, colour=None):
        """Event can also be a string representing a colour (from the grid)"""
        if event and not colour:
            colour = event.GetValue()  # from the colour button
        self.colour.SetColour(colour)
        self.update(colour, "colour")


    def change_background(self, event=None, colour=None):
        """Event can also be a string representing a colour (from the grid)"""
        if event and not colour:
            colour = event.GetValue()  # from the colour button
        self.background.SetColour(colour)
        self.update(colour, "background")


    def change_thickness(self, event=None):
        self.update(self.thickness.GetSelection(), "thickness")


    def update(self, value, var_name):
        """Updates the given utility variable and the selected shape"""
        setattr(self.gui.util, var_name, value)

        if self.gui.board.selected:
            self.gui.board.add_undo()
            setattr(self.gui.board.selected, var_name, value)
            self.gui.board.redraw_all(True)
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
        self.SetToolTipString(_("A preview of your drawing"))

    def on_paint(self, event=None):
        """
        Draws the tool inside the box when tool/colour/thickness
        is changed
        """
        if self.gui.board:
            dc = wx.PaintDC(self)
            dc.SetPen(self.gui.board.shape.pen)
            if self.gui.util.transparent:
                dc.SetBrush(wx.TRANSPARENT_BRUSH)
            else:
                dc.SetBrush(self.gui.board.shape.brush)

            width, height = self.GetClientSize()
            self.gui.board.shape.preview(dc, width, height)

            dc.SetPen(wx.Pen((0, 0, 0), 1, wx.SOLID))
            dc.SetBrush(wx.TRANSPARENT_BRUSH)
            width, height = self.GetClientSize()
            dc.DrawRectangle(0, 0, width, height)  # draw a border..


#----------------------------------------------------------------------


class SidePanel(wx.Panel):
    """
    The side panel is a tabbed window, allowing the user to switch between
    thumbnails and notes. It can be toggled on and off via CollapsiblePane
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
        self.tabs.AddPage(self.thumbs, _("Thumbnails"))
        self.tabs.AddPage(self.notes, _("Notes"))

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
    Contains a Tree which shows an overview of all sheets' notes.
    Each sheet is a child of the tree, with each Note a child of a sheet.
    Sheets can be right clicked to pop-up a menu; or double clicked to change
    to that sheet.  Notes can be double/right clicked upon to be edited.
    """
    def __init__(self, parent, gui):
        wx.Panel.__init__(self, parent, size=(170, -1), style=wx.RAISED_BORDER)
        self.gui = gui
        self.tree = wx.TreeCtrl(self, style=wx.TR_HAS_BUTTONS)
        self.root = self.tree.AddRoot("Whyteboard")
        self.tabs = []
        self.notes = []
        self.add_tab()
        self.tree.Expand(self.root)

        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.tree, 1, wx.EXPAND)  # fills out vertical space
        self.SetSizer(self.sizer)
        self.tree.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.on_click)
        self.tree.Bind(wx.EVT_TREE_ITEM_RIGHT_CLICK, self.pop_up)


    def add_tab(self, name=None):
        """Adds a new tab as a child to the root element"""
        _id = len(self.tabs)
        if not _id:
            _id = 0
        if not name:
            name = _("Sheet")+" %s" % (_id + 1)

        data = wx.TreeItemData(_id)
        t = self.tree.AppendItem(self.root, name, data=data)
        self.tabs.insert(_id, t)


    def add_note(self, note, _id=None):
        """
        Adds a note to the current tab tree element. The notes' text is the
        element's text in the tree - newlines are replaced to stop the tree's
        formatting becoming too wide.
        """
        text = note.text.replace("\n", " ")[:15]

        if not _id:
            _id = self.tabs[self.gui.tabs.GetSelection()]
        else:
            _id = self.tabs[_id]
        data = wx.TreeItemData(note)
        note.tree_id = self.tree.AppendItem(_id, text, data=data)
        self.tree.Expand(_id)


    def remove_tab(self, note):
        """Removes a tab and its children."""
        item = self.tabs[note]
        self.tree.DeleteChildren(item)
        self.tree.Delete(item)

        del self.tabs[note]
        # now ensure all nodes are linked to the right tab
        count = self.gui.current_tab
        for x in range(self.gui.current_tab, len(self.tabs)):
            self.tree.SetItemData(self.tabs[x], wx.TreeItemData(x))


    def update_name(self, _id, name):
        """Renames a given sheet"""
        self.tree.SetItemText(self.tabs[_id], name)

    def remove_all(self):
        """Removes all tabs."""
        self.tree.DeleteChildren(self.root)
        self.tabs = []
        self.notes = []


    def on_click(self, event):
        """
        Changes to the selected tab if a tab node is double clicked upon,
        otherwise we're editing the note.
        """
        item = self.tree.GetPyData(event.GetItem())

        if item is None:  # clicked on the root node
            return
        if isinstance(item, int):
            self.gui.tabs.SetSelection(item)
            self.gui.on_change_tab()
        else:
            item.edit()

    def pop_up(self, event):
        """Brings up the context menu on right click (except on root node)"""
        if self.tree.GetPyData(event.GetItem()) is not None:
            self.PopupMenu(NotesPopup(self, self.gui, event))


#----------------------------------------------------------------------


class Popup(wx.Menu):
    """
    A general pop-up menum providing default menu items. Easy to subclass to add
    new functionality. The "extra" (of type wx.Event*) variable must be passed
    around a lot as different subclasses access different functions of different
    events
    """
    def __init__(self, parent, gui, extra):
        wx.Menu.__init__(self)
        self.parent = parent
        self.gui = gui
        self.item = None
        self.set_item(extra)
        self.make_menu(extra)

    def make_menu(self, extra):
        ID, ID2, ID3 = wx.NewId(),  wx.NewId(), wx.NewId()
        method = self.select_tab_method(extra)

        self.AppendItem(wx.MenuItem(self, ID, _("Select")))
        self.AppendSeparator()
        self.AppendItem(wx.MenuItem(self, wx.ID_NEW, _("New")+"\tCtrl-T"))
        self.AppendItem(wx.MenuItem(self, wx.ID_CLOSE, _("Close")))
        self.AppendSeparator()
        self.AppendItem(wx.MenuItem(self, ID2, _("Rename...")))
        self.AppendItem(wx.MenuItem(self, ID3, _("Export...")+"\tCtrl-E"))

        self.Bind(wx.EVT_MENU, method, id=ID)
        self.Bind(wx.EVT_MENU, self.rename, id=ID2)
        self.Bind(wx.EVT_MENU, self.close, id=wx.ID_CLOSE)
        self.Bind(wx.EVT_MENU, self.export, id=ID3)


    def close(self, event):
        self.gui.current_tab = self.item
        self.gui.board = self.gui.tabs.GetPage(self.item)
        self.gui.on_close_tab()

    def export(self, event):
        board = self.gui.board
        self.gui.board = self.gui.tabs.GetPage(self.item)
        self.gui.on_export()
        self.gui.board = board

    def rename(self, event):
        self.gui.on_rename(sheet=self.item)

    def select_tab_method(self, extra):
        pass

    def set_item(self, extra):
        pass


#----------------------------------------------------------------------


class NotesPopup(Popup):
    """
    Parent = Notes panel - needs access to tree's events and methods. Overwrites
    the menu for a note
    """
    def make_menu(self, extra):
        if self.item is None:  # root node
            return
        if isinstance(self.item, int):  # sheet node
            super(NotesPopup, self).make_menu(extra)
        else:
            ID = wx.NewId()
            menu = wx.MenuItem(self, ID, _("Edit Note..."))
            self.AppendItem(menu)
            method = self.select_tab_method(extra)
            self.Bind(wx.EVT_MENU, method, id=ID)

    def select_tab_method(self, extra):
        return lambda x: self.parent.on_click(extra)

    def set_item(self, extra):
        self.item = self.parent.tree.GetPyData(extra.GetItem())

#----------------------------------------------------------------------


class SheetsPopup(Popup):
    """
    Brought up by right-clicking the tab list. Its parent is the GUI
    """
    def set_item(self, extra):
        """Hit test on the tab bar"""
        self.item = extra#sheet = self.parent.tabs.HitTest(extra)
        #self.item = sheet[0]
        #if sheet[0] < 0:
        #    self.item = self.parent.current_tab


    def select_tab_method(self, extra):
        return lambda x: self.bleh()

    def bleh(self):
        self.parent.tabs.SetSelection(self.item)
        self.parent.on_change_tab()


#----------------------------------------------------------------------


class ThumbsPopup(SheetsPopup):
    """
    Just need to set the item to the current tab number, parent: tab number
    """

    def bleh(self,):
        self.parent.gui.tabs.SetSelection(self.item)
        self.parent.gui.on_change_tab()

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
        self.SetScrollRate(0, 170)

        self.gui = gui
        self.thumbs  = []  # ThumbButtons
        self.text = []  # StaticTexts
        self.new_thumb()  # inital thumb
        self.thumbs[0].current = True


    def new_thumb(self, _id=0, name=None):
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
            if os.name == "nt":
                memory.SetPen(wx.Pen(wx.BLACK, 1, wx.SOLID))
                memory.SetBrush(wx.TRANSPARENT_BRUSH)
                memory.DrawRectangle(0, 0, 150, 150)
            memory.SelectObject(wx.NullBitmap)

        btn = ThumbButton(self, _id, bmp, name)
        if not name:
            name = _("Sheet")+" %s" % (_id + 1)

        text = wx.StaticText(self, label=name)
        self.text.insert(_id, text)
        self.thumbs.insert(_id, btn)

        self.sizer.Add(text, 0, wx.ALIGN_CENTER | wx.TOP, 13)
        self.sizer.Add(btn, 0, wx.ALIGN_CENTER | wx.TOP, 7)
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
        count = self.gui.current_tab
        for x in range(self.gui.current_tab, len(self.thumbs)):
            self.thumbs[x].thumb_id = x


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
        img = wx.ImageFromBitmap(board.buffer)
        img.Rescale(150, 150)
        bitmap = wx.BitmapFromImage(img)

        if os.name == "nt":
            memory = wx.MemoryDC()
            memory.SelectObject(bitmap)
            memory.SetPen(wx.Pen(wx.BLACK, 1, wx.SOLID))
            memory.SetBrush(wx.TRANSPARENT_BRUSH)
            memory.DrawRectangle(0, 0, 150, 150)
            memory.SelectObject(wx.NullBitmap)
        return bitmap


    def update_name(self, _id, name):
        self.text[_id].SetLabel(name)
        self.Layout()

    def update(self, _id):
        """
        Updates a single thumbnail.
        """
        bmp = self.redraw(_id)
        thumb = self.thumbs[_id]
        thumb.SetBitmapLabel(bmp)
        self.thumbs[_id].buffer = bmp

        if thumb.current:
            thumb.highlight()


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
    def __init__(self, parent, _id, bitmap, name=None):
        wx.BitmapButton.__init__(self, parent, size=(150, 150))
        self.thumb_id  = _id
        self.parent = parent
        self.SetBitmapLabel(bitmap)
        self.buffer = bitmap
        self.current = False  # active thumb?
        self.Bind(wx.EVT_BUTTON, self.on_press)
        self.SetBackgroundColour(wx.WHITE)
        self.Bind(wx.EVT_RIGHT_UP, self.tab_popup)

    def tab_popup(self, event):
        """ Pops up the tab context menu. """
        self.PopupMenu(ThumbsPopup(self.parent, self.parent.gui, self.thumb_id))


    def on_press(self, event):
        """
        Changes the tab to the selected button, deselect previous one
        """
        self.parent.gui.tabs.SetSelection(self.thumb_id)
        self.parent.gui.on_change_tab()


    def update(self):
        for thumb in self.parent.thumbs:
            if thumb.thumb_id != self.thumb_id:
                if thumb.current:
                    thumb.current = False
                    self.parent.update(thumb.thumb_id)

        self.current = True
        self.parent.update(self.thumb_id)


    def highlight(self):
        """
        Highlights the current thumbnail with a light overlay.
        """
        _copy = copy(self.buffer)
        dc = wx.MemoryDC()
        dc.SelectObject(_copy)

        gcdc = wx.GCDC(dc)
        gcdc.SetBrush(wx.Brush(wx.Color(0, 0, 255, 50)))  # light blue
        gcdc.SetPen(wx.Pen((0, 0, 0), 1, wx.TRANSPARENT))
        gcdc.DrawRectangle(0, 0, 150, 150)

        dc.SelectObject(wx.NullBitmap)
        self.SetBitmapLabel(_copy)


#----------------------------------------------------------------------