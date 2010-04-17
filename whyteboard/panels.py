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
This module contains classes for the GUI side panels and pop-up menus.
"""

from __future__ import division
import os

import wx
import wx.media
import wx.lib.colourselect as csel
from wx.lib.wordwrap import wordwrap as wordwrap
from wx.lib import scrolledpanel as scrolled
from wx.lib.buttons import GenBitmapToggleButton

from lib.pubsub import pub

import meta
from utility import MediaDropTarget
from event_ids import *
from functions import create_colour_bitmap, get_time

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
        wx.Panel.__init__(self, gui, style=0 | wx.RAISED_BORDER)

        cp = wx.CollapsiblePane(self, style=wx.CP_DEFAULT_STYLE | wx.CP_NO_TLW_RESIZE)
        self.pane = cp.GetPane()  # every widget's parent
        self.gui = gui
        self.toggled = 1  # Pen, initallly
        self.preview = DrawingPreview(self.pane, self.gui)
        self.tools = {}
        sizer = wx.BoxSizer(wx.VERTICAL)
        csizer = wx.BoxSizer(wx.VERTICAL)
        thickness = wx.StaticText(self.pane, label=_("Thickness:"))
        #prev = wx.StaticText(self.pane, label=_("Preview:"))

        colour = self.colour_buttons()
        self.grid = wx.GridSizer(cols=3, hgap=4, vgap=4)
        self.toolsizer = wx.GridSizer(cols=1, hgap=5, vgap=5)
        self.make_colour_grid()
        self.make_toolbox(gui.util.config['toolbox'])

        choices = ''.join(str(i) + " " for i in range(1, 35) ).split()
        self.thickness = wx.ComboBox(self.pane, choices=choices, size=(25, 25),
                                        style=wx.CB_READONLY)
        self.thickness.SetSelection(0)
        self.thickness.SetToolTipString(_("Sets the drawing thickness"))
        line = wx.StaticLine(self, size=(-1, 30))
        line.SetBackgroundColour((0, 0, 0))
        spacing = 4
        box = wx.BoxSizer(wx.VERTICAL)
        box.Add(self.toolsizer, 0, wx.ALIGN_CENTER | wx.ALL, spacing)
        box.Add((5, 8))
        box.Add(self.grid, 0, wx.EXPAND | wx.ALL, spacing)
        box.Add((5, 8))
        box.Add(colour, 0, wx.EXPAND | wx.ALL, spacing)
        box.Add((5, 10))
        box.Add(thickness, 0, wx.ALL | wx.ALIGN_CENTER, spacing)
        box.Add(self.thickness, 0, wx.EXPAND | wx.ALL, spacing)
        box.Add((5, 5))
        #box.Add(prev, 0, wx.ALL | wx.ALIGN_CENTER, spacing)
        box.Add(self.preview, 0, wx.EXPAND | wx.ALL, spacing)
        csizer.Add(box, 1, wx.EXPAND)
        sizer.Add(cp, 1, wx.EXPAND)

        self.SetSizer(sizer)
        cp.GetPane().SetSizer(csizer)
        cp.Expand()
        self.control_sizer = box
        self.background.Raise()

        if not self.gui.util.config['tool_preview']:
            self.preview.Hide()
        if not self.gui.util.config['colour_grid']:
            box.Hide(self.grid)

        self.Bind(wx.EVT_COLLAPSIBLEPANE_CHANGED, self.toggle)
        self.Bind(wx.EVT_MOUSEWHEEL, self.scroll)
        self.Bind(wx.EVT_COMBOBOX, self.change_thickness, self.thickness)


    def colour_buttons(self):
        panel = wx.Panel(self.pane)
        self.colour = csel.ColourSelect(panel, pos=(0, 0), size=(60, 60))
        parent = panel
        if os.name == "nt":
            parent = self.colour  # segfaults otherwise

        sizer = wx.BoxSizer()
        swap_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.background = csel.ColourSelect(parent, pos=(0, 30), size=(30, 30))
        self.background.SetValue("White")
        self.transparent = wx.CheckBox(panel, label=_("Transparent"), pos=(0, 69))
        self.transparent.SetValue(True)
        icon = os.path.join(self.gui.util.get_path(), "images",
                            "icons", "swap_colours.png")

        swap = wx.BitmapButton(panel, bitmap=wx.Bitmap(icon), pos=(70, 0),
                                     style=wx.NO_BORDER)

        self.colour.Bind(csel.EVT_COLOURSELECT, self.change_colour)
        self.background.Bind(csel.EVT_COLOURSELECT, self.change_background)
        self.transparent.Bind(wx.EVT_CHECKBOX, self.on_transparency)
        swap.Bind(wx.EVT_BUTTON, self.on_swap)

        self.colour.SetToolTipString(_("Set the foreground color"))
        self.background.SetToolTipString(_("Set the background color"))
        self.transparent.SetToolTipString(_("Ignores the background color"))
        swap.SetToolTipString(_("Swaps the foreground and background colors"))

        sizer.Add(self.background)
        sizer.Add(self.colour)
        sizer.Add(self.transparent)
        swap_sizer.Add(sizer)
        swap_sizer.Add(swap, flag=wx.ALIGN_RIGHT)
        return panel


    def make_toolbox(self, _type="text"):
        """Creates a toolbox made from toggleable text or icon buttons"""
        items = [_(i.name) for i in self.gui.util.items]
        self.toolsizer.SetCols(1)

        if _type == "icon":
            items = [_(i.icon) for i in self.gui.util.items]
            self.toolsizer.SetCols(int(self.gui.util.config['toolbox_columns']))

        for x, val in enumerate(items):
            if _type == "icon":
                path = os.path.join(self.gui.util.get_path(), "images", "tools",
                                    val.decode("utf-8") + ".png")
                b = GenBitmapToggleButton(self.pane, x + 1, wx.Bitmap(path),
                                          style=wx.NO_BORDER)
                evt = wx.EVT_BUTTON
            else:
                b = wx.ToggleButton(self.pane, x + 1, val)
                evt = wx.EVT_TOGGLEBUTTON

            b.SetToolTipString("%s\n%s %s" % (_(self.gui.util.items[x].tooltip),
                                            _("Shortcut Key:"),
                                            self.gui.util.items[x].hotkey.upper()))

            b.Bind(evt, self.change_tool, id=x + 1)
            self.toolsizer.Add(b, 0, wx.EXPAND | wx.RIGHT, 2)
            self.tools[x + 1] = b
        self.tools[self.toggled].SetValue(True)


    def make_colour_grid(self):
        """Builds a colour grid from the user's preferred colours"""
        colours = []
        for x in range(1, 10):
            col = self.gui.util.config["colour%s" % x]
            colours.append([int(c) for c in col])

        for colour in colours:
            method = lambda evt, col = colour: self.change_colour(evt, col)
            method2 = lambda evt, col = colour: self.change_background(evt, col)

            b = wx.BitmapButton(self.pane, bitmap=create_colour_bitmap(colour))
            self.grid.Add(b, 0)
            b.Bind(wx.EVT_BUTTON, method)
            b.Bind(wx.EVT_RIGHT_UP, method2)


    def toggle(self, evt):
        """Toggles the collapsible pane and its widgets"""
        self.gui.Layout()
        self.gui.board.redraw_all()  # fixes a windows redraw bug


    def scroll(self, event):
        """Scrolls the thickness drop-down box (for Windows)"""
        val = self.thickness.GetSelection()
        if event.GetWheelRotation() > 0:  # mousewheel down
            val -= 1
            if val <= 0:
                val = 0
        else:
            val += 1

        self.thickness.SetSelection(val)
        self.change_thickness()


    def change_tool(self, event=None, _id=None):
        """
        Toggles the tool buttons on/off and calls change_current_tool on the drawing
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
            self.gui.board.change_current_tool(new)


    def on_transparency(self, event):
        """Toggles transparency in the shapes' background"""
        if event.Checked() and not self.gui.board.selected:
            self.gui.util.transparent = True
        else:
            self.gui.util.transparent = False

        if self.gui.board.selected:
            self.gui.board.toggle_transparent()
        self.gui.board.change_current_tool()


    def on_swap(self, event):
        """Swaps foreground/background colours"""
        a, b = self.background.GetColour(), self.colour.GetColour()
        self.background.SetColour(b)
        self.colour.SetColour(a)

        self.gui.util.colour = a
        if not self.transparent.IsChecked():
            self.gui.util.background = a
        self.gui.board.change_current_tool()


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
            if var_name == "background" and not self.transparent.IsChecked():
                setattr(self.gui.board.selected, var_name, value)
            elif var_name != "background":
                setattr(self.gui.board.selected, var_name, value)
            self.gui.board.redraw_all(True)

        self.gui.board.change_current_tool()
        self.preview.Refresh()


