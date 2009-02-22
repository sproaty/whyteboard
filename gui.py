#!/usr/bin/python

# Copyright (c) 2009 by Steven Sproat
#
# GNU General Public Licence (GPL)
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 3 of the License, or (at your option) any later
# version.
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 59 Temple
# Place, Suite 330, Boston, MA  02111-1307  USA

"""
This module implements the Whteboard application.  It takes a Whyteboard class
and wraps it in a GUI with a menu/toolbar/statusbar; can save and load drawings,
clear the workspace, undo, redo, a simple history "replayer", allowing you to
have a replay of what you have drawn played back to you.

Also on the GUI is a panel for setting color and line thickness, with an
indicator that shows an example of the drawing-to-be
"""

import os
import wx
from wx.lib import scrolledpanel as scrolled

from copy import copy
from tools import Image
from whyteboard import Whyteboard
from utility import Utility
from dialogs import About, History, ConvertProgress



#----------------------------------------------------------------------

ID_EXPORT = wx.NewId()
ID_THUMBS = wx.NewId()
ID_HISTORY = wx.NewId()
ID_CLEAR_ALL = wx.NewId()      # remove all from current tab
ID_CLEAR_TABS = wx.NewId()     # remove all drawings from all tabs, keep images
ID_CLEAR_ALL_TABS = wx.NewId() # remove all from all tabs

