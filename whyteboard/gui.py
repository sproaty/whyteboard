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
This module implements the Whyteboard application.  It takes a Canvas class
and wraps it in a GUI with a menu, toolbar, statusbar and some control panels.

The GUI acts as a controller for the application - it delegates method calls
to the appropriate classes when certain actions take place.
"""

from __future__ import with_statement

import os
import sys
import time
import locale
import webbrowser
import subprocess
import shutil
from optparse import OptionParser

import wx
import wx.lib.newevent
import lib.flatnotebook as fnb
from wx.html import HtmlHelpController

from lib.pubsub import pub
from lib.configobj import ConfigObj
from lib.validate import Validator

import lib.icon
import meta
#import topic_tree
from canvas import Canvas, CanvasDropTarget
from tools import Image, Note, Text, Media, Highlighter, EDGE_LEFT, EDGE_TOP
from utility import Utility

from functions import (get_home_dir, is_exe, get_clipboard, download_help_files,
                       file_dialog, get_path, get_image_path)
from dialogs import (History, ProgressDialog, Resize, UpdateDialog, MyPrintout,
                     ExceptionHook, ShapeViewer, Feedback, PDFCache)
from panels import ControlPanel, SidePanel, SheetsPopup
from preferences import Preferences

# phew!
from event_ids import (ID_CLEAR_ALL, ID_CLEAR_ALL_SHEETS, ID_CLEAR_SHEETS,
                       ID_COLOUR_GRID, ID_DESELECT, ID_EXPORT, ID_EXPORT_ALL,
                       ID_EXPORT_PDF, ID_FEEDBACK, ID_EXPORT_PREF, ID_FULLSCREEN,
                       ID_HISTORY, ID_IMPORT_IMAGE, ID_IMPORT_PDF, ID_IMPORT_PREF,
                       ID_IMPORT_PS, ID_MOVE_UP, ID_MOVE_DOWN, ID_MOVE_TO_TOP,
                       ID_MOVE_TO_BOTTOM, ID_NEW, ID_NEXT, ID_PASTE_NEW, ID_PDF_CACHE,
                       ID_PREV, ID_RECENTLY_CLOSED, ID_RELOAD_PREF, ID_RENAME,
                       ID_REPORT_BUG, ID_RESIZE, ID_SHAPE_VIEWER, ID_STATUSBAR,
                       ID_SWAP_COLOURS, ID_TOOL_PREVIEW, ID_TOOLBAR, ID_TRANSPARENT,
                       ID_TRANSLATE, ID_UNDO_SHEET, ID_UPDATE)


_ = wx.GetTranslation  # Define a translation string
SCROLL_AMOUNT = 3

#----------------------------------------------------------------------


class GUI(wx.Frame):
    """
    This class contains a ControlPanel, a Canvas frame and a SidePanel
    and manages their layout with a wx.BoxSizer.  A menu, toolbar and associated
    event handlers call the appropriate functions of other classes.
    """
    title = "Whyteboard " + meta.version
    LoadEvent, LOAD_DONE_EVENT = wx.lib.newevent.NewEvent()

    def __init__(self, parent, config):
        """
        Initialise utility, status/menu/tool bar, tabs, ctrl panel + bindings.
        """
        wx.Frame.__init__(self, parent, title=_("Untitled") + u" - %s" % self.title)
        ico = lib.icon.whyteboard.getIcon()
        self.SetIcon(ico)
        self.SetExtraStyle(wx.WS_EX_PROCESS_UI_UPDATES)
        self.util = Utility(self, config)
        self.file_drop = CanvasDropTarget(self)
        self.SetDropTarget(self.file_drop)
        self.statusbar = self.CreateStatusBar()
        self.printData = wx.PrintData()
        self.printData.SetPaperId(wx.PAPER_LETTER)
        self.printData.SetPrintMode(wx.PRINT_MODE_PRINTER)

        self.filehistory = wx.FileHistory(8)
        self.config = wx.Config(u"Whyteboard", style=wx.CONFIG_USE_LOCAL_FILE)
        self.filehistory.Load(self.config)

        self._oldhook = sys.excepthook
        sys.excepthook = ExceptionHook
        meta.find_transparent()  # important
        if meta.transparent:
            try:
                x = self.util.items.index(Highlighter)
            except ValueError:
                self.util.items.insert(1, Highlighter)

        self.can_paste = False
        if get_clipboard():
            self.can_paste = True
        self.toolbar = None
        self.menu = None
        self.process = None
        self.pid = None
        self.dialog = None
        self.convert_cancelled = False
        self.viewer = False  # Shape Viewer dialog open?
        self.help = None
        self.make_toolbar()
        self.bar_shown = True  # slight ? performance optimisation
        self.hotkey_pressed = False  # for hotkey timer
        self.hotkey_timer = None
        self.find_help()
        self.tab_count = 1  # instead of typing self.tabs.GetPageCount()
        self.tab_total = 1
        self.current_tab = 0
        self.closed_tabs = []  # [shapes: undo, redo, canvas_size, view_x, view_y] per tab
        self.closed_tabs_id = {}  # wx.Menu IDs for undo closed tab list
        self.hotkeys = []
        self.showcolour, self.showtool, self.next = None, None, None
        self.showstat, self.showprevious, self.prev = None, None, None
        self.closed_tabs_menu = wx.Menu()
        self.control = ControlPanel(self)

        style = (fnb.FNB_X_ON_TAB | fnb.FNB_NO_X_BUTTON | fnb.FNB_VC8 |
                 fnb.FNB_DROPDOWN_TABS_LIST | fnb.FNB_MOUSE_MIDDLE_CLOSES_TABS |
                 fnb.FNB_NO_NAV_BUTTONS)
        self.tabs = fnb.FlatNotebook(self, style=style)
        self.canvas = Canvas(self.tabs, self)  # the active whyteboard tab
        self.panel = SidePanel(self)

        self.thumbs = self.panel.thumbs
        self.notes = self.panel.notes
        self.tabs.AddPage(self.canvas, _("Sheet") + u" 1")
        box = wx.BoxSizer(wx.HORIZONTAL)  # position windows side-by-side
        box.Add(self.control, 0, wx.EXPAND)
        box.Add(self.tabs, 1, wx.EXPAND)
        box.Add(self.panel, 0, wx.EXPAND)
        self.SetSizer(box)
        self.SetSizeWH(800, 600)

        if os.name == "posix":
            self.canvas.SetFocus()  # makes EVT_CHAR_HOOK trigger
        if 'mac' != os.name:
            self.Maximize(True)

        self.count = 5  # used to update menu timings
        wx.UpdateUIEvent.SetUpdateInterval(50)
        wx.UpdateUIEvent.SetMode(wx.UPDATE_UI_PROCESS_SPECIFIED)
        self.canvas.update_thumb()
        self.make_menu()
        self.do_bindings()
        self.update_panels(True)  # bold first items

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
        _export = wx.Menu()
        recent = wx.Menu()
        self.filehistory.UseMenu(recent)
        self.filehistory.AddFilesToMenu()
        self.make_closed_tabs_menu()

        _import.Append(ID_IMPORT_IMAGE, _('&Image...'))
        _import.Append(ID_IMPORT_PDF, '&PDF...')
        _import.Append(ID_IMPORT_PS, 'Post&Script...')
        _import.Append(ID_IMPORT_PREF, _('P&references...'), _("Load in a Whyteboard preferences file"))
        _export.Append(ID_EXPORT, _("&Export Sheet...") + "\tCtrl+E", _("Export the current sheet to an image file"))
        _export.Append(ID_EXPORT_ALL, _("Export &All Sheets...") + "\tCtrl+Shift+E", _("Export every sheet to a series of image files"))
        _export.Append(ID_EXPORT_PDF, _('As &PDF...'), _("Export every sheet into a PDF file"))
        _export.Append(ID_EXPORT_PREF, _('P&references...'), _("Export your Whyteboard preferences file"))

        new = wx.MenuItem(_file, ID_NEW, _("New &Window") + "\tCtrl-N", _("Opens a new Whyteboard instance"))
        pnew = wx.MenuItem(edit, ID_PASTE_NEW, _("Paste to a &New Sheet") + "\tCtrl+Shift-V", _("Paste from your clipboard into a new sheet"))
        undo_sheet = wx.MenuItem(edit, ID_UNDO_SHEET, _("&Undo Last Closed Sheet") + "\tCtrl+Shift-T", _("Undo the last closed sheet"))

        if os.name != "nt":
            new.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_NEW, wx.ART_MENU))
            pnew.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_PASTE, wx.ART_MENU))
            undo_sheet.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_UNDO, wx.ART_MENU))

        _file.AppendItem(new)
        _file.Append(wx.ID_NEW, _("&New Sheet") + "\tCtrl-T", _("Add a new sheet"))
        _file.Append(wx.ID_OPEN, _("&Open...") + "\tCtrl-O", _("Load a Whyteboard save file, an image or convert a PDF/PS document"))
        _file.AppendMenu(-1, _('Open &Recent'), recent, _("Recently Opened Files"))
        _file.AppendSeparator()
        _file.Append(wx.ID_SAVE, _("&Save") + "\tCtrl+S", _("Save the Whyteboard data"))
        _file.Append(wx.ID_SAVEAS, _("Save &As...") + "\tCtrl+Shift+S", _("Save the Whyteboard data in a new file"))
        _file.AppendSeparator()
        _file.AppendMenu(-1, _('&Import File'), _import, _("Import various file types"))
        _file.AppendMenu(-1, _('&Export File'), _export, _("Export your data files as images/PDFs"))
        _file.Append(ID_RELOAD_PREF, _('Re&load Preferences'), _("Reload your preferences file"))
        _file.AppendSeparator()
        _file.Append(wx.ID_PRINT_SETUP, _("Page Set&up"), _("Set up the page for printing"))
        _file.Append(wx.ID_PREVIEW_PRINT, _("Print Pre&view"), _("View a preview of the page to be printed"))
        _file.Append(wx.ID_PRINT, _("&Print...") + "\tCtrl+P", _("Print the current page"))
        _file.AppendSeparator()
        _file.Append(wx.ID_EXIT, _("&Quit") + "\tAlt+F4", _("Quit Whyteboard"))

        edit.Append(wx.ID_UNDO, _("&Undo") + "\tCtrl+Z", _("Undo the last operation"))
        edit.Append(wx.ID_REDO, _("&Redo") + "\tCtrl+Y", _("Redo the last undone operation"))
        edit.AppendSeparator()
        edit.Append(wx.ID_COPY, _("&Copy") + "\tCtrl+C", _("Copy a Bitmap Selection region"))
        edit.Append(wx.ID_PASTE, _("&Paste") + "\tCtrl+V", _("Paste text or an image from your clipboard into Whyteboard"))
        edit.AppendItem(pnew)
        edit.AppendSeparator()
        edit.Append(wx.ID_PREFERENCES, _("Prefere&nces"), _("Change your preferences"))

        view.Append(ID_SHAPE_VIEWER, _("&Shape Viewer...") + "\tF3", _("View and edit the shapes' drawing order"))
        view.Append(ID_HISTORY, _("&History Viewer...") + "\tCtrl+H", _("View and replay your drawing history"))
        view.Append(ID_PDF_CACHE, _("&PDF Cache...") + "\tF4", _("View and modify Whyteboard's PDF Cache"))
        view.AppendSeparator()
        self.showtool = view.Append(ID_TOOLBAR, u" " + _("&Toolbar"), _("Show and hide the toolbar"), kind=wx.ITEM_CHECK)
        self.showstat = view.Append(ID_STATUSBAR, u" " + _("&Status Bar"), _("Show and hide the status bar"), kind=wx.ITEM_CHECK)
        self.showprevious = view.Append(ID_TOOL_PREVIEW, u" " + _("Tool &Preview"), _("Show and hide the tool preview"), kind=wx.ITEM_CHECK)
        self.showcolour = view.Append(ID_COLOUR_GRID, u" " + _("&Color Grid"), _("Show and hide the color grid"), kind=wx.ITEM_CHECK)
        view.AppendSeparator()
        view.Append(ID_FULLSCREEN, u" " + _("&Full Screen") + "\tF11", _("View Whyteboard in full-screen mode"), kind=wx.ITEM_CHECK)

        shapes.Append(ID_MOVE_UP, _("Move Shape &Up") + "\tCtrl-Up", _("Moves the currently selected shape up"))
        shapes.Append(ID_MOVE_DOWN, _("Move Shape &Down") + "\tCtrl-Down", _("Moves the currently selected shape down"))
        shapes.Append(ID_MOVE_TO_TOP, _("Move Shape To &Top") + "\tCtrl-Shift-Up", _("Moves the currently selected shape to the top"))
        shapes.Append(ID_MOVE_TO_BOTTOM, _("Move Shape To &Bottom") + "\tCtrl-Shift-Down", _("Moves the currently selected shape to the bottom"))
        shapes.AppendSeparator()
        shapes.Append(wx.ID_DELETE, _("&Delete Shape") + "\tDelete", _("Delete the currently selected shape"))
        shapes.Append(ID_DESELECT, _("&Deselect Shape") + "\tCtrl-D", _("Deselects the currently selected shape"))
        shapes.Append(ID_SWAP_COLOURS, _("Swap &Colors"), _("Swaps the foreground and background colors"))
        shapes.AppendCheckItem(ID_TRANSPARENT, " " + _("T&ransparent"), _("Toggles the selected shape's transparency"))

        sheets.Append(wx.ID_CLOSE, _("Re&move Sheet") + "\tCtrl+W", _("Close the current sheet"))
        sheets.Append(ID_RENAME, _("&Rename Sheet...") + "\tF2", _("Rename the current sheet"))
        sheets.Append(ID_RESIZE, _("Resi&ze Canvas...") + "\tCtrl+R", _("Change the canvas' size"))
        sheets.AppendSeparator()
        self.next = sheets.Append(ID_NEXT, _("&Next Sheet") + "\tCtrl+Tab", _("Go to the next sheet"))#
        self.prev = sheets.Append(ID_PREV, _("&Previous Sheet") + "\tCtrl+Shift+Tab", _("Go to the previous sheet"))
        sheets.AppendItem(undo_sheet)
        sheets.AppendMenu(ID_RECENTLY_CLOSED, _("Recently &Closed Sheets"), self.closed_tabs_menu, _("View all recently closed sheets"))
        sheets.AppendSeparator()
        sheets.Append(wx.ID_CLEAR, _("&Clear Sheets' Drawings"), _("Clear drawings on the current sheet (keep images)"))
        sheets.Append(ID_CLEAR_ALL, _("Clear &Sheet"), _("Clear the current sheet"))
        sheets.AppendSeparator()
        sheets.Append(ID_CLEAR_SHEETS, _("Clear All Sheets' &Drawings"), _("Clear all sheets' drawings (keep images)"))
        sheets.Append(ID_CLEAR_ALL_SHEETS, _("Clear &All Sheets"), _("Clear all sheets"))

        _help.Append(wx.ID_HELP, _("&Contents") + "\tF1", _("View Whyteboard's help documents"))
        _help.AppendSeparator()
        _help.Append(ID_UPDATE, _("Check for &Updates...") + "\tF12", _("Search for updates to Whyteboard"))
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

        keys = [u'toolbar', u'statusbar', u'tool_preview', u'colour_grid']
        ids = [ID_TOOLBAR, ID_STATUSBAR, ID_TOOL_PREVIEW, ID_COLOUR_GRID]
        for x, _id in zip(keys, ids):
            if self.util.config[x]:
                view.Check(_id, True)
            else:
                getattr(self, u"on_" + x)(None, False)


    def do_bindings(self):
        """
        Performs event binding.
        """
        self.Bind(fnb.EVT_FLATNOTEBOOK_PAGE_CHANGED, self.on_change_tab)
        self.Bind(fnb.EVT_FLATNOTEBOOK_PAGE_CONTEXT_MENU, self.tab_popup)
        self.Bind(fnb.EVT_FLATNOTEBOOK_PAGE_DROPPED, self.on_drop_tab)
        self.Bind(self.LOAD_DONE_EVENT, self.on_done_load)
        self.Bind(wx.EVT_CHAR_HOOK, self.hotkey)
        self.Bind(wx.EVT_CLOSE, self.on_exit)
        self.Bind(wx.EVT_END_PROCESS, self.on_end_process)  # end pdf conversion
        self.Bind(wx.EVT_MENU_RANGE, self.on_file_history, id=wx.ID_FILE1, id2=wx.ID_FILE9)

        topics = {'shape.add': self.shape_add,
                  'shape.selected': self.shape_selected,
                  'canvas.capture_mouse': self.capture_mouse,
                  'canvas.release_mouse': self.release_mouse,
                  'shape_viewer.update': self.update_shape_viewer}
        [pub.subscribe(value, key) for key, value in topics.items()]

        # idle event handlers
        ids = [ID_DESELECT, ID_MOVE_DOWN, ID_MOVE_TO_BOTTOM, ID_MOVE_TO_TOP,
               ID_MOVE_UP, ID_NEXT, ID_PREV, ID_RECENTLY_CLOSED, ID_SWAP_COLOURS,
               ID_TRANSPARENT, ID_UNDO_SHEET, wx.ID_CLOSE, wx.ID_COPY, wx.ID_DELETE,
               wx.ID_PASTE, wx.ID_REDO, wx.ID_UNDO]
        [self.Bind(wx.EVT_UPDATE_UI, self.update_menus, id=x) for x in ids]

        self.hotkeys = [x.hotkey for x in self.util.items]
        ac = []
        # Need to bind each item's hotkey to trigger change tool, passing its ID
        # (position + 1 in the list, basically)
        if os.name == "nt":
            for x, item in enumerate(self.util.items):
                blah = lambda evt, y = x + 1: self.on_change_tool(evt, y)
                _id = wx.NewId()
                ac.append((wx.ACCEL_NORMAL, ord(item.hotkey.upper()), _id))
                self.Bind(wx.EVT_MENU, blah, id=_id)
        else:
            ac = [(wx.ACCEL_CTRL, ord(u'\t'), self.next.GetId()),
                  (wx.ACCEL_CTRL | wx.ACCEL_SHIFT, ord(u'\t'), self.prev.GetId()) ]

        tbl = wx.AcceleratorTable(ac)
        self.SetAcceleratorTable(tbl)

        # "import" sub-menu's bindings
        ids = {'pdf': ID_IMPORT_PDF, 'ps': ID_IMPORT_PS, 'img': ID_IMPORT_IMAGE}
        [self.Bind(wx.EVT_MENU, lambda evt, text=key: self.on_open(evt, text),
                    id=ids[key]) for key in ids]

        # menu bindings
        bindings = { ID_CLEAR_ALL: "clear_all",
                     ID_CLEAR_ALL_SHEETS: "clear_all_sheets",
                     ID_CLEAR_SHEETS: "clear_sheets",
                     ID_COLOUR_GRID: "colour_grid",
                     ID_DESELECT: "deselect_shape",
                     ID_EXPORT: "export",
                     ID_EXPORT_ALL: "export_all",
                     ID_EXPORT_PDF: "export_pdf",
                     ID_EXPORT_PREF: "export_pref",
                     ID_FEEDBACK: "feedback",
                     ID_FULLSCREEN: "fullscreen",
                     ID_HISTORY: "history",
                     ID_IMPORT_PREF: "import_pref",
                     ID_MOVE_DOWN: "move_down",
                     ID_MOVE_TO_BOTTOM: "move_bottom",
                     ID_MOVE_TO_TOP: "move_top",
                     ID_MOVE_UP: "move_up",
                     ID_NEW: "new_win",
                     ID_NEXT: "next",
                     ID_PASTE_NEW: "paste_new",
                     ID_PDF_CACHE: "pdf_cache",
                     ID_PREV: "prev",
                     ID_RELOAD_PREF: "reload_preferences",
                     ID_RENAME: "rename",
                     ID_REPORT_BUG: "report_bug",
                     ID_RESIZE: "resize",
                     ID_SHAPE_VIEWER: "shape_viewer",
                     ID_STATUSBAR: "statusbar",
                     ID_SWAP_COLOURS: "swap_colours",
                     ID_TOOL_PREVIEW: "tool_preview",
                     ID_TOOLBAR: "toolbar",
                     ID_TRANSLATE: "translate",
                     ID_TRANSPARENT: "transparent",
                     ID_UNDO_SHEET: "undo_tab",
                     ID_UPDATE: "update",
                     wx.ID_ABOUT: "about",
                     wx.ID_CLEAR: "clear",
                     wx.ID_CLOSE: "close_tab",
                     wx.ID_COPY: "copy",
                     wx.ID_DELETE: "delete_shape",
                     wx.ID_EXIT: "exit",
                     wx.ID_HELP: "help",
                     wx.ID_NEW : "new_tab",
                     wx.ID_OPEN: "open",
                     wx.ID_PASTE: "paste",
                     wx.ID_PREFERENCES: "preferences",
                     wx.ID_PREVIEW_PRINT: "print_preview",
                     wx.ID_PRINT: "print",
                     wx.ID_PRINT_SETUP: "page_setup",
                     wx.ID_REDO: "redo",
                     wx.ID_SAVE: "save",
                     wx.ID_SAVEAS: "save_as",
                     wx.ID_UNDO: "undo" }

        for _id, name in bindings.items():
            method = getattr(self, u"on_" + name)  # self.on_*
            self.Bind(wx.EVT_MENU, method, id=_id)


    def make_toolbar(self):
        """
        Creates a toolbar, Pythonically :D
        Move to top/up/down/bottom must be created with a custom bitmap.
        """
        self.toolbar = self.CreateToolBar()
        _move = [ID_MOVE_TO_TOP, ID_MOVE_UP, ID_MOVE_DOWN, ID_MOVE_TO_BOTTOM]

        ids = [wx.ID_NEW, wx.ID_OPEN, wx.ID_SAVE, wx.ID_COPY, wx.ID_PASTE,
               wx.ID_UNDO, wx.ID_REDO, wx.ID_DELETE]

        arts = [wx.ART_NEW, wx.ART_FILE_OPEN, wx.ART_FILE_SAVE, wx.ART_COPY,
                wx.ART_PASTE, wx.ART_UNDO, wx.ART_REDO, wx.ART_DELETE]
        tips = [_("New Sheet"), _("Open a File"), _("Save Drawing"), _("Copy a Bitmap Selection"),
                _("Paste an Image/Text"), _("Undo the Last Action"), _("Redo the Last Undone Action"),
                _("Delete the currently selected shape"), _("Move Shape To Top"), ("Move Shape Up"),
                ("Move Shape Down"), ("Move Shape To Bottom")]

        ids.extend(_move)
        arts.extend(_move)
        icons = [u"top", u"up", u"down", u"bottom"]

        bmps = {}
        for icon, _id in zip(icons, _move):
            bmps[_id] = wx.Bitmap(get_image_path(u"icons", u"move-%s-small" % icon))

        # add tools, add a separator and bind paste/undo/redo for UI updating
        for x, (_id, art_id, tip) in enumerate(zip(ids, arts, tips)):
            if _id in _move:
                art = bmps[_id]
            else:
                art = wx.ArtProvider.GetBitmap(art_id, wx.ART_TOOLBAR)

            self.toolbar.AddSimpleTool(_id, art, tip)
            if x == 2 or x == 6:
                self.toolbar.AddSeparator()

        self.toolbar.EnableTool(wx.ID_PASTE, self.can_paste)
        self.toolbar.Realize()


    def make_closed_tabs_menu(self):
        for key, value in self.closed_tabs_id.items():
            self.closed_tabs_menu.Remove(key)
            self.Unbind(wx.EVT_MENU, id=key)

        self.closed_tabs_id = dict()

        for x, tab in enumerate(reversed(self.closed_tabs)):
            _id = wx.NewId()
            name = tab[4]
            self.closed_tabs_id[_id] = tab
            self.closed_tabs_menu.Append(_id, u"&%i: %s" % (x + 1, name),
                                         _('Restore sheet "%s"') % name)
            self.Bind(wx.EVT_MENU, lambda evt, tab=tab: self.on_undo_tab(tab=tab),
                      id=_id)


    def shape_selected(self, shape):
        """
        Shape getting selected (by Select tool)
        """
        self.canvas.select_shape(shape)

        ctrl, menu = True, True
        if not shape.background == wx.TRANSPARENT:
            ctrl, menu = False, False

        self.control.transparent.SetValue(ctrl)
        self.menu.Check(ID_TRANSPARENT, menu)


    def release_mouse(self):
        self.canvas.release_mouse()

    def capture_mouse(self):
        self.canvas.capture_mouse()

    def shape_add(self, shape):
        self.canvas.add_shape(shape)

    def update_shape_viewer(self):
        if self.viewer:
            self.viewer.shapes = list(self.canvas.shapes)
            self.viewer.populate()
            self.viewer.check_buttons()

    def save_last_path(self, path):
        self.util.config['last_opened_dir'] = os.path.dirname(path)
        self.util.config.write()

    def on_save(self, event=None):
        """
        Saves file if filename is set, otherwise calls 'save as'.
        """
        if not self.util.filename:  # if no wtbd file is active, prompt for one
            self.on_save_as()
        else:
            self.util.save_file()
            self.util.saved = True
            self.save_last_path(self.util.filename)


    def on_save_as(self, event=None):
        """
        Prompts for the filename and location to save to.
        """
        wildcard = _("Whyteboard file ") + u"(*.wtbd)|*.wtbd"
        _dir = ""
        _file = time.localtime(time.time())
        _file = time.strftime(u"%Y-%m-%d-%H-%M-%S")

        if self.util.filename:
            _file = self.util.filename

        if self.util.config.get('last_opened_dir'):
            _dir = self.util.config['last_opened_dir']

        name = file_dialog(self, _("Save Whyteboard As..."),
                           wx.SAVE | wx.OVERWRITE_PROMPT, wildcard, _dir, _file)
        if name:
            if not os.path.splitext(name)[1]:  # no file extension
                name += u'.wtbd'

            # only store whyteboard files, not an image as the current file
            if name.lower().endswith(u".wtbd"):
                self.util.filename = name
                self.on_save()


    def on_open(self, event=None, text=None):
        """
        Opens a file, sets Utility's temp. file to the chosen file, prompts for
        an unsaved file and calls do_open().
        text is img/pdf/ps for the "import file" menu item
        """
        wildcard = meta.dialog_wildcard
        if text == u"img":
            wildcard = wildcard[wildcard.find(_("Image Files")) :
                                wildcard.find(_('Whyteboard files')) ]  # image to page
        elif text:
            wildcard = wildcard[wildcard.find(u"PDF/PS/SVG") :
                                wildcard.find(u"*.SVG|")]  # page descriptions

        _dir = u""
        if self.util.config.get('last_opened_dir'):
            _dir = self.util.config['last_opened_dir']

        name = file_dialog(self, _("Open file..."), wx.OPEN, wildcard, _dir)
        if name:
            if name.lower().endswith(u".wtbd"):
                self.util.prompt_for_save(self.do_open, args=[name])
            else:
                self.do_open(name)


    def do_open(self, path):
        """
        Updates the appropriate variables in the utility file class and loads
        the selected file.
        """
        self.filehistory.AddFileToHistory(path)
        self.filehistory.Save(self.config)
        self.config.Flush()
        self.save_last_path(path)

        if path.lower().endswith(u".wtbd"):
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
        filename = file_dialog(self, _("Export data to..."),
                               wx.SAVE | wx.OVERWRITE_PROMPT, u"PDF (*.pdf)|*.pdf")

        if filename:
            ext = os.path.splitext(filename)[1]
            if not ext:  # no file extension
                filename += u'.pdf'
            elif ext.lower() != u".pdf":
                wx.MessageBox(_("Invalid filetype to export as:") + u" .%s" % ext,
                              u"Whyteboard")
                return

            names = []
            canvas = self.canvas
            for x in range(self.tab_count):
                self.canvas = self.tabs.GetPage(x)
                name = u"%s-tempblahhahh-%s-.jpg" % (filename, x)
                names.append(name)
                self.util.export(name)
            self.canvas = canvas

            self.process = wx.Process(self)
            files = ""
            for x in names:
                files += u'"%s" ' % x  # quote filenames for windows

            cmd = u'%s -define pdf:use-trimbox=true %s"%s"' % (self.util.im_location, files, filename)
            self.pid = wx.Execute(cmd, wx.EXEC_ASYNC, self.process)
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
            canvas = self.canvas
            for x in range(self.tab_count):
                self.canvas = self.tabs.GetPage(x)
                self.util.export(u"%s-%s%s" % (name[0], x + 1, name[1]))
            self.canvas = canvas


    def on_export_pref(self, event=None):
        """
        Copies the user's preferences file to another file.
        """
        if not os.path.exists(self.util.config.filename):
            wx.MessageBox(_("You have not set any preferences"), _("Export Error"))
            return
        wildcard = _("Whyteboard Preference Files") + u" (*.pref)|*.pref"

        filename = file_dialog(self, _("Export preferences to..."),
                               wx.SAVE | wx.OVERWRITE_PROMPT, wildcard)
        if filename:
            if not os.path.splitext(filename)[1]:
                filename += u".pref"
            shutil.copy(os.path.join(get_home_dir(), u"user.pref"), filename)


    def on_import_pref(self, event=None):
        """
        Imports the preference file. Backsup the user's current prefernce file
        into a directory, with a timestamp on the filename
        """
        wildcard = _("Whyteboard Preference Files") + u" (*.pref)|*.pref"

        filename = file_dialog(self, _("Import Preferences From..."), wx.OPEN,
                               wildcard, get_home_dir())

        if filename:
            config = ConfigObj(filename, configspec=meta.config_scheme.split(u"\n"))
            validator = Validator()
            config.validate(validator)
            _dir = os.path.join(get_home_dir(), u"pref-bkup")

            if not os.path.isdir(_dir):
                os.makedirs(_dir)

            home = os.path.join(get_home_dir(), u"user.pref")
            if os.path.exists(home):
                stamp = time.strftime(u"%d-%b-%Y_%Hh-%Mm_%Ss", time.gmtime())

                os.rename(home, os.path.join(_dir, stamp + u".user.pref"))
            pref = Preferences(self)
            pref.config = config
            pref.config.filename = home
            pref.on_okay()



    def on_reload_preferences(self, event):
        home = os.path.join(get_home_dir(), u"user.pref")
        if os.path.exists(home):
            config = ConfigObj(home, configspec=meta.config_scheme.split("\n"))
            validator = Validator()
            config.validate(validator)
            pref = Preferences(self)
            pref.config = config
            pref.config.filename = home
            pref.on_okay()


    def export_prompt(self):
        """Find out the filename to save to"""
        val = None  # return value
        wildcard = (u"PNG (*.png)|*.png|JPEG (*.jpg, *.jpeg)|*.jpeg;*.jpg|" +
                    u"BMP (*.bmp)|*.bmp|TIFF (*.tiff)|*.tiff")

        dlg = wx.FileDialog(self, _("Export data to..."),
                            style=wx.SAVE | wx.OVERWRITE_PROMPT, wildcard=wildcard)
        if dlg.ShowModal() == wx.ID_OK:
            filename = dlg.GetPath()
            _name = os.path.splitext(filename)[1].replace(u".", u"")
            types = {0: u"png", 1: u"jpg", 2: u"bmp", 3: u"tiff"}

            if not os.path.splitext(filename)[1]:
                _name = types[dlg.GetFilterIndex()]
                filename += u"." + _name
                val = filename
            if not _name in meta.types[2:]:
                wx.MessageBox(_("Invalid filetype to export as:") + u" .%s" % _name,
                              u"Whyteboard")
            else:
                val = filename
        dlg.Destroy()
        return val


    def on_new_win(self, event=None):
        """Fires up a new Whyteboard window"""
        program = (u'python', os.path.abspath(sys.argv[0]))
        if is_exe():
            program = os.path.abspath(sys.argv[0])

        subprocess.Popen(program)


    def on_new_tab(self, event=None, name=None, wb=None):
        """
        Opens a new tab, selects it, creates a new thumbnail and tree item
        name: unique name, sent by PDF convert/load file.
        wb: Passed by undo_tab to ensure the tab total is correct
        """
        if not wb:
            self.tab_total += 1
        if not name:
            name = _("Sheet") + u" %s" % self.tab_total

        self.tab_count += 1
        self.thumbs.new_thumb(name=name)
        self.notes.add_tab(name)
        self.tabs.AddPage(Canvas(self.tabs, self), name)

        self.update_panels(False)  # unhighlight current
        self.thumbs.thumbs[self.current_tab].current = True

        self.current_tab = self.tab_count - 1
        self.tabs.SetSelection(self.current_tab)  # fires on_change_tab
        self.on_change_tab()


    def on_change_tab(self, event=None):
        """Updates tab vars, scrolls thumbnails and selects tree node"""
        self.canvas = self.tabs.GetCurrentPage()
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

        self.dialog = ProgressDialog(self, _("Loading..."))
        self.dialog.Show()
        self.on_change_tab()

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
            del self.closed_tabs[0]

        self.notes.remove_tab(self.current_tab)
        self.thumbs.remove(self.current_tab)

        for x in self.canvas.medias:
            x.remove_panel()

        canvas = self.canvas
        item = [canvas.shapes, canvas.undo_list, canvas.redo_list, canvas.area,
                self.tabs.GetPageText(self.current_tab), canvas.medias,
                canvas.GetViewStart()[0], canvas.GetViewStart()[1]]

        self.closed_tabs.append(item)
        self.tab_count -= 1

        if os.name == "posix":
            self.tabs.RemovePage(self.current_tab)
        else:
            self.tabs.DeletePage(self.current_tab)

        self.on_change_tab()  # updates self.canvas
        self.make_closed_tabs_menu()


    def on_undo_tab(self, event=None, tab=None):
        """
        Undoes the last closed tab from the list.
        Re-creates the canvas from the saved shapes/undo/redo lists
        """
        if not self.closed_tabs:
            return
        if not tab:
            canvas = self.closed_tabs.pop()
        else:
            canvas = self.closed_tabs.pop(self.closed_tabs.index(tab))

        self.on_new_tab(name=canvas[4], wb=True)
        self.canvas.shapes = canvas[0]
        self.canvas.undo_list = canvas[1]
        self.canvas.redo_list = canvas[2]
        self.canvas.medias = canvas[5]

        for x in self.canvas.medias:
            x.canvas = self.canvas
            x.make_panel()

        for shape in self.canvas.shapes:
            shape.canvas = self.canvas
            if isinstance(shape, Note):
                pub.sendMessage('note.add', note=shape)

        wx.Yield()  # doesn't draw thumbnail otherwise...
        self.canvas.resize(canvas[3])
        self.canvas.Scroll(canvas[6], canvas[7])
        self.canvas.redraw_all(True)
        self.update_shape_viewer()
        self.make_closed_tabs_menu()


    def on_rename(self, event=None, sheet=None):
        if sheet is None:
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
        self.canvas.delete_selected()
        self.update_shape_viewer()

    def on_deselect_shape(self, event=None):
        self.canvas.deselect_shape()


    def update_menus(self, event):
        """
        Enables/disables the undo/redo/next/prev button as appropriate.
        It is called every 65ms and uses a counter to update the clipboard check
        less often than the 65ms, as it's too performance intense
        """
        if not self.canvas:
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
            canvas = self.canvas
            if _id == wx.ID_REDO and canvas.redo_list:
                do = True
            elif _id == wx.ID_UNDO and canvas.undo_list:
                do = True
            elif _id == ID_PREV and self.current_tab:
                do = True
            elif (_id == ID_NEXT and self.tab_count > 1 and
                  self.current_tab + 1 < self.tab_count):
                do = True
            elif _id == wx.ID_CLOSE and self.tab_count > 1:
                do = True
            elif _id in [ID_UNDO_SHEET, ID_RECENTLY_CLOSED] and self.closed_tabs:
                do = True
            elif _id in [wx.ID_DELETE, ID_DESELECT] and canvas.selected:
                do = True
            elif _id == ID_MOVE_UP and canvas.check_move(u"up"):
                do = True
            elif _id == ID_MOVE_DOWN and canvas.check_move(u"down"):
                do = True
            elif _id == ID_MOVE_TO_TOP and canvas.check_move(u"top"):
                do = True
            elif _id == ID_MOVE_TO_BOTTOM and canvas.check_move(u"bottom"):
                do = True
            elif (_id == ID_TRANSPARENT and canvas.selected
                  and not isinstance(canvas.selected, (Media, Image, Text))):
                do = True
            elif (_id == ID_SWAP_COLOURS and canvas.selected
                  and not self.canvas.selected.background == wx.TRANSPARENT
                  and not isinstance(canvas.selected, (Media, Image, Text))):
                do = True
        elif self.canvas:
            if self.canvas.copy:
                do = True
        event.Enable(do)


    def on_copy(self, event):
        """
        If a rectangle selection is made, copy the selection as a bitmap.
        NOTE: The bitmap selection can be larger than the actual canvas bitmap,
        so we must only selection the region of the selection that is on the
        canvas
        """
        self.canvas.copy.update_rect()  # ensure w, h are correct
        bmp = self.canvas.copy

        if bmp.x + bmp.width > self.canvas.area[0]:
            bmp.rect.SetWidth(self.canvas.area[0] - bmp.x)

        if bmp.y + bmp.height > self.canvas.area[1]:
            bmp.rect.SetHeight(self.canvas.area[1] - bmp.y)

        self.canvas.copy = None
        self.canvas.redraw_all()
        self.util.set_clipboard(bmp.rect)
        self.count = 4
        self.UpdateWindowUI()  # force paste buttons to enable (it counts to 4)


    def on_paste(self, event=None, ignore=False):
        """
        Grabs the image from the clipboard and places it on the panel
        Ignore is used when pasting into a new sheet
        """
        data = get_clipboard()
        if not data:
            return

        x, y = 0, 0
        if not ignore:
            x, y = self.canvas.ScreenToClient(wx.GetMousePosition())
            if x < 0 or y < 0 or x > self.canvas.area[0] or y > self.canvas.area[1]:
                x, y = 0, 0

            x, y = self.canvas.CalcUnscrolledPosition(x, y)

        if isinstance(data, wx.TextDataObject):
            shape = Text(self.canvas, self.util.colour, 1)
            shape.text = data.GetText()

            self.canvas.shape = shape
            shape.left_down(x, y)
            shape.left_up(x, y)
            self.canvas.text = None
            self.canvas.change_current_tool()
            self.canvas.redraw_all(True)
        else:
            bmp = data.GetBitmap()
            shape = Image(self.canvas, bmp, None)
            shape.left_down(x, y)
            wx.Yield()
            self.canvas.redraw_all(True)
            if ignore:
                self.canvas.resize((bmp.GetWidth(), bmp.GetHeight()))


    def on_paste_new(self, event):
        """ Pastes the image into a new tab """
        self.on_new_tab()
        self.on_paste(ignore=True)

    def on_change_tool(self, event, _id):
        if not self.canvas.shape.drawing and not self.canvas.drawing:
            self.control.change_tool(_id=_id)


    def on_fullscreen(self, event=None, val=None):
        """ Toggles fullscreen. val forces fullscreen on/off """
        flag = (wx.FULLSCREEN_NOBORDER | wx.FULLSCREEN_NOCAPTION |
               wx.FULLSCREEN_NOSTATUSBAR)
        if not val:
            val = not self.IsFullScreen()

        menu = self.menu.FindItemById(ID_FULLSCREEN)
        self.ShowFullScreen(val, flag)
        menu.Check(val)


    def hotkey(self, event=None):
        """escape / home / end / page up / page down/arrow key)"""
        code = event.GetKeyCode()
        if os.name == "posix":
            for x, key in enumerate(self.hotkeys):

                if code in [ord(key), ord(key.upper())]:
                    self.on_change_tool(None, _id=x + 1)
                    return

        if code == wx.WXK_ESCAPE:  # close fullscreen/deselect shape
            if self.canvas.selected:
                self.canvas.deselect_shape()  # check this before fullscreen
                return
            if self.IsFullScreen():
                self.on_fullscreen(None, False)
        elif code in [wx.WXK_DOWN, wx.WXK_LEFT, wx.WXK_RIGHT, wx.WXK_UP]:
            if self.canvas.selected:
                shape = self.canvas.selected

                _map = { wx.WXK_UP: (shape.x, shape.y - SCROLL_AMOUNT),
                        wx.WXK_DOWN: (shape.x, shape.y + SCROLL_AMOUNT),
                        wx.WXK_LEFT: (shape.x - SCROLL_AMOUNT, shape.y),
                        wx.WXK_RIGHT: (shape.x + SCROLL_AMOUNT, shape.y) }

                if not self.hotkey_pressed:
                    self.hotkey_pressed = True
                    self.canvas.add_undo()
                    shape.start_select_action(0)
                    self.hotkey_timer = wx.CallLater(150, self.reset_hotkey)
                else:
                    self.hotkey_timer.Restart(150)

                shape.move(_map.get(code)[0], _map.get(code)[1],
                           offset=shape.offset(shape.x, shape.y))
                self.canvas.draw_shape(shape)
                #shape.find_edges()
                #self.canvas.shape_near_canvas_edge(shape.edges[EDGE_LEFT],
                #                                   shape.edges[EDGE_TOP], True)
                return
        self.hotkey_scroll(code, event)
        event.Skip()


    def hotkey_scroll(self, code, event):
        """Scrolls the viewport depending on the key pressed"""
        x, y = None, None
        if code == wx.WXK_HOME:
            x, y = 0, -1  # beginning of viewport
            if event.ControlDown():
                x, y = -1, 0  # top of document

        elif code == wx.WXK_END:
            x, y = self.canvas.area[0], -1  # end of viewport
            if event.ControlDown():
                x, y = -1, self.canvas.area[1]  # end of page

        elif code in [wx.WXK_PAGEUP, wx.WXK_PAGEDOWN, wx.WXK_DOWN, wx.WXK_LEFT,
                      wx.WXK_RIGHT, wx.WXK_UP]:
            x, y = self.canvas.GetViewStart()
            x2, y2 = self.canvas.GetClientSizeTuple()

            _map = { wx.WXK_PAGEUP: (-1, y - y2),
                    wx.WXK_PAGEDOWN: (-1, y + y2),
                    wx.WXK_UP: (-1, y - SCROLL_AMOUNT),
                    wx.WXK_DOWN: (-1, y + SCROLL_AMOUNT),
                    wx.WXK_LEFT: (x - SCROLL_AMOUNT, -1),
                    wx.WXK_RIGHT: (x + SCROLL_AMOUNT, -1) }

            x, y = _map.get(code)[0], _map.get(code)[1]

        if x != None and y != None:
            self.canvas.Scroll(x, y)


    def reset_hotkey(self):
        """Reset the system for the next stream of hotkey up/down events"""
        self.hotkey_pressed = False
        if not self.canvas.selected:
            return
        self.canvas.selected.end_select_action(0)
        self.update_shape_viewer()


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
        self.toggle_view(self.showprevious, self.control.preview, force)


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
        self.dialog = ProgressDialog(self, _("Converting..."), True)
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
            wx.MessageBox(_("File %s not found") % path, u"Whyteboard")
            self.filehistory.RemoveFileFromHistory(num)
            return
        self.filehistory.AddFileToHistory(path)  # move up the list

        if path.lower().endswith(u".wtbd"):
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
        self.canvas.undo()
        self.update_shape_viewer()

    def on_redo(self, event=None):
        """ Calls redo on the active tab and updates the menus """
        self.canvas.redo()
        self.update_shape_viewer()

    def on_move_top(self, event=None):
        self.canvas.move_top(self.canvas.selected)
        self.update_shape_viewer()

    def on_move_bottom(self, event=None):
        self.canvas.move_bottom(self.canvas.selected)
        self.update_shape_viewer()

    def on_move_up(self, event=None):
        self.canvas.move_up(self.canvas.selected)
        self.update_shape_viewer()

    def on_move_down(self, event=None):
        self.canvas.move_down(self.canvas.selected)
        self.update_shape_viewer()

    def on_prev(self, event=None):
        """ Changes to the previous sheet """
        if not self.current_tab:
            return
        self.tabs.SetSelection(self.current_tab - 1)
        self.on_change_tab()

    def on_next(self, event=None):
        """ Changes to the next sheet """
        if self.tab_count < 1 and self.current_tab + 1 > self.tab_count:
            return
        self.tabs.SetSelection(self.current_tab + 1)
        self.on_change_tab()

    def on_clear(self, event=None):
        """ Clears current sheet's drawings, except images. """
        self.canvas.clear(keep_images=True)
        self.update_shape_viewer()

    def on_clear_all(self, event=None):
        """ Clears current sheet """
        self.canvas.clear()
        self.update_shape_viewer()
        self.thumbs.update_all()

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
        self.thumbs.update_all()


    def on_refresh(self):
        self.thumbs.update_all()

    def on_transparent(self, event=None):
        self.canvas.toggle_transparent()

    def on_swap_colours(self, event=None):
        self.canvas.swap_colours()


    def on_page_setup(self, evt):
        psdd = wx.PageSetupDialogData(self.printData)
        psdd.CalculatePaperSizeFromId()
        dlg = wx.PageSetupDialog(self, psdd)
        dlg.ShowModal()
        self.printData = wx.PrintData(dlg.GetPageSetupData().GetPrintData())
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

        if not printer.Print(self.canvas, printout, True):
            if printer.GetLastError() is not wx.PRINTER_CANCELLED:
                wx.MessageBox(_("There was a problem printing.\nPerhaps your current printer is not set correctly?"),
                              _("Printing Error"), wx.OK)
        else:
            self.printData = wx.PrintData(printer.GetPrintDialogData().GetPrintData())
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
        self.open_url(u"https://translations.launchpad.net/whyteboard")

    def on_report_bug(self, event):
        self.open_url(u"https://bugs.launchpad.net/whyteboard")

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

    def on_pdf_cache(self, event=None):
        self.show_dialog(PDFCache(self))

    def on_feedback(self, event):
        self.show_dialog(Feedback(self), False)


    def find_help(self):
        """Locate the help files, update self.help var"""
        _file = os.path.join(get_path(), u'whyteboard-help', u'whyteboard.hhp')

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
                download_help_files(self.util.path[0])
                self.find_help()
                return True
            except IOError:
                return False


    def on_about(self, event=None):
        inf = wx.AboutDialogInfo()
        inf.Name = u"Whyteboard"
        inf.Version = meta.version
        inf.Copyright = u"(C) 2009 Steven Sproat"
        inf.Description = _("A simple whiteboard and PDF annotator")
        inf.Developers = [u"Steven Sproat <sproaty@gmail.com>"]
        inf.Translators = meta.translators
        x = u"http://www.launchpad.net/whyteboard"
        inf.WebSite = (x, x)

        license = os.path.join(get_path(), u"LICENSE.txt")
        if os.path.exists(license):
            with open(license) as f:
                inf.Licence = f.read()
        else:
            inf.Licence = u"GPL 3"

        wx.AboutBox(inf)