#----------------------------------------------------------------------


class DrawingPreview(wx.Window):
    """
    Shows a sample of what the current tool's drawing will look like.
    Pane is the collapsible pane, its parent.
    """
    def __init__(self, pane, gui):
        """
        Stores gui reference to access utility colour/thickness attributes.
        """
        wx.Window.__init__(self, pane)
        self.gui = gui
        self.SetBackgroundColour(wx.WHITE)
        self.SetSize((45, 45))
        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.SetToolTipString(_("A preview of your current tool"))

    def on_paint(self, event=None):
        """
        Draws the tool inside the box when tool/colour/thickness
        is changed
        """
        if self.gui.board:
            dc = wx.PaintDC(self)
            dc.SetPen(wx.Pen(self.gui.board.shape.colour, self.gui.board.shape.thickness, wx.SOLID))
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

class MediaPanel(wx.Window):
    """
    A panel that contains a MediaCtrl for playing videos/audio, and buttons for
    controlling it: open (file)/pause/stop/play, and a slider bar.
    Used by the Media tool.
    """
    def __init__(self, parent, pos, tool):
        wx.Window.__init__(self, parent, pos=pos, style=wx.CLIP_CHILDREN)
        self.gui = parent.gui
        self.tool = tool
        self.offset = (0, 0)
        self.directory = None
        self.mc = wx.media.MediaCtrl(self, style=wx.SIMPLE_BORDER)
        self.timer = wx.Timer(self)  # updates the slider as the file plays
        self.SetCursor(wx.StockCursor(wx.CURSOR_ARROW))
        self.total = ""  # total time

        self.file_drop = MediaDropTarget(self)
        self.SetDropTarget(self.file_drop)

        path = os.path.join(self.gui.util.get_path(), "images", "icons", "")
        self.open = wx.BitmapButton(self, bitmap=wx.ArtProvider.GetBitmap(wx.ART_FILE_OPEN, wx.ART_TOOLBAR))
        self.play = wx.BitmapButton(self, bitmap=wx.Bitmap(path + "play.png"))
        self.pause = wx.BitmapButton(self, bitmap=wx.Bitmap(path +  "pause.png"))
        self.stop = wx.BitmapButton(self, bitmap=wx.Bitmap(path + "stop.png"))
        self.play.Disable()
        self.pause.Disable()
        self.stop.Disable()

        self.file = wx.StaticText(self)
        self.elapsed = wx.StaticText(self)
        timesizer = wx.BoxSizer(wx.HORIZONTAL)
        timesizer.Add(self.file, 1, wx.LEFT | wx.RIGHT, 5)
        timesizer.Add(self.elapsed, 0, wx.ALIGN_RIGHT | wx.RIGHT, 5)

        self.slider = wx.Slider(self)
        self.slider.SetToolTipString(_("Skip to a position "))
        self.volume = wx.Slider(self, value=100, style=wx.SL_VERTICAL | wx.SL_INVERSE)
        self.volume.SetToolTipString(_("Set the volume"))
        self.slider.SetMinSize((150, -1))
        self.volume.SetMinSize((-1, 75))

        sizer = wx.GridBagSizer(6, 5)
        sizer.Add(self.mc, (1, 1), span=(5, 1))
        sizer.Add(self.open, (1, 3), flag=wx.RIGHT, border=10)
        sizer.Add(self.play, (2, 3), flag=wx.RIGHT, border=10)
        sizer.Add(self.pause, (3, 3), flag=wx.RIGHT, border=10)
        sizer.Add(self.stop, (4, 3), flag=wx.RIGHT, border=10)
        sizer.Add(self.volume, (5, 3), flag=wx.RIGHT, border=10)
        sizer.Add(self.slider, (6, 1), flag=wx.EXPAND)
        sizer.Add(timesizer, (7, 1), flag=wx.EXPAND | wx.BOTTOM, border=10)
        self.SetSizer(sizer)
        self.Layout()
        self.Fit()

        self.Bind(wx.media.EVT_MEDIA_LOADED, self.media_loaded)
        self.Bind(wx.media.EVT_MEDIA_STOP, self.media_stopped)
        self.Bind(wx.EVT_BUTTON, self.load_file, self.open)
        self.Bind(wx.EVT_BUTTON, self.on_play, self.play)
        self.Bind(wx.EVT_BUTTON, self.on_pause, self.pause)
        self.Bind(wx.EVT_BUTTON, self.on_stop, self.stop)
        self.Bind(wx.EVT_SLIDER, self.on_seek, self.slider)
        self.Bind(wx.EVT_SLIDER, self.on_volume, self.volume)
        self.Bind(wx.EVT_LEFT_UP, self.left_up)
        self.Bind(wx.EVT_LEFT_DOWN, self.left_down)
        self.Bind(wx.EVT_MOTION, self.left_motion)
        self.Bind(wx.EVT_TIMER, self.on_timer)
        self.timer.Start(650)


    def left_down(self, event):
        """Grab the mouse offset of the window relative the the top-left"""
        self.gui.board.selected = self.tool
        self.tool.selected = True
        self.CaptureMouse()
        pos = self.Parent.ScreenToClient(self.ClientToScreen(event.Position))

        self.offset = (pos[0] - self.tool.x, pos[1] - self.tool.y)


    def left_up(self, event):
        if self.HasCapture():
            self.ReleaseMouse()
        self.Layout()


    def left_motion(self, event):
        """Reposition the window with an offset"""
        if event.Dragging():
            pos = self.Parent.ScreenToClient(self.ClientToScreen(event.Position))
            pos = (pos[0] - self.offset[0], pos[1] - self.offset[1])

            self.tool.x, self.tool.y = pos
            self.SetPosition(pos)


    def load_file(self, evt):
        """
        Display a file chooser window and try to load the file
        """
        vids = "*.avi; *.mkv; *.mov; *.mpg; *ogg; *.wmv"
        audio = "*.mp3; *.oga; *.ogg; *.wav"
        wc = _("Media Files")+" |%s;%s|" % (vids, audio)
        wc += _("Video Files")+" (%s)|%s|" % (vids, vids)
        wc += _("Audio Files")+" (%s)|%s" % (audio, audio)

        _dir = ""
        if self.directory:
            _dir = self.directory

        dlg = wx.FileDialog(self, message=_("Choose a media file"),
                            wildcard=wc, style=wx.OPEN, defaultDir=_dir)
        if dlg.ShowModal() == wx.ID_OK:
            self.do_load_file(dlg.GetPath())
        dlg.Destroy()


    def do_load_file(self, path):
        """
        Loads a file from a given path, sets up instance variables and enables
        and disabled buttons
        """
        if not self.mc.Load(path):
            wx.MessageBox(_("Unable to load %s: Unsupported format?") % path,
                         "Whyteboard", wx.ICON_ERROR | wx.OK)
            self.play.Disable()
            self.pause.Disable()
            self.stop.Disable()
        else:
            if os.name == "posix":
                self.mc.Load(path)
        self.directory = path
        self.tool.filename = path


    def media_loaded(self, evt):
        """
        Called when a media file has finished loading. Calculates the total time
        of the file and updates the filename label
        """
        self.play.Enable()
        self.total = get_time(self.mc.Length() / 1000)
        wordwrap(os.path.basename(self.tool.filename), 350, wx.ClientDC(self.gui))
        self.file.SetLabel(os.path.basename(self.tool.filename))
        self.elapsed.SetLabel("00:00/" + self.total)
        self.mc.SetInitialSize()
        self.slider.SetRange(0, self.mc.Length())
        self.GetSizer().Layout()
        self.Fit()


    def media_stopped(self, evt):
        self.on_stop(None, True)

    def on_timer(self, evt):
        """Keep updating the timer label/scrollbar..."""
        if self.mc.GetState() == wx.media.MEDIASTATE_PLAYING:
            offset = self.mc.Tell()
            self.slider.SetValue(offset)
            self.elapsed.SetLabel(get_time(offset / 1000)+"/"+ self.total)


    def on_play(self, evt):
        if not self.mc.Play():
            wx.MessageBox(_("Unable to Play media : Unsupported format?"),
                          "Whyteboard", wx.ICON_ERROR | wx.OK)
        else:
            self.play.Disable()
            self.pause.Enable()
            self.stop.Enable()


    def on_pause(self, evt):
        self.mc.Pause()
        self.play.Enable()
        self.pause.Disable()

    def on_stop(self, evt, ignore=False):
        if not ignore:
            self.mc.Stop()
        self.slider.SetValue(0)
        self.elapsed.SetLabel("00:00/" + self.total)
        self.play.Enable()
        self.pause.Disable()
        self.stop.Disable()

    def on_seek(self, evt):
        self.mc.Seek(self.slider.GetValue())
        self.elapsed.SetLabel(get_time(self.slider.GetValue() / 1000) + "/" +
                              self.total )

    def on_volume(self, evt):
        self.mc.SetVolume(float(self.volume.GetValue() / 100))

