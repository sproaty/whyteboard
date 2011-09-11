#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2009-2011 by Steven Sproat
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
import logging
import wx

from whyteboard.misc import get_image_path

from whyteboard.gui import (ID_CLEAR_ALL, ID_CLEAR_ALL_SHEETS, ID_CLEAR_SHEETS,
       ID_CLOSE_ALL, ID_COLOUR_GRID, ID_DESELECT, ID_EXPORT, ID_EXPORT_ALL,
       ID_EXPORT_PDF, ID_FEEDBACK, ID_EXPORT_PREF, ID_FULLSCREEN, ID_HISTORY,
       ID_IMPORT_IMAGE, ID_IMPORT_PDF, ID_IMPORT_PREF, ID_IMPORT_PS, ID_MOVE_UP,
       ID_MOVE_DOWN, ID_MOVE_TO_TOP, ID_MOVE_TO_BOTTOM, ID_NEW, ID_NEXT,
       ID_PASTE_NEW, ID_PDF_CACHE, ID_PREV, ID_RECENTLY_CLOSED, ID_RELOAD_PREF,
       ID_RENAME, ID_REPORT_BUG, ID_RESIZE, ID_SHAPE_VIEWER, ID_STATUSBAR,
       ID_SWAP_COLOURS, ID_TOOL_PREVIEW, ID_TOOLBAR, ID_TRANSPARENT,
       ID_TRANSLATE, ID_UNDO_SHEET, ID_UPDATE, ID_BACKGROUND, ID_FOREGROUND)

_ = wx.GetTranslation
logger = logging.getLogger("whyteboard.menu")

#----------------------------------------------------------------------

