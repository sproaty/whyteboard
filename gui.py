# -*- coding: utf-8 -*-
#!/usr/bin/python

# Copyright (c) 2009 by Steven Sproat
#
# GNU General Public Licence (GPL)
#
s = """Whyteboard is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by the Free
Software Foundation; either version 3 of the License, or (at your option) any
later version.
Whyteboard is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE.  See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
Whyteboard; if not, write to the Free Software Foundation, Inc., 59 Temple
Place, Suite 330, Boston, MA  02111-1307  USA"""


"""
This module implements the Whteboard application.  It takes a Whyteboard class
and wraps it in a GUI with a menu/toolbar/statusbar; can save and load drawings,
clear the workspace, undo, redo, a simple history "replayer", allowing you to
have a replay of what you have drawn played back to you.

Also on the GUI is a panel for setting color and line thickness, with an
indicator that shows a drawing preview. On the right is a tabbed panel, allowing
the user to switch between viewing Thumbnails of each drawing's tab, or a Tree
of Notes that the user has inputted.
"""


import os
import sys
import locale
import webbrowser
import wx
import wx.lib.newevent
from wx.html import HtmlHelpController
from wx.lib.wordwrap import wordwrap

from lib.configobj import ConfigObj
from lib.validate import Validator

import lib.icon
from whyteboard import Whyteboard
from tools import Image, Note
from utility import Utility, FileDropTarget, languages, cfg, get_home_dir
from dialogs import (History, ProgressDialog, Resize, Rotate, UpdateDialog,
                     MyPrintout, ExceptionHook)
from panels import ControlPanel, SidePanel, SheetsPopup
from preferences import Preferences


ID_CLEAR_ALL = wx.NewId()         # remove everything from current tab
ID_CLEAR_ALL_SHEETS = wx.NewId()  # remove everything from all tabs
ID_CLEAR_SHEETS = wx.NewId()      # remove all drawings from all tabs, keep imgs
ID_EXPORT = wx.NewId()            # export sheet to image file
ID_EXPORT_ALL = wx.NewId()        # export every sheet to numbered image files
ID_FULLSCREEN = wx.NewId()        # toggle fullscreen
ID_HISTORY = wx.NewId()           # history viewer
ID_IMG = wx.NewId()               # import->Image
ID_NEW = wx.NewId()               # new window
ID_NEXT = wx.NewId()              # next sheet
ID_PASTE_NEW = wx.NewId()         # paste as new selection
ID_PDF = wx.NewId()               # import->PDF
ID_PREV = wx.NewId()              # previous sheet
ID_PS = wx.NewId()                # import->PS
ID_RENAME = wx.NewId()            # rename sheet
ID_REPORT_BUG = wx.NewId()        # report a problem
ID_RESIZE = wx.NewId()            # resize dialog
ID_ROTATE = wx.NewId()            # rotate dialog for image 90/180/270
ID_STATUSBAR = wx.NewId()         # toggle statusbar
ID_TOOLBAR = wx.NewId()           # toggle toolbar
ID_TRANSLATE = wx.NewId()         # open translation URL
ID_UNDO_SHEET = wx.NewId()        # undo close sheet
ID_UPDATE = wx.NewId()            # update self
#ID_EXP_IMG = wx.NewId()           # export->Image
#ID_EXP_PDF = wx.NewId()           # export->PDF

_ = wx.GetTranslation            # Define a translation string

#----------------------------------------------------------------------