#---------------------------------------------------------------------


class SidePanel(wx.Panel):
    """
    The side panel is a tabbed window, allowing the user to switch between
    thumbnails and notes. It can be toggled on and off via CollapsiblePane
    """
    def __init__(self, gui):
        wx.Panel.__init__(self, gui, style=wx.RAISED_BORDER)
        cp = wx.CollapsiblePane(self, style=wx.CP_DEFAULT_STYLE |
                                     wx.CP_NO_TLW_RESIZE)

        self.tabs = wx.Notebook(cp.GetPane())
        self.thumbs = Thumbs(self.tabs, gui)
        self.notes = Notes(self.tabs, gui)
        self.tabs.AddPage(self.thumbs, _("Thumbnails"))
        self.tabs.AddPage(self.notes, _("Notes"))

        sizer = wx.BoxSizer(wx.VERTICAL)
        csizer = wx.BoxSizer(wx.VERTICAL)
        csizer.Add(self.tabs, 1, wx.EXPAND)
        sizer.Add(cp, 1, wx.EXPAND)

        self.SetSizer(sizer)
        cp.GetPane().SetSizer(csizer)
        cp.Expand()
        self.Bind(wx.EVT_COLLAPSIBLEPANE_CHANGED, self.toggle)


    def toggle(self, evt):
        """Toggles the pane and its widgets"""
        self.GetTopLevelParent().Layout()