class Menu(object):
    """
    Menu bar and its bindings.
    """
    def __init__(self, gui):
        logger.debug("Initialising Menu")
        self.gui = gui
        self.menu = wx.MenuBar()
        self.closed_tabs_menu = wx.Menu()
        self.recent = wx.Menu()
        self.file = wx.Menu()
        self.view = wx.Menu()
        edit = wx.Menu()
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

        new = wx.MenuItem(self.file, ID_NEW, _("New &Window") + "\tCtrl-N", _("Opens a new Whyteboard instance"))
        pnew = wx.MenuItem(edit, ID_PASTE_NEW, _("Paste to a &New Sheet") + "\tCtrl+Shift-V", _("Paste from your clipboard into a new sheet"))
        undo_sheet = wx.MenuItem(edit, ID_UNDO_SHEET, _("&Undo Last Closed Sheet") + "\tCtrl+Shift-T", _("Undo the last closed sheet"))

        if os.name != "nt":
            new.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_NEW, wx.ART_MENU))
            pnew.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_PASTE, wx.ART_MENU))
            undo_sheet.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_UNDO, wx.ART_MENU))

        self.file.AppendItem(new)
        self.file.Append(wx.ID_NEW, _("&New Sheet") + "\tCtrl-T", _("Add a new sheet"))
        self.file.Append(wx.ID_OPEN, _("&Open...") + "\tCtrl-O", _("Load a Whyteboard save file, an image or convert a PDF/PS document"))
        self.file.AppendMenu(-1, _('Open &Recent'), self.recent, _("Recently Opened Files"))
        self.file.AppendSeparator()
        self.file.Append(wx.ID_SAVE, _("&Save") + "\tCtrl+S", _("Save the Whyteboard data"))
        self.file.Append(wx.ID_SAVEAS, _("Save &As...") + "\tCtrl+Shift+S", _("Save the Whyteboard data in a new file"))
        self.file.AppendSeparator()
        self.file.AppendMenu(-1, _('&Import File'), _import, _("Import various file types"))
        self.file.AppendMenu(-1, _('&Export File'), _export, _("Export your data files as images/PDFs"))
        self.file.Append(ID_RELOAD_PREF, _('Re&load Preferences'), _("Reload your preferences file"))
        self.file.AppendSeparator()
        self.file.Append(wx.ID_PRINT_SETUP, _("Page Set&up"), _("Set up the page for printing"))
        self.file.Append(wx.ID_PREVIEW_PRINT, _("Print Pre&view"), _("View a preview of the page to be printed"))
        self.file.Append(wx.ID_PRINT, _("&Print...") + "\tCtrl+P", _("Print the current page"))
        self.file.AppendSeparator()
        self.file.Append(wx.ID_EXIT, _("&Quit") + "\tAlt+F4", _("Quit Whyteboard"))

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
        shapes.AppendCheckItem(ID_TRANSPARENT, " " + _("T&ransparent"), _("Toggles the selected shape's transparency"))
        shapes.Append(ID_FOREGROUND, _("&Color..."), _("Change the selected shape's color"))
        shapes.Append(ID_BACKGROUND, _("&Background Color..."), _("Change the selected shape's background color"))
        shapes.Append(ID_SWAP_COLOURS, _("Swap &Colors"), _("Swaps the foreground and background colors"))

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

        self.menu.Append(self.file, _("&File"))
        self.menu.Append(edit, _("&Edit"))
        self.menu.Append(self.view, _("&View"))
        self.menu.Append(shapes, _("Sha&pes"))
        self.menu.Append(sheets, _("&Sheets"))
        self.menu.Append(_help, _("&Help"))

        self.gui.SetMenuBar(self.menu)


    def bindings(self):
        """
        Binds the menu items to the GUI
        """
        self.gui.Bind(wx.EVT_MENU_RANGE, self.gui.on_file_history, id=wx.ID_FILE1, id2=wx.ID_FILE9)
        # print -- ..test this on linux
        #self.gui.Bind(wx.EVT_MENU_OPEN, self.gui.load_recent_files)

        # "Import" sub-menu
        ids = {'pdf': ID_IMPORT_PDF, 'ps': ID_IMPORT_PS, 'img': ID_IMPORT_IMAGE}
        [self.gui.Bind(wx.EVT_MENU, lambda evt, text=key: self.gui.on_open(evt, text),
                    id=ids[key]) for key in ids]


        # idle event handlers
        ids = [ID_BACKGROUND, ID_CLOSE_ALL, ID_DESELECT, ID_FOREGROUND, ID_MOVE_DOWN,
               ID_MOVE_TO_BOTTOM, ID_MOVE_TO_TOP, ID_MOVE_UP, ID_NEXT, ID_PASTE_NEW, ID_PREV,
               ID_RECENTLY_CLOSED, ID_SWAP_COLOURS, ID_TRANSPARENT, ID_UNDO_SHEET,
               wx.ID_CLOSE, wx.ID_COPY, wx.ID_DELETE, wx.ID_PASTE, wx.ID_REDO, wx.ID_UNDO]
        [self.gui.Bind(wx.EVT_UPDATE_UI, self.gui.update_menus, id=x) for x in ids]

        # menu items
        self.gui.Bind(wx.EVT_MENU, self.gui.on_background, id=ID_BACKGROUND)
        self.gui.Bind(wx.EVT_MENU, self.gui.on_clear_all, id=ID_CLEAR_ALL)
        self.gui.Bind(wx.EVT_MENU, self.gui.on_clear_all_sheets, id=ID_CLEAR_ALL_SHEETS)
        self.gui.Bind(wx.EVT_MENU, self.gui.on_clear_sheets, id=ID_CLEAR_SHEETS)
        self.gui.Bind(wx.EVT_MENU, self.gui.on_close_all_sheets, id=ID_CLOSE_ALL)
        self.gui.Bind(wx.EVT_MENU, self.gui.on_colour_grid, id=ID_COLOUR_GRID)
        self.gui.Bind(wx.EVT_MENU, self.gui.on_deselect_shape, id=ID_DESELECT)
        self.gui.Bind(wx.EVT_MENU, self.gui.on_export, id=ID_EXPORT)
        self.gui.Bind(wx.EVT_MENU, self.gui.on_export_all, id=ID_EXPORT_ALL)
        self.gui.Bind(wx.EVT_MENU, self.gui.on_export_pdf, id=ID_EXPORT_PDF)
        self.gui.Bind(wx.EVT_MENU, self.gui.on_export_preferences, id=ID_EXPORT_PREF)
        self.gui.Bind(wx.EVT_MENU, self.gui.on_feedback, id=ID_FEEDBACK)
        self.gui.Bind(wx.EVT_MENU, self.gui.on_foreground, id=ID_FOREGROUND)
        self.gui.Bind(wx.EVT_MENU, self.gui.on_fullscreen, id=ID_FULLSCREEN)
        self.gui.Bind(wx.EVT_MENU, self.gui.on_history, id=ID_HISTORY)
        self.gui.Bind(wx.EVT_MENU, self.gui.on_import_preferences, id=ID_IMPORT_PREF)
        self.gui.Bind(wx.EVT_MENU, self.gui.on_move_down, id=ID_MOVE_DOWN)
        self.gui.Bind(wx.EVT_MENU, self.gui.on_move_bottom, id=ID_MOVE_TO_BOTTOM)
        self.gui.Bind(wx.EVT_MENU, self.gui.on_move_top, id=ID_MOVE_TO_TOP)
        self.gui.Bind(wx.EVT_MENU, self.gui.on_move_up, id=ID_MOVE_UP)
        self.gui.Bind(wx.EVT_MENU, self.gui.on_new_win, id=ID_NEW)
        self.gui.Bind(wx.EVT_MENU, self.gui.on_next_sheet, id=ID_NEXT)
        self.gui.Bind(wx.EVT_MENU, self.gui.on_paste_new, id=ID_PASTE_NEW)
        self.gui.Bind(wx.EVT_MENU, self.gui.on_pdf_cache, id=ID_PDF_CACHE)
        self.gui.Bind(wx.EVT_MENU, self.gui.on_previous_sheet, id=ID_PREV)
        self.gui.Bind(wx.EVT_MENU, self.gui.on_reload_preferences, id=ID_RELOAD_PREF)
        self.gui.Bind(wx.EVT_MENU, self.gui.on_rename, id=ID_RENAME)
        self.gui.Bind(wx.EVT_MENU, self.gui.on_report_bug, id=ID_REPORT_BUG)
        self.gui.Bind(wx.EVT_MENU, self.gui.on_resize, id=ID_RESIZE)
        self.gui.Bind(wx.EVT_MENU, self.gui.on_shape_viewer, id=ID_SHAPE_VIEWER)
        self.gui.Bind(wx.EVT_MENU, self.gui.on_statusbar, id=ID_STATUSBAR)
        self.gui.Bind(wx.EVT_MENU, self.gui.on_swap_colours, id=ID_SWAP_COLOURS)
        self.gui.Bind(wx.EVT_MENU, self.gui.on_tool_preview, id=ID_TOOL_PREVIEW)
        self.gui.Bind(wx.EVT_MENU, self.gui.on_toolbar, id=ID_TOOLBAR)
        self.gui.Bind(wx.EVT_MENU, self.gui.on_translate, id=ID_TRANSLATE)
        self.gui.Bind(wx.EVT_MENU, self.gui.on_transparent, id=ID_TRANSPARENT)
        self.gui.Bind(wx.EVT_MENU, self.gui.on_undo_tab, id=ID_UNDO_SHEET)
        self.gui.Bind(wx.EVT_MENU, self.gui.on_update, id=ID_UPDATE)
        self.gui.Bind(wx.EVT_MENU, self.gui.on_about, id=wx.ID_ABOUT)
        self.gui.Bind(wx.EVT_MENU, self.gui.on_clear, id=wx.ID_CLEAR)
        self.gui.Bind(wx.EVT_MENU, self.gui.on_close_tab, id=wx.ID_CLOSE)
        self.gui.Bind(wx.EVT_MENU, self.gui.on_copy, id=wx.ID_COPY)
        self.gui.Bind(wx.EVT_MENU, self.gui.on_delete_shape, id=wx.ID_DELETE)
        self.gui.Bind(wx.EVT_MENU, self.gui.on_exit, id=wx.ID_EXIT)
        self.gui.Bind(wx.EVT_MENU, self.gui.on_help, id=wx.ID_HELP)
        self.gui.Bind(wx.EVT_MENU, self.gui.on_new_tab, id=wx.ID_NEW )
        self.gui.Bind(wx.EVT_MENU, self.gui.on_open, id=wx.ID_OPEN)
        self.gui.Bind(wx.EVT_MENU, self.gui.on_paste, id=wx.ID_PASTE)
        self.gui.Bind(wx.EVT_MENU, self.gui.on_preferences, id=wx.ID_PREFERENCES)
        self.gui.Bind(wx.EVT_MENU, self.gui.on_print_preview, id=wx.ID_PREVIEW_PRINT)
        self.gui.Bind(wx.EVT_MENU, self.gui.on_print, id=wx.ID_PRINT)
        self.gui.Bind(wx.EVT_MENU, self.gui.on_page_setup, id=wx.ID_PRINT_SETUP)
        self.gui.Bind(wx.EVT_MENU, self.gui.on_redo, id=wx.ID_REDO)
        self.gui.Bind(wx.EVT_MENU, self.gui.on_save, id=wx.ID_SAVE)
        self.gui.Bind(wx.EVT_MENU, self.gui.on_save_as, id=wx.ID_SAVEAS)
        self.gui.Bind(wx.EVT_MENU, self.gui.on_undo, id=wx.ID_UNDO)



    def make_closed_tabs_menu(self):
        """
        Recreates the undo tab menu
        """
        for menu in self.closed_tabs_menu.GetMenuItems():
            self.closed_tabs_menu.Remove(menu.GetId())
            self.gui.Unbind(wx.EVT_MENU, id=menu.GetId())

        for x, tab in enumerate(reversed(self.gui.closed_tabs)):
            _id = wx.NewId()
            name = tab['name']
            self.closed_tabs_menu.Append(_id, u"&%i: %s" % (x + 1, name),
                                         _('Restore sheet "%s"') % name)
            func = lambda evt, tab=tab: self.gui.on_undo_tab(tab=tab)
            self.gui.Bind(wx.EVT_MENU, func, id=_id)


    def toggle_fullscreen(self, value):
        menu = self.menu.FindItemById(ID_FULLSCREEN)
        menu.Check(value)

    def remove_all_recent(self):
        for x in self.recent.GetMenuItems():
            self.recent.RemoveItem(x)

    def is_checked(self, _id):
        menu = self.menu.FindItemById(_id)
        return menu.IsChecked()

    def is_file_menu(self, menu):
        return menu == self.file

    def check(self, _id, value):
        self.menu.Check(_id, value)

    def enable(self, _id, value):
        self.menu.Enable(_id, value)