class GUI(wx.Frame):
    """
    This class contains a ControlPanel, a Whyteboard frame and a SidePanel
    and manages their layout with a wx.BoxSizer.  A menu, toolbar and associated
    event handlers call the appropriate functions of other classes.
    """
    version = "0.38.8"
    title = "Whyteboard " + version
    LoadEvent, LOAD_DONE_EVENT = wx.lib.newevent.NewEvent()

    def __init__(self, parent, config):
        """
        Initialise utility, status/menu/tool bar, tabs, ctrl panel + bindings.
        """
        wx.Frame.__init__(self, parent, title=_("Untitled")+" - " + self.title)
        ico = lib.icon.whyteboard.getIcon()
        self.SetIcon(ico)
        self.SetExtraStyle(wx.WS_EX_PROCESS_UI_UPDATES)
        self.util = Utility(self, config)
        self.file_drop = FileDropTarget(self)
        self.SetDropTarget(self.file_drop)
        self.statusbar = self.CreateStatusBar()
        self.printData = wx.PrintData()
        self.printData.SetPaperId(wx.PAPER_LETTER)
        self.printData.SetPrintMode(wx.PRINT_MODE_PRINTER)

        self._oldhook = sys.excepthook
        sys.excepthook = ExceptionHook

        self.can_paste = False
        if self.util.get_clipboard():
            self.can_paste = True
        self.toolbar = None
        self.menu = None
        self.process = None
        self.pid = None
        self.dialog = None
        self.convert_cancelled = False
        self.help = None
        self.make_toolbar()
        self.make_menu()
        self.bar_shown = True  # slight performance optimisation
        self.find_help()
        self.tab_count = 1  # instead of typing self.tabs.GetPageCount()
        self.current_tab = 0
        self.closed_tabs = []  # [shapes - undo - redo - canvas_size] per tab

        self.control = ControlPanel(self)
        self.tabs = wx.Notebook(self)
        self.board = Whyteboard(self.tabs, self)  # the active whiteboard tab
        self.panel = SidePanel(self)
        self.thumbs = self.panel.thumbs
        self.notes = self.panel.notes
        self.tabs.AddPage(self.board, _("Sheet")+" 1")
        box = wx.BoxSizer(wx.HORIZONTAL)  # position windows side-by-side
        box.Add(self.control, 0, wx.EXPAND)
        box.Add(self.tabs, 2, wx.EXPAND)
        box.Add(self.panel, 0, wx.EXPAND)
        self.SetSizer(box)
        self.SetSizeWH(800, 600)
        self.Maximize(True)

        self.count = 4  # used to update menu timings
        wx.UpdateUIEvent.SetUpdateInterval(65)
        wx.UpdateUIEvent.SetMode(wx.UPDATE_UI_PROCESS_SPECIFIED)
        self.do_bindings()
        self.update_panels(True)  # bold first items
        self.UpdateWindowUI()


    def __del__(self):
        sys.excepthook = self._oldhook


    def make_menu(self):
        """
        Creates the menu...pretty damn messy, may give this a cleanup like the
        do_bindings/make_toolbar. I hate this method - made worse by i8n!
        """
        self.menu = wx.MenuBar()
        _file = wx.Menu()
        edit = wx.Menu()
        view = wx.Menu()
        sheets = wx.Menu()
        _help = wx.Menu()
        _import = wx.Menu()
        _import.Append(ID_IMG, _('&Image...'))
        _import.Append(ID_PDF, '&PDF...')
        _import.Append(ID_PS, 'Post&Script...')
        #_export = wx.Menu()
        #_export.Append(ID_EXP_PDF, '&PDF')
        #_export.Append(ID_EXP_IMG, 'Current Sheet as &Image')

        new = wx.MenuItem(_file, ID_NEW, _("New &Window")+"\tCtrl-N", _("Opens a new Whyteboard instance"))
        new.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_NEW, wx.ART_MENU))

        pnew = wx.MenuItem(edit, ID_PASTE_NEW, _("Paste to a &New Sheet")+"\tCtrl+Shift-V", _("Paste from your clipboard into a new sheet"))
        pnew.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_PASTE, wx.ART_MENU))

        undo_sheet = wx.MenuItem(edit, ID_UNDO_SHEET, _("&Undo Last Closed Sheet")+"\tCtrl+Shift-T", _("Undo the last closed sheet"))
        undo_sheet.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_UNDO, wx.ART_MENU))

        _file.AppendItem(new)
        _file.Append(wx.ID_OPEN, _("&Open...")+"\tCtrl-O", _("Load a Whyteboard save file, an image or convert a PDF/PS document"))
        _file.AppendSeparator()
        _file.Append(wx.ID_SAVE, _("&Save")+"\tCtrl+S", _("Save the Whyteboard data"))
        _file.Append(wx.ID_SAVEAS, _("Save &As...")+"\tCtrl+Shift+S", _("Save the Whyteboard data in a new file"))
        _file.AppendSeparator()
        _file.AppendMenu(+1, _('&Import File'), _import)
        #_file.AppendMenu(+1, '&Export File', _export)
        _file.Append(ID_EXPORT, _("&Export Sheet...")+"\tCtrl+E", _("Export the current sheet to an image file"))
        _file.Append(ID_EXPORT_ALL, _("Export &All Sheets...")+"\tCtrl+Shift+E", _("Export every sheet to a series of image files"))
        _file.AppendSeparator()
        _file.Append(wx.ID_PRINT_SETUP, _("Page Set&up"), _("Set up the page for printing"))
        _file.Append(wx.ID_PREVIEW_PRINT, _("Print Pre&view"), _("View a preview of the page to be printed"))
        _file.Append(wx.ID_PRINT, _("&Print...")+"\tCtrl+P", _("Print the current page"))
        _file.AppendSeparator()
        _file.Append(wx.ID_EXIT, _("&Quit")+"\tAlt+F4", _("Quit Whyteboard"))

        edit.Append(wx.ID_UNDO, _("&Undo")+"\tCtrl+Z", _("Undo the last operation"))
        edit.Append(wx.ID_REDO, _("&Redo")+"\tCtrl+Y", _("Redo the last undone operation"))
        edit.AppendSeparator()
        edit.Append(ID_RESIZE, _("Re&size Canvas...")+"\tCtrl+R", _("Change the canvas' size"))
        edit.Append(ID_ROTATE, _("R&otate Image..."), _("Rotate the selected image"))
        edit.Append(wx.ID_DELETE, _("&Delete Shape")+"\tDelete", _("Delete the currently selected shape"))        
        edit.AppendSeparator()
        edit.Append(wx.ID_COPY, _("&Copy")+"\tCtrl+C", _("Copy a Bitmap Selection region"))
        edit.Append(wx.ID_PASTE, _("&Paste")+"\tCtrl+V", _("Paste an image from your clipboard into Whyteboard"))
        edit.AppendItem(pnew)
        edit.AppendSeparator()
        edit.Append(wx.ID_PREFERENCES, _("Prefere&nces"), _("Change your preferences"))

        view.Append(ID_HISTORY, _("&History Viewer...")+"\tCtrl+H", _("View and replay your drawing history"))
        view.AppendSeparator()
        self.showtool = view.Append(ID_TOOLBAR," "+ _("&Toolbar"), _("Show and hide the toolbar"), kind=wx.ITEM_CHECK)
        self.showstat = view.Append(ID_STATUSBAR, " "+_("&Status Bar"), _("Show and hide the status bar"), kind=wx.ITEM_CHECK)
        view.Append(ID_FULLSCREEN, " "+_("&Full Screen")+"\tF11", _("View Whyteboard in full-screen mode"), kind=wx.ITEM_CHECK)

        sheets.Append(wx.ID_NEW, _("&New Sheet")+"\tCtrl-T", _("Add a new sheet"))
        sheets.Append(wx.ID_CLOSE, _("&Remove Sheet")+"\tCtrl+W", _("Close the current sheet"))
        sheets.Append(ID_RENAME, _("&Rename Sheet..."), _("Rename the current sheet"))
        sheets.AppendSeparator()
        self.next = sheets.Append(ID_NEXT, _("&Next Sheet")+"\tCtrl+Tab", _("Go to the next sheet"))
        self.prev = sheets.Append(ID_PREV, _("&Previous Sheet")+"\tCtrl+Shift+Tab", _("Go to the previous sheet"))
        sheets.AppendItem(undo_sheet)
        sheets.AppendSeparator()
        sheets.Append(wx.ID_CLEAR, _("&Clear Sheets' Drawings"), _("Clear drawings on the current sheet (keep images)"))
        sheets.Append(ID_CLEAR_ALL, _("Clear &Sheet"), _("Clear the current sheet"))
        sheets.AppendSeparator()
        sheets.Append(ID_CLEAR_SHEETS, _("Clear All Sheets' &Drawings"), _("Clear all sheets' drawings (keep images)"))
        sheets.Append(ID_CLEAR_ALL_SHEETS, _("Clear &All Sheets"), _("Clear all sheets"))

        _help.Append(wx.ID_HELP, _("&Contents")+"\tF1", _("View information about Whyteboard"))
        _help.AppendSeparator()
        _help.Append(ID_UPDATE, _("Check for &Updates...")+"\tF12", _("Search for updates to Whyteboard"))
        _help.Append(ID_REPORT_BUG, _("&Report a Problem"), _("Report any bugs or issues with Whyteboard"))
        _help.Append(ID_TRANSLATE, _("&Translate Whyteboard"), _("Translate Whyteboard to your language"))
        _help.AppendSeparator()
        _help.Append(wx.ID_ABOUT, _("&About"), _("View information about Whyteboard"))
        self.menu.Append(_file, _("&File"))
        self.menu.Append(edit, _("&Edit"))
        self.menu.Append(view, _("&View"))
        self.menu.Append(sheets, _("&Sheets"))
        self.menu.Append(_help, _("&Help"))
        self.SetMenuBar(self.menu)
        self.menu.Enable(ID_PASTE_NEW, self.can_paste)
        self.menu.Enable(ID_UNDO_SHEET, False)


        if self.util.config['toolbar']:
            view.Check(ID_TOOLBAR, True)
        else:
            self.on_toolbar(None, False)
        if self.util.config['statusbar']:
            view.Check(ID_STATUSBAR, True)
        else:
            self.on_statusbar(None, False)


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
        self.Bind(wx.EVT_UPDATE_UI, self.update_menus, id=wx.ID_DELETE)
        self.Bind(wx.EVT_UPDATE_UI, self.update_menus, id=ID_ROTATE)
        self.tabs.Bind(wx.EVT_RIGHT_UP, self.tab_popup)

        ac = [(wx.ACCEL_CTRL, ord('\t'), self.next.GetId()),
              (wx.ACCEL_CTRL | wx.ACCEL_SHIFT, ord('\t'), self.prev.GetId()) ]        
        tbl = wx.AcceleratorTable(ac)
        self.SetAcceleratorTable(tbl)


        ids = { 'pdf': ID_PDF, 'ps': ID_PS, 'img': ID_IMG }  # file->import
        [self.Bind(wx.EVT_MENU, lambda evt, text = key: self.on_open(evt, text),
                    id=ids[key]) for key in ids]

        functs = ["new_win", "new_tab", "open",  "close_tab", "save", "save_as", "export", "export_all", "page_setup", "print_preview", "print", "exit", "undo", "redo", "undo_tab",
                  "copy", "paste", "rotate", "delete_shape", "preferences", "paste_new", "history", "resize", "fullscreen", "toolbar", "statusbar", "prev", "next", "clear", "clear_all",
                  "clear_sheets", "clear_all_sheets", "rename", "help", "update", "translate", "report_bug", "about"]

        IDs = [ID_NEW, wx.ID_NEW, wx.ID_OPEN, wx.ID_CLOSE, wx.ID_SAVE, wx.ID_SAVEAS, ID_EXPORT, ID_EXPORT_ALL, wx.ID_PRINT_SETUP, wx.ID_PREVIEW_PRINT, wx.ID_PRINT, wx.ID_EXIT, wx.ID_UNDO,
               wx.ID_REDO, ID_UNDO_SHEET, wx.ID_COPY, wx.ID_PASTE, ID_ROTATE, wx.ID_DELETE, wx.ID_PREFERENCES, ID_PASTE_NEW, ID_HISTORY, ID_RESIZE, ID_FULLSCREEN, ID_TOOLBAR, ID_STATUSBAR, 
               ID_PREV, ID_NEXT, wx.ID_CLEAR, ID_CLEAR_ALL, ID_CLEAR_SHEETS, ID_CLEAR_ALL_SHEETS, ID_RENAME, wx.ID_HELP, ID_UPDATE, ID_TRANSLATE, ID_REPORT_BUG, wx.ID_ABOUT]

        for name, _id in zip(functs, IDs):
            method = getattr(self, "on_"+ name)  # self.on_*
            self.Bind(wx.EVT_MENU, method, id=_id )


    def make_toolbar(self):
        """
        Creates a toolbar, Pythonically :D
        """
        self.toolbar = self.CreateToolBar()

        ids = [wx.ID_NEW, wx.ID_OPEN, wx.ID_SAVE, wx.ID_COPY, wx.ID_PASTE,
               wx.ID_UNDO, wx.ID_REDO, wx.ID_DELETE]
        arts = [wx.ART_NEW, wx.ART_FILE_OPEN, wx.ART_FILE_SAVE, wx.ART_COPY,
                wx.ART_PASTE, wx.ART_UNDO, wx.ART_REDO, wx.ART_DELETE]
        tips = [_("New Sheet"), _("Open a File"), _("Save Drawing"), _("Copy a Bitmap Selection"), 
                _("Paste Image"), _("Undo the Last Action"), _("Redo the Last Undone Action"), 
                _("Delete the currently selected shape")]

        # add tools, add a separator and bind paste/undo/redo for UI updating
        x = 0
        for _id, art_id, tip in zip(ids, arts, tips):
            art = wx.ArtProvider.GetBitmap(art_id, wx.ART_TOOLBAR)
            self.toolbar.AddSimpleTool(_id, art, tip)

            if x == 2 or x == 6:
                self.toolbar.AddSeparator()
            if x >= 3:
                self.Bind(wx.EVT_UPDATE_UI, self.update_menus, id=_id)
                self.toolbar.EnableTool(_id, False)
            x += 1
        self.toolbar.Realize()


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
        dlg = wx.FileDialog(self, _("Save Whyteboard As..."), os.getcwd(),
                style=wx.SAVE | wx.OVERWRITE_PROMPT,
                wildcard = _("Whyteboard file ")+"(*.wtbd)|*.wtbd")
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

        dlg = wx.FileDialog(self, _("Open file..."), style=wx.OPEN, wildcard=wc)
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
        filename = self.export_prompt()
        if filename:
            self.util.export(filename)


    def on_export_all(self, event=None):
        """
        Iterate over the chosen filename, add a numeric value to each path to
        separate each sheet's image.
        """
        filename = self.export_prompt()
        if filename:
            name = os.path.splitext(filename)
            board = self.board
            for x in range(0, self.tab_count):
                self.board = self.tabs.GetPage(x)
                filename = name[0] + "-%s" % (x + 1) + name[1]
                self.util.export(filename)
            self.board = board


    def export_prompt(self):
        """Find out the filename to save to"""
        val = None  # return balue
        wc =  ("PNG (*.png)|*.png|JPEG (*.jpg, *.jpeg)|*.jpeg;*.jpg|" +
               "BMP (*.bmp)|*.bmp|TIFF (*.tiff)|*.tiff")

        dlg = wx.FileDialog(self, _("Export data to..."), style=wx.SAVE |
                             wx.OVERWRITE_PROMPT, wildcard=wc)
        if dlg.ShowModal() == wx.ID_OK:
            filename = dlg.GetPath()
            _name = os.path.splitext(filename)[1].replace(".", "")
            types = {0: "png", 1: "jpg", 2: "bmp", 3: "tiff"}

            if not os.path.splitext(filename)[1]:
                _name = types[dlg.GetFilterIndex()]
                filename += "." + _name
                val = filename
            if not _name in self.util.types[2:]:
                wx.MessageBox(_("Invalid filetype to export as:")+" .%s" % _name,
                              _("Invalid filetype"))
            else:
                val = filename

        dlg.Destroy()
        return val


    def on_new_win(self, event=None):
        """Fires up a new Whyteboard window"""
        frame = GUI(None, self.util.config)
        frame.Show(True)


    def on_new_tab(self, event=None, name=None, wb=None):
        """Opens a new tab, selects it, creates a new thumbnail and tree item"""
        if not wb:
            wb = Whyteboard(self.tabs, self)
        self.thumbs.new_thumb(name=name)
        self.notes.add_tab(name)
        self.tab_count += 1
        if name:
            self.tabs.AddPage(wb, name)
        else:
            self.tabs.AddPage(wb, _("Sheet")+" %s" % self.tab_count)
        self.update_panels(False)
        self.current_tab = self.tab_count - 1
        self.tabs.SetSelection(self.current_tab)  # fires on_change_tab


    def on_change_tab(self, event=None):
        """Updates tab vars, scrolls thumbnails and selects tree node"""
        self.board = self.tabs.GetCurrentPage()
        self.update_panels(False)

        self.current_tab = self.tabs.GetSelection()
        if event:
            self.current_tab = event.GetSelection()

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
            try:
                font = self.thumbs.text[tab].GetClassDefaultAttributes().font
                if select:
                    font.SetWeight(wx.FONTWEIGHT_BOLD)
                else:
                    font.SetWeight(wx.FONTWEIGHT_NORMAL)
                self.thumbs.text[tab].SetFont(font)
            except IndexError:
                pass  # ignore a bug closing the last tab from the pop-up menu
                      # temp fix, can't think how to solve it otherwise


    def on_close_tab(self, event=None):
        """
        Closes the current tab (if there are any to close).
        Adds the 3 lists from the Whyteboard to a list inside the undo tab list.
        """
        if not self.tab_count - 1:  # must have at least one sheet open
            return
        if len(self.closed_tabs) == self.util.config['undo_sheets']:
            del self.closed_tabs[self.util.config['undo_sheets'] - 1]

        # doesn't remove the notes if called earlier
        self.notes.remove_tab(self.current_tab)
        self.thumbs.remove(self.current_tab)

        board = self.board
        name = ""
        if board.renamed:
            name = self.tabs.GetPageText(self.current_tab)
        item = [board.shapes, board.undo_list, board.redo_list,
                board.area, name]

        self.closed_tabs.append(item)
        self.tab_count -= 1
        if os.name == "posix":
            self.tabs.RemovePage(self.current_tab)
        else:
            self.tabs.DeletePage(self.current_tab)

        self.on_change_tab()  # updates self.board

        for x in range(self.tab_count):
            if not self.tabs.GetPage(x).renamed:
                self.tabs.SetPageText(x, _("Sheet")+" %s" % (x + 1))


    def on_undo_tab(self, event=None):
        """
        Undoes the last closed tab from the list.
        Re-creates the board from the saved shapes/undo/redo lists
        """
        #self.board.redraw_all()
        if not self.closed_tabs:
            return
        board = self.closed_tabs.pop()

        if board[4]:
            self.on_new_tab(name=board[4])
        else:
            self.on_new_tab()
        self.board.shapes = board[0]
        self.board.undo_list = board[1]
        self.board.redo_list = board[2]

        for shape in self.board.shapes:
            shape.board = self.board
            if isinstance(shape, Note):
                self.notes.add_note(shape)

        wx.Yield()  # doesn't draw thumbnail otherwise...
        self.board.resize_canvas(board[3])
        self.board.redraw_all(True)


    def on_rename(self, event=None, sheet=None):
        if not sheet:
            sheet = self.current_tab
        dlg = wx.TextEntryDialog(self, _("Rename this sheet to:"),
                                                        _("Rename sheet"))
        dlg.SetValue(self.tabs.GetPageText(sheet))

        if dlg.ShowModal() == wx.ID_CANCEL:
            dlg.Destroy()
        else:
            val = dlg.GetValue()
            if val:
                self.tabs.SetPageText(sheet, val)
                self.tabs.GetPage(sheet).renamed = True
                self.thumbs.update_name(sheet, val)
                self.notes.update_name(sheet, val)

    def on_delete_shape(self, event=None):
        self.board.delete_selected()
                
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
                try:
                    event.Enable(self.can_paste)
                    self.menu.Enable(ID_PASTE_NEW, self.can_paste)
                    self.menu.Enable(wx.ID_PASTE, self.can_paste)
                except wx.PyDeadObjectError:
                    pass
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
            elif _id == wx.ID_DELETE and self.board.selected:
                do = True   
            elif (_id == ID_ROTATE and self.board.selected 
                  and isinstance(self.board.selected, Image)): 
                do = True                                
        elif self.board:
            if self.board.copy:
                do = True
        event.Enable(do)


    def on_copy(self, event):
        """
        If a rectangle selection is made, copy the selection as a bitmap. 
        NOTE: The bitmap selection can be larger than the actual canvas bitmap,
        so we must only selection the region of the selection that is on the 
        canvas
        """        
        self.board.copy.update_rect()  # ensure w, h are correct
        bmp = self.board.copy

        if bmp.x + bmp.width > self.board.area[0]:
            bmp.rect.SetWidth(self.board.area[0] - bmp.x)
            
        if bmp.y + bmp.height > self.board.area[1]:
            bmp.rect.SetHeight(self.board.area[1] - bmp.y)
                
        self.board.copy = None
        self.board.redraw_all()
        self.util.set_clipboard(bmp.rect)
        self.count = 4
        self.UpdateWindowUI()  # force paste buttons to enable (it counts to 4)


    def on_paste(self, event=None):
        """ Grabs the image from the clipboard and places it on the panel """
        bmp = self.util.get_clipboard()
        if not bmp:
            return
        shape = Image(self.board, bmp.GetBitmap(), None)
        
        x, y = self.board.ScreenToClient(wx.GetMousePosition())
        x, y = self.board.CalcUnscrolledPosition(x, y)
        shape.left_down(x, y)
        wx.Yield()
        self.board.redraw_all(True)


    def on_paste_new(self, event):
        """ Pastes the image into a new tab """
        self.on_new_tab()
        self.on_paste()


    def on_fullscreen(self, event=None):
        """ Toggles fullscreen """
        flag = (wx.FULLSCREEN_NOBORDER | wx.FULLSCREEN_NOCAPTION |
               wx.FULLSCREEN_NOSTATUSBAR)
        self.ShowFullScreen(not self.IsFullScreen(), flag)


    def on_toolbar(self, event=None, force=None):
        """ Toggles the toolbar """
        if self.showtool.IsChecked() or force:
            self.toolbar.Show()
            self.showtool.Check(True)
        else:
            self.toolbar.Hide()
            self.showtool.Check(False)
        if force is False:
            self.toolbar.Hide()
            self.showtool.Check(False)
        self.SendSizeEvent()


    def on_statusbar(self, event=None, force=None):
        if self.showstat.IsChecked() or force:
            self.statusbar.Show()
            self.showstat.Check(True)
            self.bar_shown = True
        else:
            self.statusbar.Hide()
            self.showstat.Check(False)
            self.bar_shown = False
        if force is False:
            self.statusbar.Hide()
            self.showstat.Check(False)
            self.bar_shown = False
        self.SendSizeEvent()


    def convert_dialog(self, cmd):
        """
        Called when the convert process begins, executes the process call and
        shows the convert dialog
        """
        self.process = wx.Process(self)
        self.pid = wx.Execute(cmd, wx.EXEC_ASYNC, self.process)
        self.dialog = ProgressDialog(self, _("Converting..."), cancellable=True)
        self.dialog.ShowModal()


    def on_end_process(self, event):
        """ Destroy the progress process after convert returns """
        self.process.Destroy()
        self.dialog.Destroy()
        del self.process
        self.pid = None


    def on_done_load(self, event=None):
        """ Refreshes thumbnails, destroys progress dialog after loading """
        self.dialog.SetTitle(_("Updating Thumbnails"))
        wx.MilliSleep(50)
        wx.SafeYield()
        self.on_refresh()  # force thumbnails
        self.dialog.Destroy()


    def on_exit(self, event=None):
        """ Ask to save, quit or cancel if the user hasn't saved. """
        self.util.prompt_for_save(self.Destroy)


    def tab_popup(self, event):
        """ Pops up the tab context menu. """
        self.PopupMenu(SheetsPopup(self, self, (event.GetX(), event.GetY())))


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


    def on_page_setup(self, evt):
        psdd = wx.PageSetupDialogData(self.printData)
        psdd.CalculatePaperSizeFromId()
        dlg = wx.PageSetupDialog(self, psdd)
        dlg.ShowModal()
        self.printData = wx.PrintData( dlg.GetPageSetupData().GetPrintData() )
        dlg.Destroy()


    def on_print_preview(self, event):
        data = wx.PrintDialogData(self.printData)
        printout = MyPrintout(self)
        printout2 = MyPrintout(self)
        self.preview = wx.PrintPreview(printout, printout2, data)

        if not self.preview.Ok():
            wx.MessageBox(_("There was a problem printing.\nPerhaps your current printer is not set correctly?"),
              _("Printing Error"))
            return

        pfrm = wx.PreviewFrame(self.preview, self, _("Print Preview"))
        pfrm.Initialize()
        pfrm.SetPosition(self.GetPosition())
        pfrm.SetSize(self.GetSize())
        pfrm.Show(True)


    def on_print(self, event):
        pdd = wx.PrintDialogData(self.printData)
        pdd.SetToPage(2)
        printer = wx.Printer(pdd)
        printout = MyPrintout(self)

        if not printer.Print(self.board, printout, True):
            if printer.GetLastError() is not wx.PRINTER_CANCELLED:
                wx.MessageBox(_("There was a problem printing.\nPerhaps your current printer is not set correctly?"),
                              _("Printing Error"), wx.OK)
        else:
            self.printData = wx.PrintData( printer.GetPrintDialogData().GetPrintData() )
        printout.Destroy()


    def on_translate(self, event):
        wx.BeginBusyCursor()
        webbrowser.open_new_tab("https://translations.launchpad.net/whyteboard")
        wx.CallAfter(wx.EndBusyCursor)


    def on_report_bug(self, event):
        wx.BeginBusyCursor()
        webbrowser.open_new_tab("https://bugs.launchpad.net/whyteboard")
        wx.CallAfter(wx.EndBusyCursor)


    def on_resize(self, event=None):
        dlg = Resize(self)
        dlg.ShowModal()
        

    def on_rotate(self, event=None):
        dlg = Rotate(self)
        dlg.ShowModal()
        
        
    def on_preferences(self, event=None):
        """ Checks for new versions of the program ***"""
        dlg = Preferences(self)
        dlg.ShowModal()


    def on_update(self, event=None):
        """ Checks for new versions of the program ***"""
        dlg = UpdateDialog(self)
        dlg.ShowModal()


    def on_history(self, event=None):
        dlg = History(self)
        dlg.ShowModal()
        dlg.Destroy()


    def find_help(self):
        """Locate the help files, update self.help var"""
        path = self.util.path[0]
        _file = os.path.join(path, 'whyteboard-help', 'whyteboard.hhp')

        if os.path.exists(_file):
            self.help = HtmlHelpController()
            self.help.AddBook(_file)
        else:
            self.help = None


    def on_help(self, event=None, page=None):
        """
        Shows the help file, if it exists, otherwise prompts the user to
        download it.
        """
        if self.help:
            if page:
                self.help.Display(page)
            else:
                self.help.DisplayContents()
        else:
            if self.download_help():
                self.on_help(page=page)


    def download_help(self):
        """Downloads the help files"""
        msg = _("Help files not found, do you want to download them?")
        d = wx.MessageDialog(self, msg, style=wx.YES_NO | wx.ICON_QUESTION)
        if d.ShowModal() == wx.ID_YES:
            try:
                self.util.download_help_files()
                self.find_help()
                return True
            except IOError:
                return False


    def on_about(self, event=None):
        inf = wx.AboutDialogInfo()
        inf.Name = "Whyteboard"
        inf.Version = self.version
        inf.Copyright = "(C) 2009 Steven Sproat"
        inf.Description = _("A simple whiteboard and PDF annotator")
        inf.Developers = ["Steven Sproat <sproaty@gmail.com>"]
        t = ['A. Emmanuel Mendoza https://launchpad.net/~a.emmanuelmendoza (Spanish)',
             'Alexey Reztsov https://launchpad.net/~ariafan (Russian)',
             '"Amy" https://launchpad.net/~anthropofobe (German)',
             'David Aller https://launchpad.net/~niclamus (Italian)', 
             '"Dennis" https://launchpad.net/~dlinn83 (German)',
             'Diejo Lopez https://launchpad.net/~diegojromerolopez (Spanish)',
             'Fernando Muñoz https://launchpad.net/~munozferna (Spanish)',
             'Gonzalo Testa https://launchpad.net/~gonzalogtesta (Spanish)',
             '"Kuvaly" https://launchpad.net/~kuvaly (Czech)',
             '"Lauren" https://launchpad.net/~lewakefi (French)',
             'James Maloy https://launchpad.net/~jamesmaloy (Spanish)',
             'John Y. Wu https://launchpad.net/~johnwuy (Traditional Chinese)',
             'Medina Colpaca https://launchpad.net/~medina-colpaca (Spanish)',
             'Milan Jensen https://launchpad.net/~milanjansen (Dutch)',
             '"MixCool" https://launchpad.net/~mixcool (German)',
             '"Rarulis" https://launchpad.net/~rarulis (French)',
             'Roberto Bondi https://launchpad.net/~bondi (Italian)',
             'Steven Sproat https://launchpad.net/~sproaty (Welsh, misc.)',
             '"tjalling" https://launchpad.net/~tjalling-taikie (Dutch)',
             'Wouter van Dijke https://launchpad.net/~woutervandijke (Dutch)']

        inf.Translators = t
        x = "http://www.launchpad.net/whyteboard"
        inf.WebSite = (x, x)
        inf.Licence = s
        wx.AboutBox(inf)