#----------------------------------------------------------------------


class Notes(wx.Panel):
    """
    Contains a Tree which shows an overview of all sheets' notes.
    Each sheet is a child of the tree, with each Note a child of a sheet.
    Sheets can be right clicked to pop-up a menu; or double clicked to change
    to that sheet.  Notes can be double/right clicked upon to be edited.
    """
    def __init__(self, parent, gui):
        wx.Panel.__init__(self, parent)
        self.gui = gui
        self.tree = wx.TreeCtrl(self, style=wx.TR_HAS_BUTTONS)
        self.root = self.tree.AddRoot("Whyteboard")
        self.tabs = []
        self.add_tab()
        self.tree.Expand(self.root)

        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.tree, 1, wx.EXPAND)  # fills vert space
        self.SetSizer(self.sizer)
        self.tree.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.on_click)
        self.tree.Bind(wx.EVT_TREE_ITEM_RIGHT_CLICK, self.pop_up)
        pub.subscribe(self.add_note, 'note.add')
        pub.subscribe(self.edit_note, 'note.edit')
        pub.subscribe(self.rename, 'sheet.rename')
        pub.subscribe(self.sheet_moved, 'sheet.move')


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
        _id = self.tabs[self.gui.tabs.GetSelection()]

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
        for x in range(self.gui.current_tab, len(self.tabs)):
            self.tree.SetItemData(self.tabs[x], wx.TreeItemData(x))


    def rename(self, _id, text):
        """Renames a given sheet"""
        self.tree.SetItemText(self.tabs[_id], text)


    def remove_all(self):
        """Removes all tabs."""
        self.tree.DeleteChildren(self.root)
        self.tabs = []


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


    def select(self, event, draw=True):
        """
        Selects a Note if unselected, otherwise it de-selects the note.
        draw forces a canvas redraw
        """
        item = self.tree.GetPyData(event.GetItem())

        if not item.selected:
            self.gui.board.deselect()
            item.selected = True
            self.gui.board.selected = item
        else:
            self.gui.board.deselect()

        if draw:
            self.gui.board.redraw_all()


    def delete(self, event):
        self.select(event, False)
        self.gui.board.delete_selected()

    def edit_note(self, tree_id, text):
        """Edit a non-blank Note by changing its tree item's text"""
        text = text.replace("\n", " ")[:15]
        self.tree.SetItemText(tree_id, text)


    def sheet_moved(self, event, tab_count):
        """
        Drag/drop sheet: move a tree item and its associated notes
        """
        tree = self.tree

        old_item = self.tabs[event.GetOldSelection()]
        text = tree.GetItemText(old_item)
        children = []

        # Save all Note item data to re-create it in the new Tree node
        if tree.ItemHasChildren(old_item):
            (child, cookie) = tree.GetFirstChild(old_item)
            while child.IsOk():
                item = (tree.GetItemPyData(child), tree.GetItemText(child))
                children.append(item)
                (child, cookie) = tree.GetNextChild(old_item, cookie)

        # Remove the old tree node, re-add it
        before = event.GetSelection()

        if event.GetSelection() >= tab_count:
            before = event.GetSelection() - 1
        if event.GetOldSelection() < event.GetSelection():  # drag to the right
            before += 1
        if before < 0:
            before = 0

        new = tree.InsertItemBefore(self.root, before, text)
        tree.Delete(old_item)

        # Restore the notes to the new tree item
        for item in children:
            data = wx.TreeItemData(item[0])
            item[0].tree_id = tree.AppendItem(new, item[1], data=data)

        # Reposition the tab in the list of wx.TreeItemID's for the loop below
        item = self.tabs.pop(event.GetOldSelection())
        self.tabs.insert(event.GetSelection(), item)

        # Update each tree's node data so it is pointing to the correct tab ID
        (child, cookie) = tree.GetFirstChild(self.root)
        count = 0

        while child.IsOk():
            self.tabs[count] = child
            tree.SetItemData(self.tabs[count], wx.TreeItemData(count))
            (child, cookie) = tree.GetNextChild(self.root, cookie)
            count += 1

        tree.Expand(new)


