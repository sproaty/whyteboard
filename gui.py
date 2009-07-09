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
from tools import Image, Note
from utility import Utility, FileDropTarget
from dialogs import  History, ProgressDialog, Resize, UpdateDialog
from panels import ControlPanel, SidePanel, SheetsPopup


#----------------------------------------------------------------------

ID_NEW = wx.NewId()               # new window
ID_PASTE_NEW = wx.NewId()         # paste as new selection
#ID_EXPORT = wx.NewId()            # export sheet to image file
ID_UNDO_SHEET = wx.NewId()        # undo close sheet
ID_HISTORY = wx.NewId()           # history viewer
ID_RESIZE = wx.NewId()            # resize dialog
ID_PREV = wx.NewId()              # previous sheet
ID_NEXT = wx.NewId()              # next sheet
ID_CLEAR_ALL = wx.NewId()         # remove all from current tab
ID_CLEAR_SHEETS = wx.NewId()      # remove all drawings from all tabs, keep imgs
ID_CLEAR_ALL_SHEETS = wx.NewId()  # remove all from all tabs
ID_FULLSCREEN = wx.NewId()        # toggle fullscreen
ID_PDF = wx.NewId()               # import->PDF
ID_PS = wx.NewId()                # import->PS
ID_IMG = wx.NewId()               # import->Image
ID_EXP_IMG = wx.NewId()           # export->Image
ID_EXP_PDF = wx.NewId()           # export->PDF
ID_UPDATE = wx.NewId()            # update self

