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
import wx.lib.newevent
import os
import sys

import icon
from whyteboard import Whyteboard
from utility import Utility, FileDropTarget
from dialogs import About, History, ProgressDialog, Resize
from panels import ControlPanel, SidePanel


#----------------------------------------------------------------------

ID_EXPORT = wx.NewId()
ID_THUMBS = wx.NewId()
ID_HISTORY = wx.NewId()
ID_RESIZE = wx.NewId()
ID_PREV = wx.NewId()
ID_NEXT = wx.NewId()
ID_CLEAR_ALL = wx.NewId()      # remove all from current tab
ID_CLEAR_TABS = wx.NewId()     # remove all drawings from all tabs, keep images
ID_CLEAR_ALL_TABS = wx.NewId() # remove all from all tabs
ID_PDF = wx.NewId()
ID_PS = wx.NewId()
ID_IMG = wx.NewId()


class GUI(wx.Frame):
    """
    This class contains a Whyteboard frame, a ControlPanel and a Thumbnail Panel
    and manages their layout with a wx.BoxSizer.  A menu, toolbar and associated
    event handlers call the appropriate functions of other classes.
    """
    version = "0.36"
    title = "Whyteboard %s" % version
    LoadEvent, LOAD_DONE_EVENT = wx.lib.newevent.NewEvent()

    def __init__(self, parent):
        """
        Initialise utility, status/menu/tool bar, tabs, ctrl panel + bindings.
        """
        wx.Frame.__init__(self, parent, title="Untitled - " + self.title)
        ico = icon.whyteboard.getIcon()
        self.SetIcon(ico)

        self.util = Utility(self)
        self.file_drop = FileDropTarget(self)
        self.SetDropTarget(self.file_drop)
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
        self.tabs.AddPage(self.board, "Sheet 1")

        self.panel = SidePanel(self)
        self.thumbs = self.panel.thumbs
        self.notes = self.panel.notes

        self.do_bindings()
        self.update_menus()
        self.box = wx.BoxSizer(wx.HORIZONTAL)  # position windows side-by-side
        self.box.Add(self.control, 0, wx.EXPAND)
        self.box.Add(self.tabs, 2, wx.EXPAND)
        self.box.Add(self.panel, 0, wx.EXPAND)
        self.SetSizer(self.box)
        self.SetSizeWH(800, 600)
        self.Maximize(True)


    def make_menu(self):
        """
        Creates the menu...pretty damn messy, may give this a cleanup like the
        do_bindings/make_toolbar
        """
        _file = wx.Menu()
        edit = wx.Menu()
        view = wx.Menu()
        sheets = wx.Menu()
        _help = wx.Menu()
        self.menu = wx.MenuBar()
        imp = wx.Menu()
        imp.Append(ID_PDF, 'PDF')
        imp.Append(ID_PS, 'PostScript')
        imp.Append(ID_IMG, 'Image')

        _file.Append(wx.ID_NEW, "&New Sheet\tCtrl+T", "Add a new sheet")
        _file.Append(wx.ID_OPEN, "&Open\tCtrl+O", "Load a Whyteboard save file, an image or convert a PDF/PS document")
        _file.Append(wx.ID_CLOSE, "&Remove Sheet\tCtrl+W", "Close the current sheet")
        _file.AppendSeparator()
        _file.Append(wx.ID_SAVE, "&Save\tCtrl+S", "Save the Whyteboard data")
        _file.Append(wx.ID_SAVEAS, "Save &As...\tCtrl+Shift+S", "Save the Whyteboard data in a new file")
        _file.AppendMenu(+1, '&Import File', imp)
        _file.Append(ID_EXPORT, "&Export Sheet\tCtrl+E", "Export the current sheet to an image file")
        _file.AppendSeparator()
        _file.Append(wx.ID_EXIT, "&Quit\tAlt+F4", "Quit Whyteboard")

        edit.Append(wx.ID_UNDO, "&Undo\tCtrl+Z", "Undo the last operation")
        edit.Append(wx.ID_REDO, "&Redo\tCtrl+Y", "Redo the last undone operation")
        edit.AppendSeparator()
        #edit.Append(ID_RESIZE, "Re&size Canvas\tCtrl+R", "Change the canvas' size")

        edit.Append(ID_HISTORY, "&History Viewer\tCtrl+H", "View and replay your drawing history")
        #view.Append(ID_THUMBS, " &Toggle Side Panel\tF9", "Toggle the side panel on or off", kind=wx.ITEM_CHECK)
        #view.Check(ID_THUMBS, True)

        sheets.Append(ID_NEXT, "&Next Sheet\tCtrl+Tab", "Go to the next sheet")
        sheets.Append(ID_PREV, "&Previous Sheet\tCtrl+Shift+Tab", "Go to the previous sheet")
        sheets.AppendSeparator()
        sheets.Append(wx.ID_CLEAR, "&Clear Sheets' Drawings", "Clear drawings on the current sheet (keep images)")
        sheets.Append(ID_CLEAR_ALL, "Clear &Sheet", "Clear the current sheet")
        sheets.AppendSeparator()
        sheets.Append(ID_CLEAR_TABS, "Clear All Sheets' &Drawings", "Clear all sheets' drawings (keep images)")
        sheets.Append(ID_CLEAR_ALL_TABS, "Clear &All Sheets", "Clear all sheets")

        _help.Append(wx.ID_ABOUT, "&About\tF1", "View information about Whyteboard")
        self.menu.Append(_file, "&File")
        self.menu.Append(edit, "&Edit")
        #self.menu.Append(view, "&View")
        self.menu.Append(sheets, "&Sheets")
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
        self.tabs.Bind(wx.EVT_ENTER_WINDOW, self.on_yeh)

        ids = { 'pdf': ID_PDF, 'ps': ID_PS, 'img': ID_IMG }
        [self.Bind(wx.EVT_MENU, lambda evt, text = key: self.on_open(evt, text),
                    id=ids[key]) for key in ids]

        functs = ["new_tab", "close_tab", "open", "save", "save_as", "export",
                  "undo", "redo", "history", "thumbs", "resize", "prev", "next",
                  "clear", "clear_all", "clear_sheets", "clear_all_sheets",
                  "about", "exit"]

        IDs = [wx.ID_NEW, wx.ID_CLOSE, wx.ID_OPEN, wx.ID_SAVE, wx.ID_SAVEAS,
               ID_EXPORT, wx.ID_UNDO, wx.ID_REDO, ID_HISTORY, ID_THUMBS,
               ID_RESIZE, ID_PREV, ID_NEXT, wx.ID_CLEAR, ID_CLEAR_ALL,
               ID_CLEAR_TABS, ID_CLEAR_ALL_TABS, wx.ID_ABOUT, wx.ID_EXIT]

        for name, _id in zip(functs, IDs):
            method = getattr(self, "on_"+ name)  # self.on_*
            self.Bind(wx.EVT_MENU, method, id=_id )
    def on_yeh(self, e):
        print 'hgfhn'

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


    def on_open(self, event=None, text=None):
        """
        Opens a file, sets Utility's temp. file to the chosen file, prompts for
        an unsaved file and calls do_open().
        """
        wc = self.util.wildcard
        if text == "img":
            wc = wc[ wc.find("I") : wc.find("P") ]  # image to page
        elif text:
            wc = wc[ wc.find("P"):]  # page descriptions

        dlg = wx.FileDialog(self, "Open file...", style=wx.OPEN, wildcard=wc)

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
        Exports the current sheet as an image.
        """
        wc =  ("PNG (*.png)|*.png|JPEG (*.jpg, *.jpeg)|*.jpeg;*.jpg|"+
               "BMP (*.bmp)|*.bmp|TIFF (*.tiff)|*.tiff")
        dlg = wx.FileDialog(self, "Export data to...", style=wx.SAVE |
                             wx.OVERWRITE_PROMPT, wildcard=wc)
        if dlg.ShowModal() == wx.ID_OK:
            filename = dlg.GetPath()
            _name = os.path.splitext(filename)[1].replace(".", "")

            types = {0: "png", 1: "jpg", 2: "bmp", 3: "tiff"}

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
        self.thumbs.new_thumb()
        self.notes.add_tab()
        self.tab_count += 1
        self.tabs.AddPage(wb, "Sheet "+ str(self.tab_count))
        self.current_tab = self.tab_count - 1

        self.tabs.SetSelection(self.current_tab)  # fires on_change_tab


    def on_change_tab(self, event=None):
        """
        Sets the GUI's board attribute to be the selected Whyteboard.
        """
        self.board = self.tabs.GetCurrentPage()
        self.current_tab = self.tabs.GetSelection()
        #self.thumbs.Scroll(-1, self.current_tab)
        self.update_menus()  # update redo/undo
        self.control.change_tool()

        if self.notes.tabs:
            tree_id = self.notes.tabs[self.current_tab]
            self.notes.tree.SelectItem(tree_id, True)


    def on_close_tab(self, event=None):
        """
        Closes the current tab (if there are any to close).
        """
        if self.tab_count:
            self.notes.remove(self.current_tab)
            self.thumbs.remove(self.current_tab)
            self.tab_count -= 1
            self.tabs.RemovePage(self.current_tab)

            for x in range(self.current_tab, self.tab_count):
                self.tabs.SetPageText(x, "Sheet " + str(x + 1))


    def on_thumbs(self, event):
        """
        Toggles the thumnnail panel on and off.
        """
        if self.box.IsShown(self.panel):
            self.panel.Hide()
        else:
            self.panel.Show()
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
        """
        Enables/disables the undo/redo/next/prev button as appropriate.
        """
        undo = False
        redo = False
        next = False
        prev = False

        if self.board.redo_list:
            redo = True
        if self.board.undo_list:
            undo = True
        if self.current_tab > 0:
            prev = True
        if self.tab_count > 1 and (self.current_tab + 1 < self.tab_count):
            next = True

        self.tb.EnableTool(wx.ID_UNDO, undo)
        self.menu.Enable(wx.ID_UNDO, undo)
        self.tb.EnableTool(wx.ID_REDO, redo)
        self.menu.Enable(wx.ID_REDO, redo)
        self.menu.Enable(ID_PREV, prev)
        self.menu.Enable(ID_NEXT, next)

    def on_prev(self, event=None):
        """
        Changes to the previous sheet
        """
        self.tabs.SetSelection(self.current_tab - 1)

    def on_next(self, event=None):
        """
        Changes to the next sheet
        """
        self.tabs.SetSelection(self.current_tab + 1)

    def on_clear(self, event=None):
        """
        Clears *** current sheet's *** drawings, except images.
        """
        self.board.clear(keep_images=True)
        self.update_menus()


    def on_clear_all(self, event=None):
        """
        Clears *** current sheet ***
        """
        self.board.clear()
        self.update_menus()


    def on_clear_sheets(self, event=None):
        """
        Clears *** all tabs' *** drawings, except images.
        """
        for tab in range(self.tab_count):
            self.tabs.GetPage(tab).clear(keep_images=True)
        self.update_menus()


    def on_clear_all_sheets(self, event=None):
        """
        Clears *** all tabs ***
        """
        for tab in range(self.tab_count):
            self.tabs.GetPage(tab).clear()
        self.update_menus()

    def on_resize(self, event=None):
        dlg = Resize(self)
        dlg.ShowModal()
        dlg.Destroy()

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
        self.SetAppName("whyteboard")  # used to identify app in $HOME/
        frame = GUI(None)
        frame.Show(True)
        try:
            _file = sys.argv[1]
            if _file:
                if os.path.exists(_file):
                    frame.do_open(sys.argv[1])
        except IndexError:
            pass
        return True

#----------------------------------------------------------------------

def main():
    app = WhyteboardApp(True)
    app.MainLoop()

if __name__ == '__main__':
    main()