#----------------------------------------------------------------------


class Popup(wx.Menu):
    """
    A general pop-up menum providing default menu items. Easy to subclass to add
    new functionality. The "extra" (of type wx.Event*) variable must be passed
    around a lot as different subclasses access different functions of different
    events e.g. a TreeCtrl event to get its item, or a notebook tab change event
    """
    def __init__(self, parent, gui, extra):
        wx.Menu.__init__(self)
        self.parent = parent
        self.gui = gui
        self.item = None
        self.set_item(extra)
        self.make_menu(extra)

    def make_menu(self, extra):
        ID, ID2, ID3 = wx.NewId(), wx.NewId(), wx.NewId()

        self.Append(ID, _("&Select"))
        self.AppendSeparator()
        self.Append(wx.ID_NEW, _("&New Sheet")+"\tCtrl-T")
        self.Append(wx.ID_CLOSE, _("Re&move Sheet")+"\tCtrl-W")
        self.AppendSeparator()
        self.Append(ID2, _("&Rename...")+"\tF2")
        self.Append(ID3, _("&Export...")+"\tCtrl+E")

        self.Bind(wx.EVT_MENU, self.select_tab_method(extra), id=ID)
        self.Bind(wx.EVT_MENU, self.rename, id=ID2)
        self.Bind(wx.EVT_MENU, self.export, id=ID3)
        self.Bind(wx.EVT_MENU, self.close, id=wx.ID_CLOSE)


    def select_tab_method(self, extra):
        """Guess this is the class' interface..."""
        pass

    def set_item(self, extra):
        self.item = extra

    def close(self, event):
        self.gui.current_tab = self.item
        self.gui.board = self.gui.tabs.GetPage(self.item)
        self.gui.on_close_tab()

    def export(self, event):
        """
        Change board temporarily to 'trick' the gui into exporting the selected
        tab. Then, restore the GUI to the correct one
        """
        board = self.gui.board  # reference to restore
        self.gui.board = self.gui.tabs.GetPage(self.item)
        self.gui.on_export()
        self.gui.board = board

    def rename(self, event):
        self.gui.on_rename(sheet=self.item)