class GUI(wx.Frame):
    """
    This class contains a Whyteboard frame, a ControlPanel and a Thumbnail Panel
    and manages their layout with a wx.BoxSizer.  A menu, toolbar and associated
    event handlers call the appropriate functions of other classes.
    """
    version = "0.38.0"
    title = "Whyteboard %s" % version
    LoadEvent, LOAD_DONE_EVENT = wx.lib.newevent.NewEvent()

    def __init__(self, parent):
        """
        Initialise utility, status/menu/tool bar, tabs, ctrl panel + bindings.
        """
        wx.Frame.__init__(self, parent, title="Untitled - " + self.title)
        ico = icon.whyteboard.getIcon()
        self.SetIcon(ico)
        self.SetExtraStyle(wx.WS_EX_PROCESS_UI_UPDATES)
        self.util = Utility(self)
        self.file_drop = FileDropTarget(self)
        self.SetDropTarget(self.file_drop)
        self.CreateStatusBar()
        if self.util.get_clipboard():
            self.can_paste = True
        else:
            self.can_paste = False
        self.tb = None
        self.menu = None
        self.process = None
        self.dialog = None
        self.make_toolbar()
        self.make_menu()
        self.tab_count = 1  # instead of typing self.tabs.GetPageCount()
        self.current_tab = 0
        self.closed_tabs = []  # [shapes - undo - redo - virtual_size] per tab

        self.control = ControlPanel(self)
        self.tabs = wx.Notebook(self)
        self.board = Whyteboard(self.tabs, self)  # the active whiteboard tab
        self.panel = SidePanel(self)
        self.thumbs = self.panel.thumbs
        self.notes = self.panel.notes
        self.tabs.AddPage(self.board, "Sheet 1")
        self.box = wx.BoxSizer(wx.HORIZONTAL)  # position windows side-by-side
        self.box.Add(self.control, 0, wx.EXPAND)
        self.box.Add(self.tabs, 2, wx.EXPAND)
        self.box.Add(self.panel, 0, wx.EXPAND)
        self.SetSizer(self.box)
        self.SetSizeWH(800, 600)
        self.Maximize(True)

        self.count = 4  # used to update menu timings
        wx.UpdateUIEvent.SetUpdateInterval(65)
        wx.UpdateUIEvent.SetMode(wx.UPDATE_UI_PROCESS_SPECIFIED)
        self.do_bindings()
        self.update_panels(True)  # bold first items
        self.UpdateWindowUI()


    def make_menu(self):
        """
        Creates the menu...pretty damn messy, may give this a cleanup like the
        do_bindings/make_toolbar
        """
        self.menu = wx.MenuBar()
        _file = wx.Menu()
        edit = wx.Menu()
        view = wx.Menu()
        sheets = wx.Menu()
        _help = wx.Menu()
        _import = wx.Menu()
        _import.Append(ID_PDF, '&PDF')
        _import.Append(ID_PS, 'Post&Script')
        _import.Append(ID_IMG, '&Image')
        _export = wx.Menu()
        _export.Append(ID_EXP_PDF, '&PDF')
        _export.Append(ID_EXP_IMG, 'Current Sheet as &Image')

        new = wx.MenuItem(_file, ID_NEW, "&New Window\tCtrl-N", "Opens a new Whyteboard instance")
        new.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_NEW, wx.ART_MENU))

        pnew = wx.MenuItem(edit, ID_PASTE_NEW, "Paste to a &New Sheet\tCtrl+Shift-V", "Paste from your clipboard into a new sheet")
        pnew.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_PASTE, wx.ART_MENU))

        undo_sheet = wx.MenuItem(edit, ID_UNDO_SHEET, "Undo Last Closed Sheet\tCtrl+Shift-T", "Undo the last closed sheet")
        undo_sheet.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_UNDO, wx.ART_MENU))

        _file.AppendItem(new)
        _file.Append(wx.ID_NEW, "&New Sheet\tCtrl-T", "Add a new sheet")
        _file.Append(wx.ID_OPEN, "&Open\tCtrl-O", "Load a Whyteboard save file, an image or convert a PDF/PS document")
        _file.Append(wx.ID_CLOSE, "&Remove Sheet\tCtrl+W", "Close the current sheet")
        _file.AppendSeparator()
        _file.Append(wx.ID_SAVE, "&Save\tCtrl+S", "Save the Whyteboard data")
        _file.Append(wx.ID_SAVEAS, "Save &As...\tCtrl+Shift+S", "Save the Whyteboard data in a new file")
        _file.AppendMenu(+1, '&Import File', _import)
        _file.AppendMenu(+1, '&Export File', _export)
        #_file.Append(ID_EXPORT, "&Export Sheet\tCtrl+E", "Export the current sheet to an image file")
        _file.AppendSeparator()
        _file.Append(wx.ID_EXIT, "&Quit\tAlt+F4", "Quit Whyteboard")

        edit.Append(wx.ID_UNDO, "&Undo\tCtrl+Z", "Undo the last operation")
        edit.Append(wx.ID_REDO, "&Redo\tCtrl+Y", "Redo the last undone operation")
        edit.AppendSeparator()
        edit.Append(ID_RESIZE, "Re&size Canvas\tCtrl+R", "Change the canvas' size")
        edit.Append(wx.ID_COPY, "&Copy\tCtrl+C", "Copy a Bitmap Selection region")
        edit.Append(wx.ID_PASTE, "&Paste\tCtrl+V", "Paste an image from your clipboard into Whyteboard")
        edit.AppendItem(pnew)

        view.Append(ID_FULLSCREEN, " &Full Screen\tF11", "View Whyteboard in full-screen mode", kind=wx.ITEM_CHECK)
        view.Append(ID_HISTORY, "&History Viewer\tCtrl+H", "View and replay your drawing history")

        sheets.Append(ID_NEXT, "&Next Sheet\tCtrl+Tab", "Go to the next sheet")
        sheets.Append(ID_PREV, "&Previous Sheet\tCtrl+Shift+Tab", "Go to the previous sheet")
        sheets.AppendItem(undo_sheet)
        sheets.AppendSeparator()
        sheets.Append(wx.ID_CLEAR, "&Clear Sheets' Drawings", "Clear drawings on the current sheet (keep images)")
        sheets.Append(ID_CLEAR_ALL, "Clear &Sheet", "Clear the current sheet")
        sheets.AppendSeparator()
        sheets.Append(ID_CLEAR_SHEETS, "Clear All Sheets' &Drawings", "Clear all sheets' drawings (keep images)")
        sheets.Append(ID_CLEAR_ALL_SHEETS, "Clear &All Sheets", "Clear all sheets")

        _help.Append(wx.ID_HELP, "&Contents\tF1", "View information about Whyteboard")
        _help.AppendSeparator()
        _help.Append(ID_UPDATE, "Check for &Updates\tF12", "Search for updates to Whyteboard")
        _help.Append(wx.ID_ABOUT, "&About", "View information about Whyteboard")
        self.menu.Append(_file, "&File")
        self.menu.Append(edit, "&Edit")
        self.menu.Append(view, "&View")
        self.menu.Append(sheets, "&Sheets")
        self.menu.Append(_help, "&Help")
        self.SetMenuBar(self.menu)
        self.menu.Enable(ID_PASTE_NEW, self.can_paste)
        self.menu.Enable(ID_UNDO_SHEET, False)


    def do_bindings(self):
        """
        Performs event binding.
        """
        self.Bind(wx.EVT_CLOSE, self.on_exit)
        self.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.on_change_tab, self.tabs)
        self.Bind(wx.EVT_END_PROCESS, self.on_end_process)  # converted
        self.Bind(self.LOAD_DONE_EVENT, self.on_done_load)
        self.Bind(wx.EVT_UPDATE_UI, self.update_menus, id=ID_NEXT)
        self.Bind(wx.EVT_UPDATE_UI, self.update_menus, id=ID_PREV)
        self.Bind(wx.EVT_UPDATE_UI, self.update_menus, id=ID_UNDO_SHEET)
        self.tabs.Bind(wx.EVT_RIGHT_UP, self.tab_popup)

        ids = { 'pdf': ID_PDF, 'ps': ID_PS, 'img': ID_IMG }  # file->import
        [self.Bind(wx.EVT_MENU, lambda evt, text = key: self.on_open(evt, text),
                    id=ids[key]) for key in ids]

        functs = ["new_win", "new_tab", "open",  "close_tab", "save", "save_as", "export", "exit", "undo", "redo", "undo_tab", "copy", "paste", "paste_new",
                  "history", "resize", "fullscreen", "prev", "next", "clear", "clear_all",  "clear_sheets", "clear_all_sheets", "help", "update", "about"]

        IDs = [ID_NEW, wx.ID_NEW, wx.ID_OPEN, wx.ID_CLOSE, wx.ID_SAVE, wx.ID_SAVEAS, ID_EXP_IMG, wx.ID_EXIT, wx.ID_UNDO, wx.ID_REDO, ID_UNDO_SHEET,
               wx.ID_COPY, wx.ID_PASTE, ID_PASTE_NEW, ID_HISTORY, ID_RESIZE, ID_FULLSCREEN, ID_PREV, ID_NEXT, wx.ID_CLEAR, ID_CLEAR_ALL,
               ID_CLEAR_SHEETS, ID_CLEAR_ALL_SHEETS, wx.ID_HELP, ID_UPDATE, wx.ID_ABOUT]

        for name, _id in zip(functs, IDs):
            method = getattr(self, "on_"+ name)  # self.on_*
            self.Bind(wx.EVT_MENU, method, id=_id )


    def make_toolbar(self):
        """
        Creates a toolbar, Pythonically :D
        """
        self.tb = self.CreateToolBar()

        ids = [wx.ID_NEW, wx.ID_OPEN, wx.ID_SAVE, wx.ID_COPY, wx.ID_PASTE,
               wx.ID_UNDO, wx.ID_REDO]
        arts = [wx.ART_NEW, wx.ART_FILE_OPEN, wx.ART_FILE_SAVE, wx.ART_COPY,
                wx.ART_PASTE, wx.ART_UNDO, wx.ART_REDO]
        tips = ["New Sheet", "Open a File", "Save Drawing", "Copy a Bitmap " +
                "Selection", "Paste Image", "Undo the Last Action",
                "Redo the Last Undone Action"]

        # add tools, add a separator and bind paste/undo/redo for UI updating
        x = 0
        for _id, art_id, tip in zip(ids, arts, tips):
            art = wx.ArtProvider.GetBitmap(art_id, wx.ART_TOOLBAR)
            self.tb.AddSimpleTool(_id, art, tip)

            if x == 2:
                self.tb.AddSeparator()
            if x >= 3:
                self.Bind(wx.EVT_UPDATE_UI, self.update_menus, id=_id)
                self.tb.EnableTool(_id, False)
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


    def on_open(self, event=None, text=None):
        """
        Opens a file, sets Utility's temp. file to the chosen file, prompts for
        an unsaved file and calls do_open().
        text is img/pdf/ps for the "import file" menu item
        """
        wc = self.util.wildcard
        if text == "img":
            wc = wc[ wc.find("Image") : wc.find("|PDF") ]  # image to page
        elif text:
            wc = wc[ wc.find("PDF") :]  # page descriptions

        dlg = wx.FileDialog(self, "Open file...", style=wx.OPEN, wildcard=wc)
        dlg.SetFilterIndex(1)

        if dlg.ShowModal() == wx.ID_OK:
            name = dlg.GetPath()

            if name.endswith(".wtbd"):
                self.util.prompt_for_save(self.do_open, args=[name])
            else:
                self.do_open(name)
        else:
            dlg.Destroy()


    def do_open(self, name):
        """
        Updates the appropriate variables in the utility file class and loads
        the selected file.
        """
        if name.endswith(".wtbd"):
            self.util.load_wtbd(name)
        else:
            self.util.temp_file = name
            self.util.load_file()


    def on_export(self, event=None, pdf=None):
        """Exports the current sheet as an image, or all as a PDF."""
        wc =  ("PDF (*.pdf)")
        if not pdf:
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


    def on_new_win(self, event=None):
        """Fires up a new Whyteboard window"""
        frame = GUI(None)
        frame.Show(True)

    def on_new_tab(self, event=None, name=None, wb=None):
        """Opens a new tab, selects it, creates a new thumbnail and tree item"""
        if not wb:
            wb = Whyteboard(self.tabs, self)
        self.thumbs.new_thumb()
        self.notes.add_tab()
        self.tab_count += 1
        if name:
            self.tabs.AddPage(wb, name)
        else:
            self.tabs.AddPage(wb, "Sheet "+ str(self.tab_count))
        self.update_panels(False)
        self.current_tab = self.tab_count - 1
        self.tabs.SetSelection(self.current_tab)  # fires on_change_tab


    def on_change_tab(self, event=None):
        """Updates tab vars, scrolls thumbnails and selects tree node"""
        self.board = self.tabs.GetCurrentPage()
        self.update_panels(False)

        self.current_tab = self.tabs.GetSelection()
        self.update_panels(True)
        #self.thumbs.Scroll(-1, self.current_tab)
        self.control.change_tool()

        if self.notes.tabs:
            tree_id = self.notes.tabs[self.current_tab]
            self.notes.tree.SelectItem(tree_id, True)

    def update_panels(self, select):
        """Updates thumbnails and notes to indicate current tab"""
        tab = self.current_tab
        if self.thumbs.text:
            font = self.thumbs.text[tab].GetClassDefaultAttributes().font
            if select:
                font.SetWeight(wx.FONTWEIGHT_BOLD)
            else:
                font.SetWeight(wx.FONTWEIGHT_NORMAL)
            self.thumbs.text[tab].SetFont(font)


    def on_close_tab(self, event=None):
        """
        Closes the current tab (if there are any to close).
        Adds the 3 lists from the Whyteboard to a list inside the undo list.
        """
        if self.tab_count - 1:
            if len(self.closed_tabs) == 10:
                del self.closed_tabs[9]

            board = self.board
            item = [board.shapes, board.undo_list, board.redo_list,
                    board.virtual_size]

            self.closed_tabs.append(item)
            self.notes.remove_tab(self.current_tab)
            self.thumbs.remove(self.current_tab)
            self.tab_count -= 1
            if os.name == "nt":
                self.tabs.DeletePage(self.current_tab)  # fires on_change_tab
            else:
                self.tabs.RemovePage(self.current_tab)  # fires on_change_tab
            self.board.redraw_all()

            for x in range(self.current_tab, self.tab_count):
                if self.tabs.GetPageText(x).startswith("Sheet "):
                    self.tabs.SetPageText(x, "Sheet " + str(x + 1))



    def on_undo_tab(self, event=None):
        """
        Undoes the last closed tab from the list.
        Re-creates the board from the saved shapes/undo/redo lists
        """
        shape = self.closed_tabs.pop()
        self.on_new_tab()
        self.board.shapes = shape[0]
        self.board.undo_list = shape[1]
        self.board.redo_list = shape[2]
        self.board.virtual_size = shape[3]

        for shape in self.board.shapes:
            shape.board = self.board
            if isinstance(shape, Note):
                self.notes.add_note(shape)
        self.board.redraw_all(True)


    def update_menus(self, event):
        """
        Enables/disables the undo/redo/next/prev button as appropriate.
        It is called every 65ms and uses a counter to update the GUI less often
        than the 65ms, as it's too performance intense
        """
        if not self.board:
            return
        _id = event.GetId()

        if _id == wx.ID_PASTE:  # check this less frequently
            self.count += 1
            if self.count == 5:
                self.can_paste = False

                if self.util.get_clipboard():
                    self.can_paste = True
                self.count = 0
            event.Enable(self.can_paste)
            self.menu.Enable(ID_PASTE_NEW, self.can_paste)
            return

        do = False
        if not _id == wx.ID_COPY:
            # update the GUI to the inverse of the bool value if the button
            # should be enabled
            if _id == wx.ID_REDO and self.board.redo_list:
                do = True
            elif _id == wx.ID_UNDO and self.board.undo_list:
                do = True
            elif _id == ID_PREV and self.current_tab > 0:
                do = True
            elif (_id == ID_NEXT and self.tab_count > 1 and
             (self.current_tab + 1 < self.tab_count)):
                do = True
            elif _id == ID_UNDO_SHEET and len(self.closed_tabs) >= 1:
                do = True
        elif self.board:
            if self.board.copy:
                do = True

        event.Enable(do)


    def on_copy(self, event):
        """ If a rectangle selection is made, copy the selection as a bitmap"""
        self.board.copy.sort_args()
        rect = self.board.copy.rect
        self.board.copy = None
        self.board.redraw_all()
        self.util.set_clipboard(rect)
        self.count = 4
        self.UpdateWindowUI()  # force paste buttons to enable (it counts to 4)


    def on_paste(self, event=None):
        """ Grabs the image from the clipboard and places it on the panel """
        shape = self.get_paste()
        shape.button_down(0, 0)
        self.board.redraw_all(True)

    def on_paste_new(self, event):
        """ Pastes the image into a new tab """
        self.on_new_tab()
        self.on_paste()

    def get_paste(self):
        """ Returns an Image of the clipboard's bitmap """
        bmp = self.util.get_clipboard()
        if bmp:
            return Image(self.board, bmp.GetBitmap(), None)

    def on_fullscreen(self, event=None):
        """ Toggles fullscreen """
        flag = (wx.FULLSCREEN_NOBORDER | wx.FULLSCREEN_NOCAPTION |
               wx.FULLSCREEN_NOSTATUSBAR)
        self.ShowFullScreen(not self.IsFullScreen(), flag)


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
        """Destroy the progress process after convert returns"""
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
        """Ask to save, quit or cancel if the user hasn't saved."""
        self.util.prompt_for_save(self.Destroy)

    def tab_popup(self, event):
        """ Pops up the tab context menu. """
        self.PopupMenu(SheetsPopup(self, (event.GetX(), event.GetY())))

    def on_undo(self, event=None):
        """ Calls undo on the active tab and updates the menus """
        self.board.undo()

    def on_redo(self, event=None):
        """ Calls redo on the active tab and updates the menus """
        self.board.redo()

    def on_prev(self, event=None):
        """ Changes to the previous sheet """
        self.tabs.SetSelection(self.current_tab - 1)

    def on_next(self, event=None):
        """ Changes to the next sheet """
        self.tabs.SetSelection(self.current_tab + 1)

    def on_clear(self, event=None):
        """ Clears current sheet's drawings, except images. """
        self.board.clear(keep_images=True)

    def on_clear_all(self, event=None):
        """ Clears current sheet """
        self.board.clear()

    def on_clear_sheets(self, event=None):
        """ Clears all sheets' drawings, except images. """
        for tab in range(self.tab_count):
            self.tabs.GetPage(tab).clear(keep_images=True)

    def on_clear_all_sheets(self, event=None):
        """ Clears all sheets ***"""
        for tab in range(self.tab_count):
            self.tabs.GetPage(tab).clear()

    def on_refresh(self):
        """Refresh all thumbnails."""
        self.thumbs.update_all()

    def on_resize(self, event=None):
        dlg = Resize(self)
        dlg.ShowModal()
        dlg.Destroy()

    def on_update(self, event=None):
        """ Checks for new versions of the program ***"""
        dlg = UpdateDialog(self)
        dlg.ShowModal()

    def on_history(self, event=None):
        dlg = History(self)
        dlg.ShowModal()
        dlg.Destroy()

    def on_help(self, event=None):
        """
        Shows the help file, if it exists, otherwise prompts the user to
        download it.
        """
        path = self.util.path[0]
        _file = os.path.join(path, 'whyteboard-help', 'whyteboard.hhp')

        if os.path.exists(_file):
            self.help = wx.html.HtmlHelpController()
            self.help.AddBook(_file)
            self.help.DisplayContents()
        else:
            msg = ("Help files not found, do you want to download them?")
            d = wx.MessageDialog(self, msg, style=wx.YES_NO | wx.ICON_QUESTION)
            if d.ShowModal() == wx.ID_YES:
                try:
                    self.util.download_help_files()
                    wx.MessageBox("Folder whyteboard-help created")
                except IOError:
                    pass
                else:
                    self.on_help()


    def on_about(self, event=None):
        info = wx.AboutDialogInfo()
        info.Name = "Whyteboard"
        info.Version = self.version
        info.Copyright = "(C) 2009 Steven Sproat"
        info.Description = "A simle PDF annotator and image editor"
        info.WebSite = ("http://www.launchpad.net/whyteboard", "Launchpad")
        info.Developers = ["Steven Sproat"]
        wx.AboutBox(info)