#----------------------------------------------------------------------


class WhyteboardApp(wx.App):
    def OnInit(self):
        """
        Load config file, apply translation, parse arguments and delete any
        temporary filse left over from an update
        """
        self.SetAppName("whyteboard")  # used to identify app in $HOME/

        path = os.path.join(get_home_dir(), "user.pref")
        config = ConfigObj(path, configspec=cfg.split("\n"))
        validator = Validator()
        config.validate(validator)

        for x in languages:
            if config['language'] == 'Welsh':
                self.locale = wx.Locale()
                self.locale.Init("Cymraeg", "cy", "cy_GB.utf8")
                break
            elif config['language'] == x[0]:
                nolog = wx.LogNull()
                self.locale = wx.Locale(x[1], wx.LOCALE_LOAD_DEFAULT)
                del nolog

        if not wx.Locale.IsOk(self.locale):
            wx.MessageBox("Error setting language to %s - reverting to English" % config['language'])
            config['language'] = 'English'
            config.write()
            self.locale = wx.Locale(wx.LANGUAGE_DEFAULT, wx.LOCALE_LOAD_DEFAULT)


        path = os.path.dirname(sys.argv[0])
        if path == "/usr/bin":
            path = "/usr/lib/whyteboard"  # simple workaround...
        langdir = os.path.join(path, 'locale')
        locale.setlocale(locale.LC_ALL, '')
        self.locale.AddCatalogLookupPathPrefix(langdir)
        self.locale.AddCatalog("whyteboard")

        self.frame = GUI(None, config)
        self.frame.Show(True)
        self.parse_args()
        self.delete_temp_files()
        return True


    def parse_args(self):
        """Forward the first command-line arg to gui.do_open()"""
        try:
            _file = os.path.abspath(sys.argv[1])
            if os.path.exists(_file):
                self.frame.do_open(_file)
        except IndexError:
            pass


    def delete_temp_files(self):
        """
        Delete temporary files from an update. Remove a backup exe, otherwise
        iterate over the current directory (where the backup files will be) and
        remove any that matches the random file extension
        """
        if self.frame.util.is_exe() and os.path.exists("wtbd-bckup.exe"):
            os.remove("wtbd-bckup.exe")
        else:
            path = self.frame.util.path[0]
            for f in os.listdir(path):
                if f.find(self.frame.util.backup_ext) is not -1:
                    os.remove(os.path.join(path, f))

#----------------------------------------------------------------------

def main():
    app = WhyteboardApp(redirect=False)
    app.MainLoop()

if __name__ == '__main__':
    main()