#----------------------------------------------------------------------


class NotesPopup(Popup):
    """
    Parent = Notes panel - needs access to tree's events and methods. Overwrites
    the menu for a note, adding in extra items
    """
    def make_menu(self, extra):
        if self.item is None:  # root node
            return
        if isinstance(self.item, int):  # sheet node
            super(NotesPopup, self).make_menu(extra)
        else:
            ID, ID2, ID3 = wx.NewId(), wx.NewId(), wx.NewId()
            text = _("&Select")

            if self.item.selected:
                text =  _("De&select")
            self.Append(ID, text)
            self.Append(ID2, _("&Edit Note..."))
            self.AppendSeparator()
            self.Append(ID3, _("&Delete")+"\tDelete")

            self.Bind(wx.EVT_MENU, lambda x: self.parent.select(extra), id=ID)
            self.Bind(wx.EVT_MENU, self.select_tab_method(extra), id=ID2)
            self.Bind(wx.EVT_MENU, lambda x: self.parent.delete(extra), id=ID3)


    def select_tab_method(self, extra):
        return lambda x: self.parent.on_click(extra)

    def set_item(self, extra):
        self.item = self.parent.tree.GetPyData(extra.GetItem())

#----------------------------------------------------------------------


class SheetsPopup(Popup):
    """
    Brought up by right-clicking the tab list. Its parent is the GUI
    """
    def select_tab_method(self, extra):
        return lambda x: self.bleh()

    def bleh(self):
        self.parent.tabs.SetSelection(self.item)
        self.parent.on_change_tab()