#----------------------------------------------------------------------

class Toolbar(object):
    @staticmethod
    def configure(toolbar, can_paste):
        """
        Configures the GUI's toolbar.
        Move to top/up/down/bottom are created with a custom bitmap.
        """
        logger.debug("Creating the tool bar")        
        _move = [ID_MOVE_UP, ID_MOVE_DOWN, ID_MOVE_TO_BOTTOM, ID_MOVE_TO_TOP]

        ids = [wx.ID_NEW, wx.ID_OPEN, wx.ID_SAVE, wx.ID_COPY, wx.ID_PASTE,
               wx.ID_UNDO, wx.ID_REDO, wx.ID_DELETE]

        arts = [wx.ART_NEW, wx.ART_FILE_OPEN, wx.ART_FILE_SAVE, wx.ART_COPY,
                wx.ART_PASTE, wx.ART_UNDO, wx.ART_REDO, wx.ART_DELETE]
        tips = [_("New Sheet"), _("Open a File"), _("Save Drawing"), _("Copy a Bitmap Selection"),
                _("Paste an Image/Text"), _("Undo the Last Action"), _("Redo the Last Undone Action"),
                _("Delete the currently selected shape"), ("Move Shape Up"), ("Move Shape Down"),
                _("Move Shape To Top"), ("Move Shape To Bottom")]

        ids.extend(_move)
        arts.extend(_move)
        icons = [u"up", u"down", u"top", u"bottom"]

        bmps = {}
        for icon, event_id in zip(icons, _move):
            bmps[event_id] = wx.Bitmap(get_image_path(u"icons", u"move-%s-small" % icon))

        # add tools, add a separator and bind paste/undo/redo for UI updating
        for x, (_id, art_id, tip) in enumerate(zip(ids, arts, tips)):
            if _id in _move:
                art = bmps[_id]
            else:
                art = wx.ArtProvider.GetBitmap(art_id, wx.ART_TOOLBAR)

            toolbar.AddSimpleTool(_id, art, tip)
            # after save and redo
            if x in [2, 6]:
                toolbar.AddSeparator()

        toolbar.EnableTool(wx.ID_PASTE, can_paste)
        toolbar.Realize()