#----------------------------------------------------------------------

class WhyteboardApp(wx.App):
    def OnInit(self):
        self.SetAppName("whyteboard")  # used to identify app in $HOME/
        self.frame = GUI(None)
        self.frame.Show(True)
        #self.Bind(wx.EVT_CHAR, self.on_key)
        self.parse_args()
        self.delete_temp_files()
        return True

    def parse_args(self):
        """Forward the first command-line arg to gui.do_open()"""
        try:
            _file = sys.argv[1]
            if os.path.exists(_file):
                self.frame.do_open(os.path.abspath(sys.argv[1]))
        except IndexError:
            pass

    def delete_temp_files(self):
        """
        Delete temporary files from an update. Remove a backup exe, otherwise
        iterate over the current directory (where the backup files will be) and
        remove any that matches the randon file extension
        """
        if self.frame.util.is_exe() and os.path.exists("wtbd-bckup.exe"):
            os.remove("wtbd-bckup.exe")
        else:
            path = self.frame.util.path[0]
            for f in os.listdir(path):
                if f.find(self.frame.util.backup_ext) is not -1:
                    os.remove(os.path.join(path, f))


    def on_key(self, event):
        """ Change tool when a number is pressed """
        frame = self.frame
        x = len(frame.util.items)
        key = event.GetKeyCode()

        #  49 -- key 1. change_tool expects list element num + 1
        if key >= 49 and key <= 49 + x:
            frame.control.change_tool(_id=key - 48)

        elif key == wx.WXK_UP and frame.current_tab > 0:
            frame.tabs.SetSelection(frame.current_tab - 1)

        elif (key == wx.WXK_DOWN and frame.tab_count > 1 and
             (frame.current_tab + 1 < frame.tab_count)):
            frame.tabs.SetSelection(frame.current_tab + 1)

        elif key == wx.WXK_ESCAPE:
            if frame.IsFullScreen():
                frame.on_fullscreen()
        event.Skip()

#----------------------------------------------------------------------

def main():
    app = WhyteboardApp()
    app.MainLoop()

if __name__ == '__main__':
    main()