#----------------------------------------------------------------------



class WhyteboardApp(wx.App):
    def OnInit(self):
        """
        Load config file, apply translation, parse arguments and delete any
        temporary filse left over from an update
        """
        wx.SetDefaultPyEncoding("utf-8")
        self.SetAppName(u"whyteboard")  # used to identify app in $HOME/

        parser = OptionParser(version="Whyteboard %s" % meta.version)
        parser.add_option("-f", "--file", help="load FILE on load")
        parser.add_option("-c", "--conf", help="load configurations from CONF file")
        parser.add_option("--width", type="int", help="set canvas to WIDTH")
        parser.add_option("--height", type="int", help="set canvas to HEIGHT")
        parser.add_option("-u", "--update", action="store_true", help="check for a newer version of whyteboard")
        parser.add_option("-l", "--lang", help="set language. can be a country code or language (e.g. fr, french, nl, dutch)")

        path = os.path.join(get_home_dir(), u"user.pref")
        (options, args) = parser.parse_args()
        if options.conf:
            path = options.conf

        config = ConfigObj(path, configspec=meta.config_scheme.split("\n"), encoding=u"utf-8")
        config.validate(Validator())

        set_lang = False
        lang_name = config['language']

        if options.lang:
            country = wx.Locale.FindLanguageInfo(options.lang)
            if country:
                set_lang = True
                lang_name = country.Description
                self.locale = wx.Locale(country.Language, wx.LOCALE_LOAD_DEFAULT)


        if not set_lang:
            for x in meta.languages:
                if config['language'].capitalize() == 'Welsh':
                    self.locale = wx.Locale()
                    self.locale.Init(u"Cymraeg", u"cy", u"cy_GB.utf8")
                    break
                elif config['language'].capitalize() == x[0]:
                    nolog = wx.LogNull()
                    self.locale = wx.Locale(x[2], wx.LOCALE_LOAD_DEFAULT)

        if hasattr(self, "locale"):
            if not wx.Locale.IsOk(self.locale):

                wx.MessageBox(u"Error setting language to %s - reverting to English" % lang_name,
                              u"Whyteboard")
                if not set_lang:
                    config['language'] = 'English'
                    config.write()
                self.locale = wx.Locale(wx.LANGUAGE_DEFAULT, wx.LOCALE_LOAD_DEFAULT)

            langdir = os.path.join(get_path(), u'locale')
            locale.setlocale(locale.LC_ALL, u'')
            self.locale.AddCatalogLookupPathPrefix(langdir)
            self.locale.AddCatalog(u"whyteboard")

        reload(meta)  # fix for some translated strings not being applied

        self.frame = GUI(None, config)
        self.frame.Show(True)

        try:
            _file = os.path.abspath(sys.argv[1])
            if _file.lower().endswith(u".wtbd"):

                if os.path.exists(_file):
                    self.frame.do_open(_file)
            elif options.file:
                self.load_file(options.file)
        except IndexError:
            pass

        if options.width:
            self.frame.canvas.resize((options.width, self.frame.canvas.area[1]))
        if options.height:
            self.frame.canvas.resize((self.frame.canvas.area[0], options.height))

        if options.update:
            self.frame.on_update()

        self.delete_temp_files()
        return True


    def load_file(self, _file):
        """Forward the first command-line arg to gui.do_open()"""
        try:
            _file = os.path.abspath(_file)
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
        if is_exe() and os.path.exists(u"wtbd-bckup.exe"):
            os.remove(u"wtbd-bckup.exe")
        else:
            path = get_path()
            for f in os.listdir(path):
                if f.find(self.frame.util.backup_ext) is not - 1:
                    os.remove(os.path.join(path, f))