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
This module implements the Whteboard application.  It takes a Whyteboard class
and wraps it in a GUI with a menu/toolbar/statusbar; can save and load drawings,
clear the workspace, undo, redo, a simple history "replayer", allowing you to
have a replay of what you have drawn played back to you.

Also on the GUI is a panel for setting color and line thickness, with an
indicator that shows an example of the drawing-to-be
"""

import wx
import  wx.lib.newevent

import os
import sys

from copy import copy

from tools import Image
from whyteboard import Whyteboard
from utility import Utility
from dialogs import About, History, ProgressDialog
from panels import ControlPanel, SidePanel


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
    version = "0.35.3"
    LoadEvent, LOAD_DONE_EVENT = wx.lib.newevent.NewEvent()

    def __init__(self, parent):
        """
        Initialise utility, status/menu/tool bar, tabs, ctrl panel + bindings.
        """
        wx.Frame.__init__(self, parent, title="Untitled - " +
           self.title, style=wx.DEFAULT_FRAME_STYLE | wx.FULL_REPAINT_ON_RESIZE)

        self.util = Utility(self)
        self.CreateStatusBar()

        self.tb = None
        self.menu = None
        self.process = None
        self.dialog = None

        self.make_toolbar()
        self.make_menu()
        self.tab_count = 1  # instead of typing self.tabs.GetPageCount()
        self.current_tab = 0
        self.control = ControlPanel(self)
        self.tabs = wx.Notebook(self)
        self.board = Whyteboard(self.tabs)  # the active whiteboard tab
        self.tabs.AddPage(self.board, "Tab 1")

        self.panel = SidePanel(self)
        self.thumbs = self.panel.thumbs
        self.notes = self.panel.notes
        #self.on_refresh()  # force first thumb to update

        self.do_bindings()
        self.update_menus()
        self.box = wx.BoxSizer(wx.HORIZONTAL)  # position windows side-by-side
        self.box.Add(self.control, 0, wx.EXPAND)
        self.box.Add(self.tabs, 2, wx.EXPAND)
        self.box.Add(self.panel, 0, wx.EXPAND)
        self.SetSizer(self.box)
        self.SetSizeWH(800, 600)
        self.Maximize(True)

        try:
            _file = sys.argv[1]
            if _file:
                if os.path.exists(_file):
                    self.do_open(sys.argv[1])
        except IndexError:
            pass


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
        self.menu = wx.MenuBar()

        _file.Append(wx.ID_NEW, "New &Tab\tCtrl-T", "Open a new tab")
        _file.Append(wx.ID_OPEN, "&Open\tCtrl-O", "Load a Whyteboard save file, an image or convert a PDF/PS document")
        _file.Append(wx.ID_SAVE, "&Save\tCtrl-S", "Save the Whyteboard data")
        _file.Append(wx.ID_SAVEAS, "Save &As...\tCtrl-Shift-S", "Save the Whyteboard data in a new file")
        _file.Append(ID_EXPORT, "&Export\tCtrl-E", "Export the current tab's contents to an image")
        _file.AppendSeparator()
        _file.Append(wx.ID_CLOSE, "&Close Tab\tCtrl-W", "Close current tab")
        _file.Append(wx.ID_EXIT, "E&xit\tAlt-F4", "Terminate Whyteboard")

        history.Append(wx.ID_UNDO, "&Undo\tCtrl-Z", "Undo the last operation")
        history.Append(wx.ID_REDO, "&Redo\tCtrl-Y", "Redo the last undone operation")
        history.AppendSeparator()
        history.Append(ID_HISTORY, "&History Viewer\tCtrl-H", "View and replay your drawing history")

        view.Append(ID_THUMBS, " &Toggle Side Panel\tF9", "Toggle the side panel on or off", kind=wx.ITEM_CHECK)
        view.Check(ID_THUMBS, True)

        image.Append(wx.ID_CLEAR, "&Clear Tab's Drawings", "Clear drawings on the current tab (keep images)")
        image.Append(ID_CLEAR_ALL, "Clear &Tab", "Clear the current tab")
        image.AppendSeparator()
        image.Append(ID_CLEAR_TABS, "Clear All Tabs' &Drawings", "Clear all tabs of drawings (keep images)")
        image.Append(ID_CLEAR_ALL_TABS, "Clear &All Tabs", "Clear all open tabs")

        _help.Append(wx.ID_ABOUT, "&About\tF1", "View information about Whyteboard")
        self.menu.Append(_file, "&File")
        self.menu.Append(history, "&History")
        self.menu.Append(view, "&View")
        self.menu.Append(image, "&Image")
        self.menu.Append(_help, "&Help")
        self.SetMenuBar(self.menu)


    def do_bindings(self):
        """
        Performs event binding.
        """
        self.Bind(wx.EVT_CLOSE, self.on_exit)
        self.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.on_change_tab, self.tabs)
        self.Bind(wx.EVT_END_PROCESS, self.on_end_process)  # converted
        self.Bind(self.LOAD_DONE_EVENT, self.on_done_load)


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

        x = 0
        for _id, art_id, tip in zip(ids, arts, tips):
            if x == 3:
                self.tb.AddSeparator()
            art = wx.ArtProvider.GetBitmap(art_id, wx.ART_TOOLBAR)
            self.tb.AddSimpleTool(_id, art, tip)
            x += 1

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
                    msg = ("You have not saved your file, and will lose all " +
                           "unsaved data. Are you sure you want to open this " +
                           "file?")
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
        Updates the appropriate variables in the utility file class and loads
        the selected file.
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
        wc =  "PNG (*.png)|*.png|JPEG (*.jpg, *.jpeg)|*.jpeg;*.jpg|GIF (*.gif)|*.gif|BMP (*.bmp)|*.bmp|TIFF (*.tiff)|*.tiff"
        dlg = wx.FileDialog(self, "Export data to...", os.getcwd(),
                style=wx.SAVE | wx.OVERWRITE_PROMPT, wildcard=wc)
        if dlg.ShowModal() == wx.ID_OK:
            filename = dlg.GetPath()
            _name = os.path.splitext(filename)[1].replace(".", "")

            types = {0: "png", 1: "jpg", 2: "gif", 3: "bmp", 4: "tiff"}

            if not os.path.splitext(filename)[1]:
                _name = types[dlg.GetFilterIndex()]
                filename += "." + _name
            if not _name in self.util.types[2:]:
                wx.MessageBox("Invalid filetype to export as.", "Invalid type")
            else:
                self.util.export(filename)
        dlg.Destroy()


    def on_new_tab(self, event=None):
        """
        Opens a new tab and selects it
        """
        wb = Whyteboard(self.tabs)
        self.tab_count += 1
        self.tabs.AddPage(wb, "Tab "+ str(self.tab_count))
        self.current_tab = self.tab_count - 1

        self.tabs.SetSelection(self.current_tab)  # fires on_change_tab
        self.thumbs.new_thumb()
        self.notes.add_tab()


    def on_change_tab(self, event=None):
        """
        Sets the GUI's board attribute to be the selected Whyteboard.
        """
        self.board = self.tabs.GetCurrentPage()
        self.current_tab = self.tabs.GetSelection()
        self.update_menus()  # update redo/undo
        self.control.change_tool()


    def on_close_tab(self, event=None):
        """
        Closes the current tab (if there are any to close).
        """
        if self.tab_count:
            self.notes.remove(self.current_tab)
            self.thumbs.remove(self.current_tab)
            self.tabs.RemovePage(self.current_tab)
            self.tab_count -= 1

            for x in range(self.current_tab, self.tab_count):
                self.tabs.SetPageText(x, "Tab " + str(x + 1))


    def on_thumbs(self, event):
        """
        Toggles the thumnnail panel on and off.
        """
        if self.box.IsShown(self.panel):
            self.panel.Hide()
        else:
            self.panel.Show()
            self.on_refresh()
        self.box.Layout()


    def on_refresh(self):
        """
        Refresh thumbnails.
        """
        self.thumbs.update_all()


    def convert_dialog(self, cmd):
        """
        Called when the convert process begins, executes the process call and
        shows the convert dialog
        """
        self.process = wx.Process(self)
        wx.Execute(cmd, wx.EXEC_ASYNC, self.process)

        self.dialog = ProgressDialog(self, "Converting...")
        self.dialog.ShowModal()


    def on_end_process(self, event):
        """
        Destroy the progress Gauge/process after the convert process returns
        """
        self.process.Destroy()
        self.dialog.Destroy()
        del self.process


    def on_done_load(self, event=None):
        """
        Refreshes the thumbnails and destroys the progress dialog after WB file
        load.
        """
        self.dialog.SetTitle("Updating thumbs")
        wx.MilliSleep(50)
        wx.SafeYield()
        self.on_refresh()  # force thumbnails

        self.dialog.Destroy()


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
        self.menu.Enable(wx.ID_UNDO, undo)
        self.tb.EnableTool(wx.ID_REDO, redo)
        self.menu.Enable(wx.ID_REDO, redo)



    def on_clear(self, event=None):
        """
        Clears all drawings on the current tab, except images.
        """
        new_shapes = copy(self.board.shapes)

        for x in self.board.shapes:
            if not isinstance(x, Image):
                new_shapes.remove(x)

        self.board.shapes = new_shapes
        self.board.redraw_all(True)
        self.update_menus()

    def on_clear_all(self, event=None):
        """
        Clears all items from the current tab
        """
        self.board.clear()
        self.update_menus()


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
            wb.redraw_all(True)
            self.update_menus()


    def on_clear_all_tabs(self, event=None):
        """
        Clears all items from the current tab
        """
        for x in range(self.tab_count):
            self.tabs.GetPage(x).clear()
        self.update_menus()


    def on_about(self, event=None):
        dlg = About(self)
        dlg.ShowModal()
        dlg.Destroy()

    def on_history(self, event=None):
        dlg = History(self)
        dlg.ShowModal()
        dlg.Destroy()


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
