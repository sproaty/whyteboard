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
This module implements the Whyteboard application.  It takes a Whyteboard class
and wraps it in a GUI with a menu/toolbar/statusbar; can save and load drawings,
clear the workspace, undo, redo, a simple history "replayer", allowing you to
have a replay of what you have drawn played back to you.

Also on the GUI is a panel for setting color and line thickness, with an
indicator that shows a drawing preview. On the right is a tabbed panel, allowing
the user to switch between viewing Thumbnails of each drawing's tab, or a Tree
of Notes that the user has inputted.
"""

from __future__ import with_statement

import os
import sys
import time
import locale
import webbrowser
import shutil

import wx
import wx.lib.newevent
import lib.flatnotebook as fnb
from wx.html import HtmlHelpController

from lib.pubsub import pub
from lib.configobj import ConfigObj
from lib.validate import Validator

import lib.icon
import meta
from whyteboard import Whyteboard
from tools import Image, Note, Text, Media, Highlighter
from utility import Utility, WhyteboardDropTarget

import event_ids as event_ids
from event_ids import *

from functions import get_home_dir
from dialogs import (History, ProgressDialog, Resize, UpdateDialog, MyPrintout,
                     ExceptionHook, ShapeViewer, Feedback)
from panels import ControlPanel, SidePanel, SheetsPopup
from preferences import Preferences


_ = wx.GetTranslation             # Define a translation string


#----------------------------------------------------------------------


class GUI(wx.Frame):
    """
    This class contains a ControlPanel, a Whyteboard frame and a SidePanel
    and manages their layout with a wx.BoxSizer.  A menu, toolbar and associated
    event handlers call the appropriate functions of other classes.
    """
    title = "Whyteboard " + meta.version
    LoadEvent, LOAD_DONE_EVENT = wx.lib.newevent.NewEvent()
    instances = 0

    def __init__(self, parent, config):
        """
        Initialise utility, status/menu/tool bar, tabs, ctrl panel + bindings.
        """
        wx.Frame.__init__(self, parent, title=_("Untitled")+" - " + self.title)
        ico = lib.icon.whyteboard.getIcon()
        self.SetIcon(ico)
        self.SetExtraStyle(wx.WS_EX_PROCESS_UI_UPDATES)
        self.util = Utility(self, config)
        self.file_drop = WhyteboardDropTarget(self)
        self.SetDropTarget(self.file_drop)
        self.statusbar = self.CreateStatusBar()
        self.printData = wx.PrintData()
        self.printData.SetPaperId(wx.PAPER_LETTER)
        self.printData.SetPrintMode(wx.PRINT_MODE_PRINTER)

        self.filehistory = wx.FileHistory(8)
        self.config = wx.Config("Whyteboard", style=wx.CONFIG_USE_LOCAL_FILE)
        self.filehistory.Load(self.config)

        self._oldhook = sys.excepthook
        sys.excepthook = ExceptionHook
        meta.find_transparent()  # important
        if meta.transparent:
            self.util.items.insert(1, Highlighter)

        self.can_paste = False
        if self.util.get_clipboard():
            self.can_paste = True
        self.toolbar = None
        self.menu = None
        self.process = None
        self.pid = None
        self.dialog = None
        self.convert_cancelled = False
        self.viewer = False  # Shape Viewer dialog open?
        self.help = None
        self.directory = None  # last opened directory
        self.make_toolbar()
        self.bar_shown = True  # slight ? performance optimisation
        self.find_help()
        self.__class__.instances += 1
        self.tab_count = 1  # instead of typing self.tabs.GetPageCount()
        self.tab_total = 1
        self.current_tab = 0
        self.closed_tabs = []  # [shapes - undo - redo - canvas_size] per tab
        self.hotkeys = []

        self.control = ControlPanel(self)
        self.tabs = fnb.FlatNotebook(self, style=fnb.FNB_X_ON_TAB | fnb.FNB_NO_X_BUTTON |
                                     fnb.FNB_VC8 | fnb.FNB_MOUSE_MIDDLE_CLOSES_TABS)
        self.board = Whyteboard(self.tabs, self)  # the active whyteboard tab
        self.panel = SidePanel(self)

        self.thumbs = self.panel.thumbs
        self.notes = self.panel.notes
        self.tabs.AddPage(self.board, _("Sheet")+" 1")
        box = wx.BoxSizer(wx.HORIZONTAL)  # position windows side-by-side
        box.Add(self.control, 0, wx.EXPAND)
        box.Add(self.tabs, 1, wx.EXPAND)
        box.Add(self.panel, 0, wx.EXPAND)
        self.SetSizer(box)
        self.SetSizeWH(800, 600)

        if os.name == "posix":
            self.board.SetFocus()  # makes EVT_CHAR_HOOK trigger
        if 'mac' != os.name:
            self.Maximize(True)

        self.count = 5  # used to update menu timings
        wx.UpdateUIEvent.SetUpdateInterval(50)
        wx.UpdateUIEvent.SetMode(wx.UPDATE_UI_PROCESS_SPECIFIED)
        self.board.update_thumb()
        self.do_bindings()
        self.update_panels(True)  # bold first items

        wx.CallAfter(self.make_menu)
        wx.CallAfter(self.UpdateWindowUI)


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
        shapes = wx.Menu()
        sheets = wx.Menu()
        _help = wx.Menu()
        _import = wx.Menu()
        recent = wx.Menu()
        self.filehistory.UseMenu(recent)
        self.filehistory.AddFilesToMenu()

        _import.Append(ID_IMPORT_IMAGE, _('&Image...'))
        _import.Append(ID_IMPORT_PDF, '&PDF...')
        _import.Append(ID_IMPORT_PS, 'Post&Script...')
        _import.Append(ID_IMPORT_PREF, _('P&references...'), _("Load in a Whyteboard preferences file"))
        _export = wx.Menu()
        _export.Append(ID_EXPORT, _("&Export Sheet...")+"\tCtrl+E", _("Export the current sheet to an image file"))
        _export.Append(ID_EXPORT_ALL, _("Export &All Sheets...")+"\tCtrl+Shift+E", _("Export every sheet to a series of image files"))
        _export.Append(ID_EXPORT_PDF, _('As &PDF...'), _("Export every sheet into a PDF file"))
        _export.Append(ID_EXPORT_PREF, _('P&references...'), _("Export your Whyteboard preferences file"))

        new = wx.MenuItem(_file, ID_NEW, _("New &Window")+"\tCtrl-N", _("Opens a new Whyteboard instance"))
        pnew = wx.MenuItem(edit, ID_PASTE_NEW, _("Paste to a &New Sheet")+"\tCtrl+Shift-V", _("Paste from your clipboard into a new sheet"))
        undo_sheet = wx.MenuItem(edit, ID_UNDO_SHEET, _("&Undo Last Closed Sheet")+"\tCtrl+Shift-T", _("Undo the last closed sheet"))

        if os.name != "nt":
            new.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_NEW, wx.ART_MENU))
            pnew.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_PASTE, wx.ART_MENU))
            undo_sheet.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_UNDO, wx.ART_MENU))

        _file.AppendItem(new)
        _file.Append(wx.ID_NEW, _("&New Sheet")+"\tCtrl-T", _("Add a new sheet"))
        _file.Append(wx.ID_OPEN, _("&Open...")+"\tCtrl-O", _("Load a Whyteboard save file, an image or convert a PDF/PS document"))
        _file.AppendMenu(-1, _('Open &Recent'), recent, _("Recently Opened Files"))
        _file.AppendSeparator()
        _file.Append(wx.ID_SAVE, _("&Save")+"\tCtrl+S", _("Save the Whyteboard data"))
        _file.Append(wx.ID_SAVEAS, _("Save &As...")+"\tCtrl+Shift+S", _("Save the Whyteboard data in a new file"))
        _file.AppendSeparator()
        _file.AppendMenu(-1, _('&Import File'), _import, _("Import various file types"))
        _file.AppendMenu(-1, _('&Export File'), _export, _("Export your data files as images/PDFs"))
        _file.Append(ID_RELOAD_PREF, _('Re&load Preferences'), _("Reload your preferences file"))
        _file.AppendSeparator()
        _file.Append(wx.ID_PRINT_SETUP, _("Page Set&up"), _("Set up the page for printing"))
        _file.Append(wx.ID_PREVIEW_PRINT, _("Print Pre&view"), _("View a preview of the page to be printed"))
        _file.Append(wx.ID_PRINT, _("&Print...")+"\tCtrl+P", _("Print the current page"))
        _file.AppendSeparator()
        _file.Append(wx.ID_EXIT, _("&Quit")+"\tAlt+F4", _("Quit Whyteboard"))

        edit.Append(wx.ID_UNDO, _("&Undo")+"\tCtrl+Z", _("Undo the last operation"))
        edit.Append(wx.ID_REDO, _("&Redo")+"\tCtrl+Y", _("Redo the last undone operation"))
        edit.AppendSeparator()
        edit.Append(wx.ID_COPY, _("&Copy")+"\tCtrl+C", _("Copy a Bitmap Selection region"))
        edit.Append(wx.ID_PASTE, _("&Paste")+"\tCtrl+V", _("Paste text or an image from your clipboard into Whyteboard"))
        edit.AppendItem(pnew)
        edit.AppendSeparator()
        edit.Append(wx.ID_PREFERENCES, _("Prefere&nces"), _("Change your preferences"))

        view.Append(ID_SHAPE_VIEWER, _("&Shape Viewer...")+"\tF3", _("View and edit the shapes' drawing order"))
        view.Append(ID_HISTORY, _("&History Viewer...")+"\tCtrl+H", _("View and replay your drawing history"))
        view.AppendSeparator()
        self.showtool = view.Append(ID_TOOLBAR, " "+ _("&Toolbar"), _("Show and hide the toolbar"), kind=wx.ITEM_CHECK)
        self.showstat = view.Append(ID_STATUSBAR, " "+_("&Status Bar"), _("Show and hide the status bar"), kind=wx.ITEM_CHECK)
        self.showprev = view.Append(ID_TOOL_PREVIEW, " "+_("Tool &Preview"), _("Show and hide the tool preview"), kind=wx.ITEM_CHECK)
        self.showcolour = view.Append(ID_COLOUR_GRID, " "+_("&Color Grid"), _("Show and hide the color grid"), kind=wx.ITEM_CHECK)
        view.AppendSeparator()
        view.Append(ID_FULLSCREEN, " "+_("&Full Screen")+"\tF11", _("View Whyteboard in full-screen mode"), kind=wx.ITEM_CHECK)

        shapes.Append(ID_MOVE_UP, _("Move Shape &Up")+"\tCtrl-Up", _("Moves the currently selected shape up"))
        shapes.Append(ID_MOVE_DOWN, _("Move Shape &Down")+"\tCtrl-Down", _("Moves the currently selected shape down"))
        shapes.Append(ID_MOVE_TO_TOP, _("Move Shape To &Top")+"\tCtrl-Shift-Up", _("Moves the currently selected shape to the top"))
        shapes.Append(ID_MOVE_TO_BOTTOM, _("Move Shape To &Bottom")+"\tCtrl-Shift-Down", _("Moves the currently selected shape to the bottom"))
        shapes.AppendSeparator()
        shapes.Append(wx.ID_DELETE, _("&Delete Shape")+"\tDelete", _("Delete the currently selected shape"))
        shapes.Append(ID_DESELECT, _("&Deselect Shape")+"\tCtrl-D", _("Deselects the currently selected shape"))
        shapes.Append(ID_SWAP_COLOURS, _("Swap &Colors"),  _("Swaps the foreground and background colors"))
        shapes.AppendCheckItem(ID_TRANSPARENT, " "+_("T&ransparent"), _("Toggles the selected shape's transparency"))

        sheets.Append(wx.ID_CLOSE, _("Re&move Sheet")+"\tCtrl+W", _("Close the current sheet"))
        sheets.Append(ID_RENAME, _("&Rename Sheet...")+"\tF2", _("Rename the current sheet"))
        sheets.Append(ID_RESIZE, _("Resi&ze Canvas...")+"\tCtrl+R", _("Change the canvas' size"))
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

        _help.Append(wx.ID_HELP, _("&Contents")+"\tF1", _("View Whyteboard's help documents"))
        _help.AppendSeparator()
        _help.Append(ID_UPDATE, _("Check for &Updates...")+"\tF12", _("Search for updates to Whyteboard"))
        _help.Append(ID_REPORT_BUG, _("&Report a Problem"), _("Report any bugs or issues with Whyteboard"))
        _help.Append(ID_TRANSLATE, _("&Translate Whyteboard"), _("Translate Whyteboard to your language"))
        _help.Append(ID_FEEDBACK, _("Send &Feedback"), _("Send feedback directly to Whyteboard's developer"))
        _help.AppendSeparator()
        _help.Append(wx.ID_ABOUT, _("&About"), _("View information about Whyteboard"))
        self.menu.Append(_file, _("&File"))
        self.menu.Append(edit, _("&Edit"))
        self.menu.Append(view, _("&View"))
        self.menu.Append(shapes, _("Sha&pes"))
        self.menu.Append(sheets, _("&Sheets"))
        self.menu.Append(_help, _("&Help"))
        self.SetMenuBar(self.menu)
        self.menu.Enable(wx.ID_PASTE, self.can_paste)
        self.menu.Enable(ID_PASTE_NEW, self.can_paste)

        # Note: using the import "functions" module here to get the ID
        keys = ['toolbar', 'statusbar', 'tool_preview', 'colour_grid']
        for x in keys:
            if self.util.config[x]:
                view.Check(getattr(event_ids, "ID_" + x.upper()), True)
            else:
                getattr(self, "on_" + x)(None, False)


    def do_bindings(self):
        """
        Performs event binding.
        """
        self.Bind(wx.EVT_CLOSE, self.on_exit)
        self.Bind(fnb.EVT_FLATNOTEBOOK_PAGE_CHANGED, self.on_change_tab)
        self.Bind(fnb.EVT_FLATNOTEBOOK_PAGE_DROPPED, self.on_drop_tab)
        self.Bind(fnb.EVT_FLATNOTEBOOK_PAGE_CONTEXT_MENU, self.tab_popup)
        self.Bind(wx.EVT_END_PROCESS, self.on_end_process)  # end conversion
        self.Bind(self.LOAD_DONE_EVENT, self.on_done_load)
        self.Bind(wx.EVT_CHAR_HOOK, self.hotkey)
        self.Bind(wx.EVT_MENU_RANGE, self.on_file_history, id=wx.ID_FILE1, id2=wx.ID_FILE9)

        topics = {'shape.add': self.shape_add, 
                  'shape.selected': self.shape_selected,
                  'board.capture_mouse': self.capture_mouse,
                  'board.release_mouse': self.release_mouse,}
        [pub.subscribe(value, key) for key, value in topics.items()]


        # idle event handlers
        ids = [ID_NEXT, ID_PREV, ID_UNDO_SHEET, ID_MOVE_UP, ID_DESELECT,
               ID_MOVE_DOWN, ID_MOVE_TO_TOP, ID_MOVE_TO_BOTTOM, wx.ID_COPY,
               wx.ID_PASTE, wx.ID_UNDO, wx.ID_REDO, wx.ID_DELETE, ID_TRANSPARENT,
               ID_SWAP_COLOURS]
        [self.Bind(wx.EVT_UPDATE_UI, self.update_menus, id=x) for x in ids]

        # hotkeys
        self.hotkeys = [x.hotkey for x in self.util.items]
        ac = []

        # Need to bind each item's hotkey to trigger change tool, passing its ID
        # (position + 1 in the list, basically)
        if os.name == "nt":
            for x, item in enumerate(self.util.items):
                blah = lambda evt, y=x + 1: self.on_change_tool(evt, y)
                _id = wx.NewId()
                ac.append((wx.ACCEL_NORMAL, ord(item.hotkey.upper()), _id))
                self.Bind(wx.EVT_MENU, blah, id=_id)

        tbl = wx.AcceleratorTable(ac)
        self.SetAcceleratorTable(tbl)


        # import sub-menu bindings
        ids = {'pdf': ID_IMPORT_PDF, 'ps': ID_IMPORT_PS, 'img': ID_IMPORT_IMAGE}
        [self.Bind(wx.EVT_MENU, lambda evt, text = key: self.on_open(evt, text),
                    id=ids[key]) for key in ids]

        # other menu bindings
        functs = ["new_win", "new_tab", "open",  "close_tab", "save", "save_as", "export", "export_all", "page_setup", "print_preview", "print", "exit", "undo", "redo", "undo_tab",
                  "copy", "paste", "delete_shape", "preferences", "paste_new", "history", "resize", "fullscreen", "toolbar", "statusbar", "prev", "next", "clear", "clear_all",
                  "clear_sheets", "clear_all_sheets", "rename", "help", "update", "translate", "report_bug", "about", "export_pdf", "import_pref", "export_pref", "shape_viewer", "move_up",
                  "move_down", "move_top", "move_bottom", "deselect", "reload_preferences", "tool_preview", "colour_grid", "feedback", "transparent", "swap_colours"]

        IDs = [ID_NEW, wx.ID_NEW, wx.ID_OPEN, wx.ID_CLOSE, wx.ID_SAVE, wx.ID_SAVEAS, ID_EXPORT, ID_EXPORT_ALL, wx.ID_PRINT_SETUP, wx.ID_PREVIEW_PRINT, wx.ID_PRINT, wx.ID_EXIT, wx.ID_UNDO,
               wx.ID_REDO, ID_UNDO_SHEET, wx.ID_COPY, wx.ID_PASTE, wx.ID_DELETE, wx.ID_PREFERENCES, ID_PASTE_NEW, ID_HISTORY, ID_RESIZE, ID_FULLSCREEN, ID_TOOLBAR, ID_STATUSBAR,
               ID_PREV, ID_NEXT, wx.ID_CLEAR, ID_CLEAR_ALL, ID_CLEAR_SHEETS, ID_CLEAR_ALL_SHEETS, ID_RENAME, wx.ID_HELP, ID_UPDATE, ID_TRANSLATE, ID_REPORT_BUG, wx.ID_ABOUT, ID_EXPORT_PDF,
               ID_IMPORT_PREF, ID_EXPORT_PREF, ID_SHAPE_VIEWER, ID_MOVE_UP, ID_MOVE_DOWN, ID_MOVE_TO_TOP, ID_MOVE_TO_BOTTOM, ID_DESELECT, ID_RELOAD_PREF, ID_TOOL_PREVIEW, ID_COLOUR_GRID,
               ID_FEEDBACK, ID_TRANSPARENT, ID_SWAP_COLOURS]

        for name, _id in zip(functs, IDs):
            method = getattr(self, "on_"+ name)  # self.on_*
            self.Bind(wx.EVT_MENU, method, id=_id )


    def make_toolbar(self):
        """
        Creates a toolbar, Pythonically :D
        Move to top/up/down/bottom must be created with a custom bitmap.
        """
        self.toolbar = self.CreateToolBar()
        _move = [ID_MOVE_TO_TOP, ID_MOVE_UP, ID_MOVE_DOWN, ID_MOVE_TO_BOTTOM]
        move = _("Move Shape")+" "

        ids = [wx.ID_NEW, wx.ID_OPEN, wx.ID_SAVE, wx.ID_COPY, wx.ID_PASTE,
               wx.ID_UNDO, wx.ID_REDO, wx.ID_DELETE]

        arts = [wx.ART_NEW, wx.ART_FILE_OPEN, wx.ART_FILE_SAVE, wx.ART_COPY,
                wx.ART_PASTE, wx.ART_UNDO, wx.ART_REDO, wx.ART_DELETE]
        tips = [_("New Sheet"), _("Open a File"), _("Save Drawing"), _("Copy a Bitmap Selection"),
                _("Paste an Image/Text"), _("Undo the Last Action"), _("Redo the Last Undone Action"),
                _("Delete the currently selected shape"), move + _("To Top"), move + _("Up"),
                move + _("Down"), move + _("To Bottom")]

        ids.extend(_move)
        arts.extend(_move)
        path = os.path.join(self.util.get_path(), "images", "icons", "")
        icons = ["top", "up", "down", "bottom"]

        bmps = {}
        for icon, _id in zip(icons, _move):
            bmps[_id] = wx.Bitmap(path + "move-" + icon +"-small.png")

        # add tools, add a separator and bind paste/undo/redo for UI updating
        x = 0
        for _id, art_id, tip in zip(ids, arts, tips):

            if _id in _move:
                art = bmps[_id]
            else:
                art = wx.ArtProvider.GetBitmap(art_id, wx.ART_TOOLBAR)

            self.toolbar.AddSimpleTool(_id, art, tip)

            if x == 2 or x == 6:
                self.toolbar.AddSeparator()
            x += 1
        self.toolbar.EnableTool(wx.ID_PASTE, self.can_paste)
        self.toolbar.Realize()


    def shape_selected(self, shape):
        """
        Shape getting selected (by Select tool)
        """
        x = self.board.shapes.index(shape)
        self.board.shapes.pop(x)
        self.board.redraw_all()  # hide 'original'
        self.board.shapes.insert(x, shape)
        shape.draw(self.board.get_dc(), False)  # draw 'new'

        ctrl, menu = True, True
        if not shape.background == wx.TRANSPARENT:
            ctrl, menu = False, False

        self.control.transparent.SetValue(ctrl)
        self.menu.Check(ID_TRANSPARENT, menu)


    def release_mouse(self):
        self.board.release_mouse()
        
    def capture_mouse(self):
        self.board.capture_mouse()
        
    def shape_add(self, shape):
        self.board.add_shape(shape)
        #self.update_shape_viewer()


    def update_shape_viewer(self):
        if self.viewer:
            self.viewer.shapes = list(self.board.shapes)
            self.viewer.populate()


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
        now = time.localtime(time.time())
        now = time.strftime("%Y-%m-%d-%H-%M-%S")

        if self.util.filename:
            now = self.util.filename

        dlg = wx.FileDialog(self, _("Save Whyteboard As..."), os.getcwd(),
                style=wx.SAVE | wx.OVERWRITE_PROMPT,  defaultFile=now,
                wildcard=_("Whyteboard file ")+"(*.wtbd)|*.wtbd")
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
        wc = meta.dialog_wildcard
        if text == "img":
            wc = wc[ wc.find(_("Image Files")) : wc.find("|PDF") ]  # image to page
        elif text:
            wc = wc[ wc.find("PDF") :]  # page descriptions

        _dir = ""
        if self.directory:
            _dir = self.directory

        dlg = wx.FileDialog(self, _("Open file..."), style=wx.OPEN, wildcard=wc,
                             defaultDir=_dir)
        dlg.SetFilterIndex(0)

        if dlg.ShowModal() == wx.ID_OK:
            name = dlg.GetPath()

            if name.endswith(".wtbd"):
                self.util.prompt_for_save(self.do_open, args=[name])
            else:
                self.do_open(name)
        else:
            dlg.Destroy()


    def do_open(self, path):
        """
        Updates the appropriate variables in the utility file class and loads
        the selected file.
        """
        self.directory = os.path.dirname(path)
        self.filehistory.AddFileToHistory(path)
        self.filehistory.Save(self.config)
        self.config.Flush()

        if path.endswith(".wtbd"):
            self.util.load_wtbd(path)
        else:
            self.util.temp_file = path
            self.util.load_file()


    def on_export_pdf(self, event=None):
        """
        Exports the all the sheets as a PDF. Must first export all sheets as
        imgages, convert to PDF (displaying a progress bar) and then remove
        all the temporary files
        """
        if not self.util.im_location:
            self.util.prompt_for_im()
        if not self.util.im_location:
            return
        filename = ""

        dlg = wx.FileDialog(self, _("Export data to..."), style=wx.SAVE |
                             wx.OVERWRITE_PROMPT, wildcard="PDF (*.pdf)|*.pdf")
        if dlg.ShowModal() == wx.ID_OK:
            filename = dlg.GetPath()
            ext = os.path.splitext(filename)[1]
            if not ext:  # no file extension
                filename += '.pdf'
            elif ext != ".pdf":
                wx.MessageBox(_("Invalid filetype to export as:")+" .%s" % ext,
                              _("Invalid filetype"))
                return

        dlg.Destroy()
        if filename:
            names = []
            board = self.board
            for x in range(self.tab_count):
                self.board = self.tabs.GetPage(x)
                name = "%s-tempblahhahh-%s-.jpg" % (filename, x)
                names.append(name)
                self.util.export(name)
            self.board = board

            self.process = wx.Process(self)
            files = ""
            for x in names:
                files += '"%s" ' % x  # quote filenames for windows

            cmd = '%s -define pdf:use-trimbox=true %s"%s"' % (self.util.im_location.decode("utf-8"), files, filename)
            self.pid = wx.Execute(cmd,  wx.EXEC_ASYNC, self.process)
            self.dialog = ProgressDialog(self, _("Converting..."))
            self.dialog.ShowModal()

            [os.remove(x) for x in names]



    def on_export(self, event=None):
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
            for x in range(self.tab_count):
                self.board = self.tabs.GetPage(x)
                self.util.export("%s-%s%s" % (name[0], x + 1, name[1]))
            self.board = board


    def on_export_pref(self, event=None):
        """Exports the user's preferences."""
        if not os.path.exists(self.util.config.filename):
            wx.MessageBox(_("Export Error"), _("You have not set any preferences"))
            return
        filename = ""
        wc = _("Whyteboard Preference Files")+" (*.pref)|*.pref"

        dlg = wx.FileDialog(self, _("Export preferences to..."), style=wx.SAVE |
                             wx.OVERWRITE_PROMPT, wildcard=wc)
        if dlg.ShowModal() == wx.ID_OK:
            filename = dlg.GetPath()
            ext = os.path.splitext(filename)[1]

            if not ext:
                filename += ".pref"
            shutil.copy(os.path.join(get_home_dir(), "user.pref"), filename)


    def on_import_pref(self, event=None):
        """
        Imports the preference file. Backsup the user's current prefernce file
        into a directory, with a timestamp on the filename
        """
        wc =  _("Whyteboard Preference Files")+" (*.pref)|*.pref"

        dlg = wx.FileDialog(self, _("Import Preferences From..."), get_home_dir(),
                            style=wx.OPEN, wildcard=wc)

        if dlg.ShowModal() == wx.ID_OK:
            filename = dlg.GetPath()

            config = ConfigObj(filename, configspec=meta.config_scheme.split("\n"))
            validator = Validator()
            config.validate(validator)
            _dir = os.path.join(get_home_dir(), "pref-bkup")


            if not os.path.isdir(_dir):
                os.makedirs(_dir)

            home =  os.path.join(get_home_dir(), "user.pref")
            if os.path.exists(home):
                stamp =  time.strftime("%d-%b-%Y_%Hh-%Mm_%Ss", time.gmtime())

                os.rename(home, os.path.join(_dir, stamp+".user.pref"))
            pref = Preferences(self)
            pref.config = config
            pref.config.filename = home
            pref.on_okay()



    def on_reload_preferences(self, event):
        home =  os.path.join(get_home_dir(), "user.pref")
        if os.path.exists(home):
            config = ConfigObj(home, configspec=meta.config_scheme.split("\n"))
            validator = Validator()
            config.validate(validator)
            pref = Preferences(self)
            pref.config = config
            pref.config.filename = home
            pref.on_okay()
        else:
            wx.MessageBox(_("No preferences file to reload"))


    def export_prompt(self):
        """Find out the filename to save to"""
        val = None  # return value
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
            if not _name in meta.types[2:]:
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
        """
        Opens a new tab, selects it, creates a new thumbnail and tree item
        name: unique name, sent by PDF convert/load file.
        wb: Passed by undo_tab to ensure the tab total is correct
        """
        if not wb:
            self.tab_total += 1
        if not name:
            name = _("Sheet")+" %s" % self.tab_total

        self.tab_count += 1
        self.thumbs.new_thumb(name=name)
        self.notes.add_tab(name)
        self.tabs.AddPage(Whyteboard(self.tabs, self), name)

        self.update_panels(False)  # unhighlight current
        self.thumbs.thumbs[self.current_tab].current = True

        self.current_tab = self.tab_count - 1
        self.tabs.SetSelection(self.current_tab)  # fires on_change_tab
        self.on_change_tab()


    def on_change_tab(self, event=None):
        """Updates tab vars, scrolls thumbnails and selects tree node"""
        self.board = self.tabs.GetCurrentPage()
        self.update_panels(False)
        self.current_tab = self.tabs.GetSelection()

        self.update_panels(True)
        self.thumbs.thumbs[self.current_tab].update()
        self.thumbs.ScrollChildIntoView(self.thumbs.thumbs[self.current_tab])
        self.control.change_tool()

        if self.notes.tabs:
            tree_id = self.notes.tabs[self.current_tab]
            self.notes.tree.SelectItem(tree_id, True)
        self.update_shape_viewer()


    def on_drop_tab(self, event):
        """
        Update the thumbs/notes so that they're poiting to the new tab position.
        Show a progress dialog, as all thumbnails must be updated.
        """
        if event.GetSelection() == event.GetOldSelection():
            return

        self.dialog = ProgressDialog(self, _("Loading..."), 5)
        self.dialog.Show()
        self.on_change_tab()

        # Update thumbnails
        for x in range(self.tab_count):
            self.thumbs.text[x].SetLabel(self.tabs.GetPageText(x))

        pub.sendMessage('sheet.move', event=event, tab_count=self.tab_count)
        self.on_done_load()
        wx.MilliSleep(100)  # try and stop user dragging too many tabs quickly
        wx.SafeYield()
        self.update_shape_viewer()


    def update_panels(self, select):
        """Updates thumbnail panel's text"""
        pub.sendMessage('thumbs.text.highlight', tab=self.current_tab,
                        select=select)


    def on_close_tab(self, event=None):
        """
        Closes the current tab (if there are any to close).
        Adds the 3 lists from the Whyteboard to a list inside the undo tab list.
        """
        if not self.tab_count - 1:  # must have at least one sheet open
            return
        if len(self.closed_tabs) == self.util.config['undo_sheets']:
            del self.closed_tabs[self.util.config['undo_sheets'] - 1]

        self.notes.remove_tab(self.current_tab)
        self.thumbs.remove(self.current_tab)

        for x in self.board.medias:
            x.remove_panel()

        board = self.board
        item = [board.shapes, board.undo_list, board.redo_list, board.area,
                self.tabs.GetPageText(self.current_tab), board.medias]

        self.closed_tabs.append(item)
        self.tab_count -= 1

        if os.name == "posix":
            self.tabs.RemovePage(self.current_tab)
        else:
            self.tabs.DeletePage(self.current_tab)

        self.on_change_tab()  # updates self.board



    def on_undo_tab(self, event=None):
        """
        Undoes the last closed tab from the list.
        Re-creates the board from the saved shapes/undo/redo lists
        """
        if not self.closed_tabs:
            return
        board = self.closed_tabs.pop()

        self.on_new_tab(name=board[4], wb=True)
        self.board.shapes = board[0]
        self.board.undo_list = board[1]
        self.board.redo_list = board[2]
        self.board.medias = board[5]

        for x in self.board.medias:
            x.board = self.board
            x.make_panel()

        for shape in self.board.shapes:
            shape.board = self.board
            if isinstance(shape, Note):
                pub.sendMessage('note.add', note=shape)

        wx.Yield()  # doesn't draw thumbnail otherwise...
        self.board.resize_canvas(board[3])
        self.board.redraw_all(True)
        self.update_shape_viewer()


    def on_rename(self, event=None, sheet=None):
        if not sheet:
            sheet = self.current_tab
        dlg = wx.TextEntryDialog(self, _("Rename this sheet to:"), _("Rename sheet"))
        dlg.SetValue(self.tabs.GetPageText(sheet))

        if dlg.ShowModal() == wx.ID_CANCEL:
            dlg.Destroy()
        else:
            val = dlg.GetValue()
            if val:
                self.tabs.SetPageText(sheet, val)
                pub.sendMessage('sheet.rename', _id=sheet, text=val)


    def on_delete_shape(self, event=None):
        self.board.delete_selected()
        self.update_shape_viewer()

    def on_deselect(self, event=None):
        self.board.deselect()


    def update_menus(self, event):
        """
        Enables/disables the undo/redo/next/prev button as appropriate.
        It is called every 65ms and uses a counter to update the clipboard check
        less often than the 65ms, as it's too performance intense
        """
        if not self.board:
            return
        _id = event.GetId()

        if _id == wx.ID_PASTE:  # check this less frequently, possibly expensive
            self.count += 1
            if self.count == 6:
                self.can_paste = False

            if not wx.TheClipboard.IsOpened():
                wx.TheClipboard.Open()
                success = wx.TheClipboard.IsSupported(wx.DataFormat(wx.DF_BITMAP))
                success2 = wx.TheClipboard.IsSupported(wx.DataFormat(wx.DF_TEXT))
                wx.TheClipboard.Close()
                if success or success2:
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
            board = self.board
            if _id == wx.ID_REDO and board.redo_list:
                do = True
            elif _id == wx.ID_UNDO and board.undo_list:
                do = True
            elif _id == ID_PREV and self.current_tab:
                do = True
            elif (_id == ID_NEXT and self.tab_count > 1 and
                  self.current_tab + 1 < self.tab_count):
                do = True
            elif _id == ID_UNDO_SHEET and self.closed_tabs:
                do = True
            elif _id in [wx.ID_DELETE, ID_DESELECT] and board.selected:
                do = True
            elif _id == ID_MOVE_UP and board.check_move("up"):
                do = True
            elif _id == ID_MOVE_DOWN and board.check_move("down"):
                do = True
            elif _id == ID_MOVE_TO_TOP and board.check_move("top"):
                do = True
            elif _id == ID_MOVE_TO_BOTTOM and board.check_move("bottom"):
                do = True
            elif (_id == ID_TRANSPARENT and board.selected
                  and not isinstance(board.selected, (Media, Image, Text))):
                do = True
            elif (_id == ID_SWAP_COLOURS and board.selected
                  and not self.board.selected.background == wx.TRANSPARENT
                  and not isinstance(board.selected, (Media, Image, Text))):
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


    def on_paste(self, event=None, ignore=False):
        """
        Grabs the image from the clipboard and places it on the panel
        Ignore is used when pasting into a new sheet
        """
        data = self.util.get_clipboard()
        if not data:
            return

        x, y = 0, 0
        if not ignore:
            x, y = self.board.ScreenToClient(wx.GetMousePosition())
            if x < 0 or y < 0:
                x = 0
                y = 0
            if x > self.board.area[0] or y > self.board.area[1]:
                x = 0
                y = 0

            x, y = self.board.CalcUnscrolledPosition(x, y)

        if isinstance(data, wx.TextDataObject):
            shape = Text(self.board, self.util.colour, 1)
            shape.text = data.GetText()

            self.board.shape = shape
            shape.left_down(x, y)
            shape.left_up(x, y)
            self.board.text = None
            self.board.change_current_tool()
            self.board.redraw_all(True)
        else:
            bmp = data.GetBitmap()
            shape = Image(self.board, bmp, None)
            shape.left_down(x, y)
            wx.Yield()
            self.board.redraw_all(True)
            if ignore:
                self.board.resize_canvas((bmp.GetWidth(), bmp.GetHeight()))


    def on_paste_new(self, event):
        """ Pastes the image into a new tab """
        self.on_new_tab()
        self.on_paste(ignore=True)


    def on_fullscreen(self, event=None):
        """ Toggles fullscreen """
        flag = (wx.FULLSCREEN_NOBORDER | wx.FULLSCREEN_NOCAPTION |
               wx.FULLSCREEN_NOSTATUSBAR)
        self.ShowFullScreen(not self.IsFullScreen(), flag)

    def on_change_tool(self, event, _id):
        self.control.change_tool(_id=_id)


    def hotkey(self, event=None):
        """
        Processes a hotkey (escape / home / end / page up / page down)
        """
        if os.name == "posix":
            for x, key in enumerate(self.hotkeys):

                if (event.GetKeyCode() == ord(key)
                    or event.GetKeyCode() == ord(key.upper())):
                    self.control.change_tool(_id=x + 1)
                    return

        if event.GetKeyCode() == wx.WXK_ESCAPE:  # close fullscreen
            if self.board.selected:
                self.board.deselect()
                return
            if self.IsFullScreen():
                flag = (wx.FULLSCREEN_NOBORDER | wx.FULLSCREEN_NOCAPTION |
                   wx.FULLSCREEN_NOSTATUSBAR)
                self.ShowFullScreen(False, flag)
                menu = self.menu.FindItemById(ID_FULLSCREEN)
                menu.Check(False)
        elif event.GetKeyCode() == wx.WXK_HOME:
            if event.ControlDown():
                self.board.Scroll(-1, 0)
            else:
                self.board.Scroll(0, -1)
        elif event.GetKeyCode() == wx.WXK_END:
            if event.ControlDown():
                self.board.Scroll(-1, self.board.area[1])
            else:
                self.board.Scroll(self.board.area[0], -1)

        elif event.GetKeyCode() in [wx.WXK_PAGEUP, wx.WXK_PAGEDOWN]:
            x, y = self.board.GetViewStart()
            x2, y2 = self.board.GetClientSizeTuple()
            if event.GetKeyCode() == wx.WXK_PAGEUP:
                self.board.Scroll(-1, y - y2)
            else:
                self.board.Scroll(-1, y + y2)
        else:
            event.Skip()   # propogate


    def toggle_view(self, menu, view, force=None):
        """Menu: MenuItem to check/enable/disable, view: Control to show/hide"""
        if menu.IsChecked() or force:
            view.Show()
            menu.Check(True)
        else:
            view.Hide()
            menu.Check(False)
        if force is False:
            view.Hide()
            menu.Check(False)
        self.SendSizeEvent()


    def on_toolbar(self, event=None, force=None):
        self.toggle_view(self.showtool, self.toolbar, force)

    def on_tool_preview(self, event=None, force=None):
        self.toggle_view(self.showprev, self.control.preview, force)


    def on_statusbar(self, event=None, force=None):
        self.bar_shown = False
        if self.showstat.IsChecked() or force:
            self.bar_shown = True

        self.toggle_view(self.showstat, self.statusbar, force)


    def on_colour_grid(self, event=None, force=None):
        """ugly, has to show/hide an item from a sizer, not a panel"""
        if self.showcolour.IsChecked() or force:
            self.control.control_sizer.Show(self.control.grid, True)
            self.showcolour.Check(True)
        else:
            self.control.control_sizer.Hide(self.control.grid)
            self.showcolour.Check(False)
        if force is False:
            self.control.control_sizer.Hide(self.control.grid)
            self.showcolour.Check(False)

        self.control.pane.Layout()
        self.control.preview.Refresh()


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


    def on_file_history(self, evt):
        """ Handle file load from the recent files menu """
        num = evt.GetId() - wx.ID_FILE1
        path = self.filehistory.GetHistoryFile(num)
        if not os.path.exists(path):
            wx.MessageBox(_("File not found"))
            self.filehistory.RemoveFileFromHistory(num)
            return
        self.filehistory.AddFileToHistory(path)  # move up the list

        if path.endswith(".wtbd"):
            self.util.prompt_for_save(self.do_open, args=[path])
        else:
            self.do_open(path)


    def on_exit(self, event=None):
        """ Ask to save, quit or cancel if the user hasn't saved. """
        self.util.prompt_for_save(self.Destroy)


    def tab_popup(self, event):
        """ Pops up the tab context menu. """
        self.PopupMenu(SheetsPopup(self, self, event.GetSelection()))

    def on_undo(self, event=None):
        """ Calls undo on the active tab and updates the menus """
        self.board.undo()
        self.update_shape_viewer()

    def on_redo(self, event=None):
        """ Calls redo on the active tab and updates the menus """
        self.board.redo()
        self.update_shape_viewer()

    def on_move_top(self, event=None):
        self.board.move_top(self.board.selected)
        self.update_shape_viewer()

    def on_move_bottom(self, event=None):
        self.board.move_bottom(self.board.selected)
        self.update_shape_viewer()

    def on_move_up(self, event=None):
        self.board.move_up(self.board.selected)
        self.update_shape_viewer()

    def on_move_down(self, event=None):
        self.board.move_down(self.board.selected)
        self.update_shape_viewer()

    def on_prev(self, event=None):
        """ Changes to the previous sheet """
        self.tabs.SetSelection(self.current_tab - 1)
        self.on_change_tab()

    def on_next(self, event=None):
        """ Changes to the next sheet """
        self.tabs.SetSelection(self.current_tab + 1)
        self.on_change_tab()

    def on_clear(self, event=None):
        """ Clears current sheet's drawings, except images. """
        self.board.clear(keep_images=True)
        self.update_shape_viewer()

    def on_clear_all(self, event=None):
        """ Clears current sheet """
        self.board.clear()
        self.update_shape_viewer()

    def on_clear_sheets(self, event=None):
        """ Clears all sheets' drawings, except images. """
        for tab in range(self.tab_count):
            self.tabs.GetPage(tab).clear(keep_images=True)
        self.update_shape_viewer()


    def on_clear_all_sheets(self, event=None):
        """ Clears all sheets ***"""
        for tab in range(self.tab_count):
            self.tabs.GetPage(tab).clear()
        self.update_shape_viewer()


    def on_refresh(self):
        self.thumbs.update_all()

    def on_transparent(self, event=None):
        self.board.toggle_transparent()

    def on_swap_colours(self, event=None):
        self.board.swap_colours()


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
        preview = wx.PrintPreview(printout, printout2, data)

        if not preview.Ok():
            wx.MessageBox(_("There was a problem printing.\nPerhaps your current printer is not set correctly?"),
              _("Printing Error"))
            return

        pfrm = wx.PreviewFrame(preview, self, _("Print Preview"))
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


    def open_url(self, url):
        wx.BeginBusyCursor()
        webbrowser.open_new_tab(url)
        wx.CallAfter(wx.EndBusyCursor)

    def show_dialog(self, _class, modal=True):
        if modal:
            _class.ShowModal()
        else:
            _class.Show()

    def on_translate(self, event):
        self.open_url("https://translations.launchpad.net/whyteboard")

    def on_report_bug(self, event):
        self.open_url("https://bugs.launchpad.net/whyteboard")

    def on_resize(self, event=None):
        self.show_dialog(Resize(self))

    def on_shape_viewer(self, event=None):
        if not self.viewer:
            dlg = ShapeViewer(self)
            self.show_dialog(dlg, False)
            self.viewer = dlg

    def on_preferences(self, event=None):
        self.show_dialog(Preferences(self))

    def on_update(self, event=None):
        self.show_dialog(UpdateDialog(self))

    def on_history(self, event=None):
        self.show_dialog(History(self))

    def on_feedback(self, event):
        self.show_dialog(Feedback(self), False)


    def find_help(self):
        """Locate the help files, update self.help var"""
        _file = os.path.join(self.util.get_path(), 'whyteboard-help', 'whyteboard.hhp')

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
                self.help.DisplayIndex()
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
        inf.Version = meta.version
        inf.Copyright = "(C) 2009 Steven Sproat"
        inf.Description = _("A simple whiteboard and PDF annotator")
        inf.Developers = ["Steven Sproat <sproaty@gmail.com>"]
        inf.Translators = meta.translators
        x = "http://www.launchpad.net/whyteboard"
        inf.WebSite = (x, x)
        with open(os.path.join(self.util.get_path(), "LICENSE.txt")) as f:
            inf.Licence = f.read()

        wx.AboutBox(inf)

#----------------------------------------------------------------------



class WhyteboardApp(wx.App):
    def OnInit(self):
        """
        Load config file, apply translation, parse arguments and delete any
        temporary filse left over from an update
        """
        wx.SetDefaultPyEncoding("utf-8")
        self.SetAppName("whyteboard")  # used to identify app in $HOME/

        path = os.path.join(get_home_dir(), "user.pref")
        config = ConfigObj(path, configspec=meta.config_scheme.split("\n"))
        validator = Validator()
        config.validate(validator)

        for x in meta.languages:
            if config['language'].capitalize() == 'Welsh':
                self.locale = wx.Locale()
                self.locale.Init("Cymraeg", "cy", "cy_GB.utf8")
                break
            elif config['language'].capitalize() == x[0]:
                nolog = wx.LogNull()
                self.locale = wx.Locale(x[1], wx.LOCALE_LOAD_DEFAULT)

        if hasattr(self, "locale"):
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
            path = self.frame.util.get_path()
            for f in os.listdir(path):
                if f.find(self.frame.util.backup_ext) is not -1:
                    os.remove(os.path.join(path, f))