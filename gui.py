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
from copy import copy
from tools import Image
from whyteboard import Whyteboard
from utility import Utility
from dialogs import About, History, ConvertProgress


#----------------------------------------------------------------------

ID_HISTORY = wx.NewId()
ID_CLEAR_ALL = wx.NewId()      # remove all from current tab
ID_CLEAR_TABS = wx.NewId()     # remove all drawings from all tabs, keep images
ID_CLEAR_ALL_TABS = wx.NewId() # remove all from all tabs

class GUI(wx.Frame):
    """
    This class contains a Whyteboard panel, a ControlPanel and manages
    their layout with a wx.BoxSizer.  A menu, toolbar and associated event
    handlers call the appropriate functions of other classes.
    """
    title = "Whyteboard"
    version = "0.33"

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

        self.tabs = wx.Notebook(self)
        self.board = Whyteboard(self.tabs)  # the active whiteboard tab
        self.tabs.AddPage(self.board, "Untitled 1")
        self.control = ControlPanel(self)

        self.do_bindings()
        self.update_menus()
        box = wx.BoxSizer(wx.HORIZONTAL)  # position windows side-by-side
        box.Add(self.control, 0, wx.EXPAND)
        box.Add(self.tabs, 2, wx.EXPAND)
        self.SetSizer(box)
        self.Maximize(True)


    def make_menu(self):
        """
        Creates the menu...pretty damn messy, may give this a cleanup like the
        do_bindings/make_toolbar
        """
        _file = wx.Menu()
        history = wx.Menu()
        image = wx.Menu()
        _help = wx.Menu()
        self.menuBar = wx.MenuBar()

        _file.Append(wx.ID_NEW, "New &Tab\tCtrl-T", "Open a new tab")
        _file.Append(wx.ID_OPEN, "&Open\tCtrl-O", "Load a Whyteboard save file, an image or convert a PDF/PS document")
        _file.Append(wx.ID_SAVE, "&Save\tCtrl-S", "Save the Whyteboard data")
        _file.Append(wx.ID_SAVEAS, "Save &As...\tCtrl-Shift-S", "Save the Whyteboard data in a new file")
        _file.AppendSeparator()
        _file.Append(wx.ID_CLOSE, "&Close Tab\tCtrl-W", "Close current tab")
        _file.Append(wx.ID_EXIT, "E&xit\tAlt-F4", "Terminate Whyteboard")

        history.Append(wx.ID_UNDO, "&Undo\tCtrl-Z", "Undo the last operation")
        history.Append(wx.ID_REDO, "&Redo\tCtrl-Y", "Redo the last undone operation")
        history.AppendSeparator()
        history.Append(ID_HISTORY, "&History Viewer\tCtrl-H", "View and replay your drawing history")

        image.Append(wx.ID_CLEAR, "&Clear Tab's Drawings", "Clear drawings on the current tab (keep images)")
        image.Append(ID_CLEAR_ALL, "Clear &Tab", "Clear the current tab")
        image.AppendSeparator()
        image.Append(ID_CLEAR_TABS, "Clear All Tabs' &Drawings", "Clear all tabs of drawings (keep images)")
        image.Append(ID_CLEAR_ALL_TABS, "Clear &All Tabs", "Clear all open tabs")

        _help.Append(wx.ID_ABOUT, "&About\tF1", "View information about the Whyteboard application")
        self.menuBar.Append(_file, "&File")
        self.menuBar.Append(history, "&History")
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

        functs = ["new_tab", "close_tab", "open", "save", "save_as", "undo",
                  "redo", "history", "clear", "clear_all", "clear_tabs",
                  "clear_all_tabs", "about", "exit"]

        IDs = [wx.ID_NEW, wx.ID_CLOSE, wx.ID_OPEN, wx.ID_SAVE, wx.ID_SAVEAS,
               wx.ID_UNDO, wx.ID_REDO, ID_HISTORY, wx.ID_CLEAR, ID_CLEAR_ALL,
               ID_CLEAR_TABS, ID_CLEAR_ALL_TABS, wx.ID_ABOUT, wx.ID_EXIT]

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
                filename = filename + '.wtbd'

            # only store whyteboard files, not an image as the current file
            if filename.endswith(".wtbd"):
                self.util.filename = filename
                self.on_save()

            self.SetTitle(os.path.split(filename)[1] + ' - ' +  self.title)
        dlg.Destroy()


    def on_new_tab(self, event=None):
        """
        Opens a new tab and selects it
        """
        wb = Whyteboard(self.tabs)
        self.tabs.AddPage(wb, "Untitled "+ str(self.tab_count + 1) )
        self.tab_count += 1
        self.tabs.SetSelection(self.tab_count - 1 )  # fires on_change_tab


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
        if self.tab_count is not 0:
            self.tabs.RemovePage( self.tabs.GetSelection() )
            self.tab_count -= 1


    def convert_dialog(self, cmd):
        """
        Called when the convert process begins, executes the process call and
        shows the convert dialog
        """
        self.process = wx.Process(self)
        wx.Execute(cmd, wx.EXEC_ASYNC, self.process)

        self.dlg = ConvertProgress(self)
        self.dlg.ShowModal()


    def on_end_process(self, event=None):
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


        choices = ''.join(str(i) + " " for i in range(1, 26) ).split()

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
        pen = wx.Pen(self.gui.util.colour, self.gui.util.thickness)
        dc.SetPen(pen)
        width, height = self.GetClientSize()
        dc.DrawLine(10, height / 2, width - 10, height / 2)


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