class GUI(wx.Frame):
    """
    This class contains a Whyteboard frame, a ControlPanel and a Thumbnail Panel
    and manages their layout with a wx.BoxSizer.  A menu, toolbar and associated
    event handlers call the appropriate functions of other classes.
    """
    title = "Whyteboard"
    version = "0.34"

    def __init__(self, parent):
        """
        Initialise utility, status/menu/tool bar, tabs, ctrl panel + bindings.
        """
        wx.Frame.__init__(self, parent, size=(800, 600), title="Untitled - " +
           self.title, style=wx.DEFAULT_FRAME_STYLE | wx.FULL_REPAINT_ON_RESIZE)

        self.util = Utility(self)
        self.CreateStatusBar()
        self.make_toolbar()
        self.make_menu()
        self.tab_count = 1  # instead of typing self.tabs.GetPageCount()
        self.control = ControlPanel(self)
        self.tabs = wx.Notebook(self)
        self.board = Whyteboard(self.tabs)  # the active whiteboard tab
        self.tabs.AddPage(self.board, "Untitled 1")

        size = self.GetSize()
        self.thumbs = Thumbs(self, size[0])

        self.do_bindings()
        self.update_menus()
        self.box = wx.BoxSizer(wx.HORIZONTAL)  # position windows side-by-side
        self.box.Add(self.control, 0, wx.EXPAND)
        self.box.Add(self.tabs, 2, wx.EXPAND)
        self.box.Add(self.thumbs, 0, wx.EXPAND)
        self.SetSizer(self.box)
        self.Maximize(True)


    def make_menu(self):
        """
        Creates the menu...pretty damn messy, may give this a cleanup like the
        do_bindings/make_toolbar
        """
        _file = wx.Menu()
        history = wx.Menu()
        view = wx.Menu()
        image = wx.Menu()
        _help = wx.Menu()
        self.menuBar = wx.MenuBar()

        _file.Append(wx.ID_NEW, "New &Tab\tCtrl-T", "Open a new tab")
        _file.Append(wx.ID_OPEN, "&Open\tCtrl-O", "Load a Whyteboard save file, an image or convert a PDF/PS document")
        _file.Append(wx.ID_SAVE, "&Save\tCtrl-S", "Save the Whyteboard data")
        _file.Append(wx.ID_SAVEAS, "Save &As...\tCtrl-Shift-S", "Save the Whyteboard data in a new file")
        _file.Append(ID_EXPORT, "&Export\tCtrl-E", "Export the Whyteboard's contents to an image")
        _file.AppendSeparator()
        _file.Append(wx.ID_CLOSE, "&Close Tab\tCtrl-W", "Close current tab")
        _file.Append(wx.ID_EXIT, "E&xit\tAlt-F4", "Terminate Whyteboard")

        history.Append(wx.ID_UNDO, "&Undo\tCtrl-Z", "Undo the last operation")
        history.Append(wx.ID_REDO, "&Redo\tCtrl-Y", "Redo the last undone operation")
        history.AppendSeparator()
        history.Append(ID_HISTORY, "&History Viewer\tCtrl-H", "View and replay your drawing history")

        view.Append(ID_THUMBS, " &Toggle Thumbnails\tF9", "Toggle the thumbnail panel on or off", kind=wx.ITEM_CHECK)
        view.Check(ID_THUMBS, True)

        image.Append(wx.ID_CLEAR, "&Clear Tab's Drawings", "Clear drawings on the current tab (keep images)")
        image.Append(ID_CLEAR_ALL, "Clear &Tab", "Clear the current tab")
        image.AppendSeparator()
        image.Append(ID_CLEAR_TABS, "Clear All Tabs' &Drawings", "Clear all tabs of drawings (keep images)")
        image.Append(ID_CLEAR_ALL_TABS, "Clear &All Tabs", "Clear all open tabs")

        _help.Append(wx.ID_ABOUT, "&About\tF1", "View information about the Whyteboard application")
        self.menuBar.Append(_file, "&File")
        self.menuBar.Append(history, "&History")
        self.menuBar.Append(view, "&View")
        self.menuBar.Append(image, "&Image")
        self.menuBar.Append(_help, "&Help")
        self.SetMenuBar(self.menuBar)


    def do_bindings(self):
        """
        Performs event binding.
        """
        self.Bind(wx.EVT_CLOSE, self.on_exit)
        self.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.on_change_tab, self.tabs)
        self.Bind(wx.EVT_END_PROCESS, self.on_end_process)  # converted

        functs = ["new_tab", "close_tab", "open", "save", "save_as", "export",
                  "undo", "redo", "history", "thumbs", "clear", "clear_all",
                  "clear_tabs", "clear_all_tabs", "about", "exit"]

        IDs = [wx.ID_NEW, wx.ID_CLOSE, wx.ID_OPEN, wx.ID_SAVE, wx.ID_SAVEAS,
               ID_EXPORT, wx.ID_UNDO, wx.ID_REDO, ID_HISTORY, ID_THUMBS,
               wx.ID_CLEAR, ID_CLEAR_ALL, ID_CLEAR_TABS, ID_CLEAR_ALL_TABS,
               wx.ID_ABOUT, wx.ID_EXIT]

        for name, _id in zip(functs, IDs):
            method = getattr(self, "on_"+ name)  # self.on_*
            self.Bind(wx.EVT_MENU, method, id=_id )


    def make_toolbar(self):
        """
        Creates a toolbar, Pythonically :D
        """
        self.tb = self.CreateToolBar()

        ids = [wx.ID_NEW, wx.ID_OPEN, wx.ID_SAVE, wx.ID_UNDO, wx.ID_REDO]
        arts = [wx.ART_NEW, wx.ART_FILE_OPEN, wx.ART_FILE_SAVE, wx.ART_UNDO,
                wx.ART_REDO]
        tips = ["New Tab", "Open a File", "Save Drawing", "Undo Action",
                "Redo the Undone Action"]

        for _id, art_id, tip in zip(ids, arts, tips):
            art = wx.ArtProvider.GetBitmap(art_id, wx.ART_TOOLBAR)
            self.tb.AddSimpleTool(_id, art, tip)

        self.tb.Realize()


    def on_save(self, event=None):
        """
        Saves file if filename is set, otherwise calls 'save as'.
        """
        if not self.util.filename:  # if no wtbd file is active, prompt for one
            self.on_save_as()
        else:
            self.util.save_file()
            self.util.saved = True


    def on_open(self, event=None):
        """
        Opens a file, sets Utility's temp. file to the chosen file, prompts for
        an unsaved file and calls do_open().
        """
        dlg = wx.FileDialog(self, "Open file...", os.getcwd(),
                            style=wx.OPEN, wildcard = self.util.wildcard)

        if dlg.ShowModal() == wx.ID_OK:
            name = dlg.GetPath()

            if name.endswith("wtbd"):

                if self.util.saved:
                    self.do_open(name)
                else:
                    msg = ("You have not saved your file. Are you sure you " +
                           "want to open a new file?")
                    dialog = wx.MessageDialog(self, msg, style=wx.YES_NO |
                                                           wx.ICON_QUESTION)

                    if dialog.ShowModal() == wx.ID_YES:
                        self.do_open(name)
            else:
                self.do_open(name)
        else:
            dlg.Destroy()


    def do_open(self, name):
        """
        Updates te appropriate variables in the utility file class and loads
        the file.
        """
        if name.endswith("wtbd"):
            self.util.filename = name

        self.util.temp_file = name
        self.util.load_file()


    def on_save_as(self, event=None):
        """
        Prompts for the filename and location to save to.
        """
        dlg = wx.FileDialog(self, "Save Whyteboard As...", os.getcwd(),
                style=wx.SAVE | wx.OVERWRITE_PROMPT,
                wildcard = "Whyteboard file (*.wtbd)|*.wtbd")
        if dlg.ShowModal() == wx.ID_OK:
            filename = dlg.GetPath()
            if not os.path.splitext(filename)[1]:  # no file extension
                filename += '.wtbd'

            # only store whyteboard files, not an image as the current file
            if filename.endswith(".wtbd"):
                self.util.filename = filename
                self.on_save()
        dlg.Destroy()


    def on_export(self, event):
        """
        Exports the current tab as an image.
        """
        wc =  "PNG (*.png)|*.png|JPEG (*.jpg, *.jpeg)|*.jpeg;*.jpg|TIFF (*.tiff)|BMP (*.bmp)|*.bmp"
        dlg = wx.FileDialog(self, "Export data to...", os.getcwd(),
                style=wx.SAVE | wx.OVERWRITE_PROMPT, wildcard=wc)
        if dlg.ShowModal() == wx.ID_OK:
            filename = dlg.GetPath()
            _name = os.path.splitext(filename)[1].replace(".", "")

            types = {0: "png", 1: "jpg", 2: "tiff", 3: "bmp"}

            if not os.path.splitext(filename)[1]:
                _name = types[dlg.GetFilterIndex()]
                filename += "." + _name
            if not _name in self.util.types[2:]:
                wx.MessageBox("Invalid filetype to export as.", "Invalid type")
            else:
                self.board.export(filename)
        dlg.Destroy()


    def on_new_tab(self, event=None):
        """
        Opens a new tab and selects it
        """
        wb = Whyteboard(self.tabs)
        self.tab_count += 1
        self.tabs.AddPage(wb, "Untitled "+ str(self.tab_count))

        self.tabs.SetSelection(self.tab_count - 1 )  # fires on_change_tab
        self.thumbs.new_thumb()


    def on_change_tab(self, event=None):
        """
        Sets the GUI's board attribute to be the selected Whyteboard.
        """
        self.board = self.tabs.GetCurrentPage()
        self.control.change_tool()
        self.update_menus()  # update redo/undo


    def on_close_tab(self, event=None):
        """
        Closes the current tab (if there are any to close).
        """
        if self.tab_count:
            self.thumbs.remove(self.tabs.GetSelection())
            self.tabs.RemovePage(self.tabs.GetSelection())
            self.tab_count -= 1

    def on_thumbs(self, event):
        """
        Toggles the thumnnail panel on and off.
        """
        if self.box.IsShown(self.thumbs):
            self.box.Remove(self.thumbs)
            self.thumbs.Hide()
            self.box.Layout()
        else:
            self.box.Add(self.thumbs, 0, wx.EXPAND)
            self.thumbs.Show()
            self.box.Layout()


    def convert_dialog(self, cmd):
        """
        Called when the convert process begins, executes the process call and
        shows the convert dialog
        """
        self.process = wx.Process(self)
        wx.Execute(cmd, wx.EXEC_ASYNC, self.process)

        self.dlg = ConvertProgress(self)
        self.dlg.ShowModal()


    def on_end_process(self, event):
        """
        Destroy the progress Gauge/process after the convert process returns
        """
        self.process.Destroy()
        self.dlg.Destroy()
        del self.dlg
        del self.process


    def on_exit(self, event=None):
        """
        Clean up any tmp files from PDF/PS conversion.

        **NOTE**
        Temporarily keeping temp. files to make loading .wtbd files faster
        """
        if not self.util.saved:
            msg = "You have not saved your file. Are you sure you want to quit?"
            dialog = wx.MessageDialog(self, msg, style=wx.YES_NO |
                                                       wx.ICON_QUESTION)

            if dialog.ShowModal() == wx.ID_YES:
                #self.util.cleanup()
                self.Destroy()
        else:
            self.Destroy()


    def on_undo(self, event=None):
        """
        Calls undo on the active tab and updates the menus
        """
        self.board.undo()
        self.update_menus()


    def on_redo(self, event=None):
        """
        Calls redo on the active tab and updates the menus
        """
        self.board.redo()
        self.update_menus()


    def update_menus(self):
        if not self.board._redo:
            redo = False
        else:
            redo = True

        if self.board.shapes:
            undo = True
        else:
            undo = False

        self.tb.EnableTool(wx.ID_UNDO, undo)
        self.menuBar.Enable(wx.ID_UNDO, undo)
        self.tb.EnableTool(wx.ID_REDO, redo)
        self.menuBar.Enable(wx.ID_REDO, redo)



    def on_clear(self, event=None):
        """
        Clears all drawings on the current tab, except images.
        """
        new_shapes = copy(self.board.shapes)

        for x in self.board.shapes:
            if not isinstance(x, Image):
                new_shapes.remove(x)

        self.board.shapes = new_shapes
        self.board.redraw_all()


    def on_clear_all(self, event=None):
        """
        Clears all items from the current tab
        """
        self.board.clear()


    def on_clear_tabs(self, event=None):
        """
        Clears all drawings, except images on all tabs.
        """
        for tab in range(self.tab_count):
            wb = self.tabs.GetPage(tab)
            new_shapes = copy(wb.shapes)

            for x in wb.shapes:
                if not isinstance(x, Image):
                    new_shapes.remove(x)

            wb.shapes = new_shapes
            wb.redraw_all()


    def on_clear_all_tabs(self, event=None):
        """
        Clears all items from the current tab
        """
        for x in range(self.tab_count):
            self.tabs.GetPage(x).clear()


    def on_about(self, event=None):
        dlg = About(self)
        dlg.ShowModal()
        dlg.Destroy()

    def on_history(self, event=None):
        dlg = History(self)
        dlg.ShowModal()
        dlg.Destroy()


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
        self.preview = Preview(self.gui)

        self.tools  = {}
        sizer = wx.GridSizer(cols=1, hgap=1, vgap=2)

        # Get list of class names as strings for each drawable tool
        items = [str(i.__name__) for i in gui.util.items]

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
        box.Add(self.colour, 0, wx.EXPAND | wx.ALL, spacing)
        box.Add(self.thickness, 0, wx.EXPAND | wx.ALL, spacing)
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