#----------------------------------------------------------------------


class ShapePopup(Popup):
    """
    Brought up by right-clicking on a shape with the Select tool
    """
    def make_menu(self, extra):
        SELECT, EDIT, DELETE, POINT, SWAP = wx.NewId(), wx.NewId(), wx.NewId(), wx.NewId(), wx.NewId()

        text, _help = _("&Select"), _("Selects this shape")
        if self.item.selected:
            text, _help =  _("De&select"), _("Deselects this shape")
        self.Append(SELECT, text, _help)

        self.Append(EDIT, _("&Edit..."), _("Edit the text"))
        self.Append(POINT, _("&Add New Point"), _("Adds a new point to the Polygon"))
        self.Append(wx.ID_DELETE, _("&Delete")+"\tDelete")
        self.AppendSeparator()
        self.AppendCheckItem(ID_TRANSPARENT, _("T&ransparent"))
        self.Append(ID_SWAP_COLOURS, _("Swap &Colors"))
        self.AppendSeparator()
        self.Append(ID_MOVE_UP, _("Move &Up")+"\tCtrl-Up")
        self.Append(ID_MOVE_DOWN, _("Move &Down")+"\tCtrl-Down")
        self.Append(ID_MOVE_TO_TOP, _("Move To &Top")+"\tCtrl-Shift-Up")
        self.Append(ID_MOVE_TO_BOTTOM, _("Move To &Bottom")+"\tCtrl-Shift-Down")

        if not self.item.name in ["Text", "Note"]:
            self.Enable(EDIT, False)
        if not self.item.name == "Polygon":
            self.Enable(POINT, False)

        if not self.item.name in ["Image", "Text", "Note"]:
            if self.item.background == wx.TRANSPARENT:
                self.Check(ID_TRANSPARENT, True)
                self.Enable(ID_SWAP_COLOURS, False)
        else:
            self.Enable(ID_TRANSPARENT, False)
            self.Enable(ID_SWAP_COLOURS, False)

        self.Bind(wx.EVT_MENU, lambda x: self.select(), id=SELECT)
        self.Bind(wx.EVT_MENU, lambda x: self.edit(), id=EDIT)
        self.Bind(wx.EVT_MENU, lambda x: self.delete(), id=DELETE)
        self.Bind(wx.EVT_MENU, lambda x: self.add_point(), id=POINT)
        self.Bind(wx.EVT_MENU, lambda x: self.swap(), id=SWAP)


    def edit(self):
        self.item.edit()

    def delete(self):
        self.select(False)
        self.gui.board.delete_selected()

    def swap(self):
        self.gui.on_swap_colour()


    def select(self, draw=True):
        if not self.item.selected:
            self.gui.board.deselect()
            self.item.selected = True
            self.gui.board.selected = self.item
        else:
            self.gui.board.deselect()

        if draw:
            self.gui.board.redraw_all()


    def add_point(self):
        self.gui.board.add_undo()
        self.item.points = list(self.item.points)
        x, y = self.gui.board.ScreenToClient(wx.GetMousePosition())
        x, y = self.gui.board.CalcUnscrolledPosition(x, y)
        self.item.points.append((float(x), float(y)))
        self.gui.board.redraw_all()

