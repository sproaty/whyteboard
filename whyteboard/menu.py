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
Creates the menu bar for the GUI
"""

import os
import wx

from event_ids import (ID_CLEAR_ALL, ID_CLEAR_ALL_SHEETS, ID_CLEAR_SHEETS,
       ID_CLOSE_ALL, ID_COLOUR_GRID, ID_DESELECT, ID_EXPORT, ID_EXPORT_ALL,
       ID_EXPORT_PDF, ID_FEEDBACK, ID_EXPORT_PREF, ID_FULLSCREEN, ID_HISTORY,
       ID_IMPORT_IMAGE, ID_IMPORT_PDF, ID_IMPORT_PREF, ID_IMPORT_PS, ID_MOVE_UP,
       ID_MOVE_DOWN, ID_MOVE_TO_TOP, ID_MOVE_TO_BOTTOM, ID_NEW, ID_NEXT,
       ID_PASTE_NEW, ID_PDF_CACHE, ID_PREV, ID_RECENTLY_CLOSED, ID_RELOAD_PREF,
       ID_RENAME, ID_REPORT_BUG, ID_RESIZE, ID_SHAPE_VIEWER, ID_STATUSBAR,
       ID_SWAP_COLOURS, ID_TOOL_PREVIEW, ID_TOOLBAR, ID_TRANSPARENT,
       ID_TRANSLATE, ID_UNDO_SHEET, ID_UPDATE)

_ = wx.GetTranslation

class Menu(object):
    """
    Menu bar and its bindings.
    """
    def __init__(self, gui):
        self.gui = gui
        self.closed_tabs_id = {}  # of wx.Menu IDs
        self.menu = wx.MenuBar()
        self.closed_tabs_menu = wx.Menu()
        self.recent = wx.Menu()
        _file = wx.Menu()
        self.file = _file
        edit = wx.Menu()
        self.view = wx.Menu()
        shapes = wx.Menu()
        sheets = wx.Menu()
        _help = wx.Menu()
        _import = wx.Menu()
        _export = wx.Menu()
        gui.filehistory.UseMenu(self.recent)
        gui.filehistory.AddFilesToMenu()
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
        _file.AppendMenu(-1, _('Open &Recent'), self.recent, _("Recently Opened Files"))
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

        self.view.Append(ID_SHAPE_VIEWER, _("&Shape Viewer...") + "\tF3", _("View and edit the shapes' drawing order"))
        self.view.Append(ID_HISTORY, _("&History Viewer...") + "\tCtrl+H", _("View and replay your drawing history"))
        self.view.Append(ID_PDF_CACHE, _("&PDF Cache...") + "\tF4", _("View and modify Whyteboard's PDF Cache"))
        self.view.AppendSeparator()
        self.view.Append(ID_TOOLBAR, u" " + _("&Toolbar"), _("Show and hide the toolbar"), kind=wx.ITEM_CHECK)
        self.view.Append(ID_STATUSBAR, u" " + _("&Status Bar"), _("Show and hide the status bar"), kind=wx.ITEM_CHECK)
        self.view.Append(ID_TOOL_PREVIEW, u" " + _("Tool &Preview"), _("Show and hide the tool preview"), kind=wx.ITEM_CHECK)
        self.view.Append(ID_COLOUR_GRID, u" " + _("&Color Grid"), _("Show and hide the color grid"), kind=wx.ITEM_CHECK)
        self.view.AppendSeparator()
        self.view.Append(ID_FULLSCREEN, u" " + _("&Full Screen") + "\tF11", _("View Whyteboard in full-screen mode"), kind=wx.ITEM_CHECK)

        shapes.Append(ID_MOVE_UP, _("Move Shape &Up") + "\tCtrl-Up", _("Moves the currently selected shape up"))
        shapes.Append(ID_MOVE_DOWN, _("Move Shape &Down") + "\tCtrl-Down", _("Moves the currently selected shape down"))
        shapes.Append(ID_MOVE_TO_TOP, _("Move Shape To &Top") + "\tCtrl-Shift-Up", _("Moves the currently selected shape to the top"))
        shapes.Append(ID_MOVE_TO_BOTTOM, _("Move Shape To &Bottom") + "\tCtrl-Shift-Down", _("Moves the currently selected shape to the bottom"))
        shapes.AppendSeparator()
        shapes.Append(wx.ID_DELETE, _("&Delete Shape") + "\tDelete", _("Delete the currently selected shape"))
        shapes.Append(ID_DESELECT, _("&Deselect Shape") + "\tCtrl-D", _("Deselects the currently selected shape"))
        shapes.AppendSeparator()
        shapes.Append(ID_SWAP_COLOURS, _("Swap &Colors"), _("Swaps the foreground and background colors"))
        shapes.AppendCheckItem(ID_TRANSPARENT, " " + _("T&ransparent"), _("Toggles the selected shape's transparency"))

        sheets.Append(wx.ID_CLOSE, _("Re&move Sheet") + "\tCtrl+W", _("Close the current sheet"))
        sheets.Append(ID_CLOSE_ALL, _("&Close All Sheets") + "\tCtrl+Shift+W", _("Close every sheet"))
        sheets.Append(ID_RENAME, _("&Rename Sheet...") + "\tF2", _("Rename the current sheet"))
        sheets.Append(ID_RESIZE, _("Resi&ze Canvas...") + "\tCtrl+R", _("Change the canvas' size"))
        sheets.AppendSeparator()
        sheets.Append(ID_NEXT, _("&Next Sheet") + "\tCtrl+Tab", _("Go to the next sheet"))#
        sheets.Append(ID_PREV, _("&Previous Sheet") + "\tCtrl+Shift+Tab", _("Go to the previous sheet"))
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
        self.menu.Append(self.view, _("&View"))
        self.menu.Append(shapes, _("Sha&pes"))
        self.menu.Append(sheets, _("&Sheets"))
        self.menu.Append(_help, _("&Help"))


    def bindings(self):
        """
        Binds the menu items to the GUI
        """
        self.gui.Bind(wx.EVT_MENU_RANGE, self.gui.on_file_history, id=wx.ID_FILE1, id2=wx.ID_FILE9)
        self.gui.Bind(wx.EVT_MENU_OPEN, self.gui.load_recent_files)

        # "Import" sub-menu
        ids = {'pdf': ID_IMPORT_PDF, 'ps': ID_IMPORT_PS, 'img': ID_IMPORT_IMAGE}
        [self.gui.Bind(wx.EVT_MENU, lambda evt, text=key: self.gui.on_open(evt, text),
                    id=ids[key]) for key in ids]


        # idle event handlers
        ids = [ID_CLOSE_ALL, ID_DESELECT, ID_MOVE_DOWN, ID_MOVE_TO_BOTTOM, ID_MOVE_TO_TOP,
               ID_MOVE_UP, ID_NEXT, ID_PREV, ID_RECENTLY_CLOSED, ID_SWAP_COLOURS,
               ID_TRANSPARENT, ID_UNDO_SHEET, wx.ID_CLOSE, wx.ID_COPY, wx.ID_DELETE,
               wx.ID_PASTE, wx.ID_REDO, wx.ID_UNDO]
        [self.gui.Bind(wx.EVT_UPDATE_UI, self.gui.update_menus, id=x) for x in ids]
        
        # menu items
        bindings = { ID_CLEAR_ALL: "clear_all",
                     ID_CLEAR_ALL_SHEETS: "clear_all_sheets",
                     ID_CLEAR_SHEETS: "clear_sheets",
                     ID_CLOSE_ALL: "close_all_sheets",
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
            method = getattr(self.gui, u"on_" + name)
            self.gui.Bind(wx.EVT_MENU, method, id=_id)


    def make_closed_tabs_menu(self):
        """
        Recreates the undo tab menu
        """
        gui = self.gui
        for key, value in self.closed_tabs_id.items():
            self.closed_tabs_menu.Remove(key)
            gui.Unbind(wx.EVT_MENU, id=key)

        gui.closed_tabs_id = dict()

        for x, tab in enumerate(reversed(gui.closed_tabs)):
            _id = wx.NewId()
            name = tab['name']
            self.closed_tabs_id[_id] = tab
            self.closed_tabs_menu.Append(_id, u"&%i: %s" % (x + 1, name),
                                         _('Restore sheet "%s"') % name)
            gui.Bind(wx.EVT_MENU, id=_id,
                     handler=lambda evt, tab=tab: self.gui.on_undo_tab(tab=tab))


    def toggle_fullscreen(self, value):
        menu = self.menu.FindItemById(ID_FULLSCREEN)
        menu.Check(value)

    def remove_all_recent(self):
        for x in self.recent.GetMenuItems():
            self.recent.RemoveItem(x)

    def is_checked(self, id):
        menu = self.menu.FindItemById(id)
        return menu.IsChecked()

    def is_file_menu(self, menu):
        return menu == self.file

    def check(self, id, value):
        self.menu.Check(id, value)

    def enable(self, id, value):
        self.menu.Enable(id, value)