class Preview(wx.Window):
    """
    Shows a sample of what the current tool's drawing will look like.
    """
    def __init__(self, gui):
        """
        Stores gui reference to access utility colour/thickness attributes.
        """
        wx.Window.__init__(self, gui, style=wx.SUNKEN_BORDER)
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
        dc = wx.PaintDC(self)
        #pen = wx.Pen(self.gui.util.colour, self.gui.util.thickness)
        dc.SetPen(self.gui.board.shape.pen)
        dc.SetBrush(self.gui.board.shape.brush)
        width, height = self.GetClientSize()
        self.gui.board.shape.preview(dc, width, height)



#----------------------------------------------------------------------


class Thumbs(scrolled.ScrolledPanel):
    """
    Thumbnails of all tabs' drawings.
    """
    def __init__(self, gui, height):
        scrolled.ScrolledPanel.__init__(self, gui, size=(170, 150), style=wx.VSCROLL | wx.RAISED_BORDER)# | wx.ALWAYS_SHOW_SB)
        self.virtual = self.GetBestVirtualSize()

        self.gui = gui
        self.thumbs  = []
        self.text = []
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.new_thumb()  # inital thumb

        box = wx.BoxSizer(wx.VERTICAL)
        box.Add(self.sizer)
        self.SetSizer(box)
        self.SetAutoLayout(True)
        box.Fit(self)

        self.SetScrollRate(0, 110)

        self.SetInitialSize(self.virtual)
        self.sizer.SetSizeHints(self.GetParent())
        self.SetupScrolling(False, True)



    def new_thumb(self, _id=0):
        """
        Creates a new thumbnail button and manages its ID, along with a label.
        """
        if _id:
            bmp = self.redraw(_id)
        else:
            if len(self.thumbs):
                _id = len(self.thumbs)
            img = wx.ImageFromBitmap(wx.EmptyBitmap(150, 150))
            img.ConvertColourToAlpha(255, 255, 255)
            bmp = wx.BitmapFromImage(img)

        text = wx.StaticText(self, label="Tab " + str(_id + 1))
        btn = ThumbButton(self, _id, bmp)
        btn.SetBitmapHover(bmp)
        btn.SetBitmapSelected(bmp)
        self.text.insert(_id, text)
        self.thumbs.insert(_id, btn)
        btn.Bind(wx.EVT_BUTTON, self.on_press)

        self.sizer.Add(btn, flag=wx.EXPAND)
        self.sizer.Add(text, flag=wx.CENTER)
        self.sizer.Layout()

        size = self.thumbs[_id].GetSize()
        self.update_scrollbar((self.virtual[0], size[1]))


    def remove(self, _id):
        """
        Removes a thumbnail/label from the sizer and the managed widgets list.
        """
        size = self.thumbs[_id].GetSize()
        self.sizer.Remove(self.thumbs[_id])
        self.sizer.Remove(self.text[_id])
        self.thumbs[_id].Hide()  # broken without this
        self.text[_id].Hide()

        self.sizer.Layout()
        del self.thumbs[_id]
        self.update_scrollbar((self.virtual[0], -size[1]))

        # now ensure all thumbnail classes are pointing to the right tab
        for x in range(0, len(self.thumbs)):
            self.thumbs[x].thumb_id = x
            self.text[x].SetLabel("Tab " + str(x + 1))

    def on_press(self, event):
        """
        Changes the tab to the selected button.
        """
        btn = event.GetEventObject()
        self.gui.tabs.SetSelection(btn.thumb_id)


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
        self.thumbs[_id].SetBitmapLabel(bmp)
        self.thumbs[_id].SetBitmapHover(bmp)
        self.thumbs[_id].SetBitmapSelected(bmp)


    def update_all(self):
        """
        Updates all thumbnails (i.e. upon loading a Whyteboard file).
        """
        #thumbs = copy(self.thumbs)
        for x in range(0, len(self.thumbs)):
            self.update(x)


    def update_scrollbar(self, new_size):
        """
        Updates the Thumbnail's scrollbars when a thumbnail is added/removed.
        """
        width, height = new_size
        y =  self.virtual[1] + height
        self.virtual = (width, y)
        self.SetVirtualSize(self.virtual)


#----------------------------------------------------------------------

class ThumbButton(wx.BitmapButton):
    """
    This class has an extra attribute, storing its related tab ID so that when
    the button is pressed, it can switch to the proper tab.
    """
    def __init__(self, parent, _id, bitmap):
        wx.BitmapButton.__init__(self, parent, bitmap=bitmap, size=(150, 150))
        self.thumb_id  = _id
#----------------------------------------------------------------------


class WhyteboardApp(wx.App):
    def OnInit(self):
        frame = GUI(None)
        frame.Show(True)
        self.SetAppName("whyteboard")  # used to identify app in $HOME/
        return True

#----------------------------------------------------------------------


if __name__ == '__main__':
    app = WhyteboardApp(True)
    app.MainLoop()