#----------------------------------------------------------------------

class ThumbsPopup(SheetsPopup):
    """
    Just need to set the item to the current tab number, parent: thumb panel
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
        scrolled.ScrolledPanel.__init__(self, parent, style=wx.VSCROLL)
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer)
        self.SetScrollRate(0, 120)

        self.gui = gui
        self.thumbs  = []  # ThumbButtons
        self.text = []  # StaticTexts
        self.new_thumb()  # inital thumb
        self.thumbs[0].current = True
        pub.subscribe(self.highlight_current, 'thumbs.text.highlight')
        pub.subscribe(self.rename, 'sheet.rename')


    def highlight_current(self, tab, select):
        if self.text:
            try:
                font = self.text[tab].GetClassDefaultAttributes().font
                font.SetWeight(wx.FONTWEIGHT_NORMAL)
                if select:
                    font.SetWeight(wx.FONTWEIGHT_BOLD)

                self.text[tab].SetFont(font)
            except IndexError:
                pass  # ignore a bug closing the last tab from the pop-up menu
                      # temp fix, can't think how to solve it otherwise


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
        for x in range(self.gui.current_tab, len(self.thumbs)):
            self.thumbs[x].thumb_id = x


    def remove_all(self):
        """
        Removes all thumbnails.
        """
        for x in range(len(self.thumbs)):
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


    def rename(self, _id, text):
        self.text[_id].SetLabel(text)
        self.Layout()

    def update(self, _id):
        """
        Updates a single thumbnail.
        """
        bmp = self.redraw(_id)
        thumb = self.thumbs[_id]
        thumb.SetBitmapLabel(bmp)
        self.thumbs[_id].buffer = bmp

        if thumb.current and meta.transparent:
            thumb.highlight()


    def update_all(self):
        """
        Updates all thumbnails (i.e. upon loading a Whyteboard file).
        """
        for count, item in enumerate(self.thumbs):
            self.update(count)


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
        """
        Iterates over each thumb and unhighlights the previously selected thumb
        Then, sets this thumb as the currently highlighted one and redraws
        """
        for thumb in self.parent.thumbs:
            if thumb.thumb_id != self.thumb_id:
                if thumb.current:
                    thumb.current = False
                    self.parent.update(thumb.thumb_id)

        self.current = True
        self.parent.update(self.thumb_id)


    def highlight(self):
        """
        Highlights the current thumbnail with a light transparent overlay.
        """
        dc = wx.MemoryDC()
        dc.SelectObject(self.buffer)

        gcdc = wx.GCDC(dc)
        gcdc.SetBrush(wx.Brush(wx.Color(0, 0, 255, 50)))  # light blue
        gcdc.SetPen(wx.Pen((0, 0, 0), 1, wx.TRANSPARENT))
        gcdc.DrawRectangle(0, 0, 150, 150)

        dc.SelectObject(wx.NullBitmap)
        self.SetBitmapLabel(self.buffer)


#----------------------------------------------------------------------