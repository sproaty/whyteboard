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
This module implements the Whyteboard application.  It takes a Canvas class
and wraps it in a GUI with a menu, toolbar, statusbar and some control panels.

The GUI acts as a controller for the application - it delegates method calls
to the appropriate classes when certain actions take place.
"""

from __future__ import with_statement

import os
import sys
import shutil
import time
import logging

import wx
import wx.lib.newevent
from wx.html import HtmlHelpController

from whyteboard.lib import ConfigObj, Validator, icon, fnb, pub
from whyteboard.misc import Utility, meta
from whyteboard.tools import Highlighter, EDGE_LEFT, EDGE_TOP

from whyteboard.gui import (Canvas, CanvasDropTarget, ControlPanel, MediaPanel,
                            Menu, Preferences, Print, SidePanel, ShapePopup,
                            SheetsPopup, Toolbar)

from whyteboard.gui import (ExceptionHook, AboutDialog, Feedback, FindIM, History,
                            PDFCacheDialog, ProgressDialog, PromptForSave,
                            Resize, ShapeViewer, TextInput, UpdateDialog)

from whyteboard.gui import (ID_BACKGROUND, ID_CLOSE_ALL, ID_COLOUR_GRID, ID_DESELECT,
                       ID_FOREGROUND, ID_MOVE_UP, ID_MOVE_DOWN, ID_MOVE_TO_TOP,
                       ID_MOVE_TO_BOTTOM, ID_NEXT, ID_PASTE_NEW, ID_PREV,
                       ID_RECENTLY_CLOSED, ID_STATUSBAR, ID_SWAP_COLOURS,
                       ID_TOOL_PREVIEW, ID_TOOLBAR, ID_TRANSPARENT, ID_UNDO_SHEET)

from whyteboard.misc import (get_home_dir, is_save_file, get_clipboard,
                             check_clipboard, download_help_files, file_dialog,
                             get_path, set_clipboard, show_dialog, open_url,
                             new_instance, help_file_path)


_ = wx.GetTranslation
logger = logging.getLogger("whyteboard.frame")
PASTE_CHECK_COUNT = 7  # only check clipboard every x value of EVT_UPDATE_MENU
SCROLL_AMOUNT = 3
UNDO_SHEET_COUNT = 10

#----------------------------------------------------------------------

class GUI(wx.Frame):
    """
    This class contains a ControlPanel, a Canvas frame and a SidePanel
    and manages their layout with a wx.BoxSizer.  A menu, toolbar and associated
    event handlers call the appropriate functions of other classes.
    """
    title = u"Whyteboard"
    LoadEvent, LOAD_DONE_EVENT = wx.lib.newevent.NewEvent()

    def __init__(self, config):
        """
        Initialise utility, status/menu/tool bar, tabs, ctrl panel + bindings.
        """
        wx.Frame.__init__(self, None, title=_("Untitled") + u" - %s" % self.title)
        self.util = Utility(self, config)

        self._oldhook = sys.excepthook
        sys.excepthook = ExceptionHook

        meta.find_transparent()  # important
        logger.info("Transparency supported: %s", meta.transparent)
        
        if meta.transparent:
            try:
                x = self.util.items.index(Highlighter)
            except ValueError:
                self.util.items.insert(1, Highlighter)

        self.can_paste = check_clipboard()
        self.process = None
        self.pid = None
        self.dialog = None
        self.convert_cancelled = False
        self.shape_viewer_open = False
        self.help = None
        self.hotkey_pressed = False  # for hotkey timer
        self.hotkey_timer = None
        self.tab_count = 1
        self.tab_total = 1
        self.current_tab = 0
        self.closed_tabs = []
        self.hotkeys = []

        style = (fnb.FNB_X_ON_TAB | fnb.FNB_NO_X_BUTTON | fnb.FNB_VC8 |
                 fnb.FNB_DROPDOWN_TABS_LIST | fnb.FNB_MOUSE_MIDDLE_CLOSES_TABS |
                 fnb.FNB_NO_NAV_BUTTONS)

        self.control = ControlPanel(self)
        self.tabs = fnb.FlatNotebook(self, agwStyle=style)
        self.canvas = Canvas(self.tabs, self, (config['default_width'], config['default_height']))
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

        self.paste_check_count = PASTE_CHECK_COUNT - 1
        wx.UpdateUIEvent.SetUpdateInterval(75)
        #wx.UpdateUIEvent.SetMode(wx.UPDATE_UI_PROCESS_SPECIFIED)

        self.SetIcon(icon.getIcon())
        self.SetExtraStyle(wx.WS_EX_PROCESS_UI_UPDATES)
        self.SetDropTarget(CanvasDropTarget())
        self.statusbar = self.CreateStatusBar()
        self._print = Print(self)

        self.filehistory = wx.FileHistory(8)
        self.load_history_file()
        self.filehistory.Load(self.config)

        self.menu = Menu(self)
        self.toolbar = Toolbar.create(self)
        self.SetMenuBar(self.menu.menu)
        self.set_menu_from_config()
        self.do_bindings()
        self.find_help()

        pub.sendMessage('thumbs.update_current')
        self.update_panels(True)
        wx.CallAfter(self.UpdateWindowUI)


    def __del__(self):
        sys.excepthook = self._oldhook

    def do_bindings(self):
        """
        Performs event binding.
        """
        logger.debug("Beginning frame event bindings")
        self.Bind(fnb.EVT_FLATNOTEBOOK_PAGE_CHANGED, self.on_change_tab)
        self.Bind(fnb.EVT_FLATNOTEBOOK_PAGE_CONTEXT_MENU, self.tab_popup)
        self.Bind(fnb.EVT_FLATNOTEBOOK_PAGE_DROPPED, self.on_drop_tab)
        self.Bind(self.LOAD_DONE_EVENT, self.on_done_load)
        self.Bind(wx.EVT_CHAR_HOOK, self.hotkey)
        self.Bind(wx.EVT_CLOSE, self.on_exit)
        self.Bind(wx.EVT_END_PROCESS, self.on_end_process)  # end pdf conversion
        self.menu.bindings()

        topics = {'shape.add': self.shape_add,
                  'shape.popup': self.shape_popup,
                  'shape.selected': self.shape_selected,
                  'canvas.capture_mouse': self.capture_mouse,
                  'canvas.change_tool': self.pubsub_change_tool,
                  'canvas.paste_image': self.paste_image,
                  'canvas.paste_text': self.paste_text,
                  'canvas.release_mouse': self.release_mouse,
                  'gui.mark_unsaved': self.mark_unsaved,
                  'gui.open_file': self.open_file,
                  'media.create_panel': self.make_media_panel,
                  'text.show_dialog': self.show_text_dialog}
        [pub.subscribe(value, key) for key, value in topics.items()]

        logger.debug("Setting up tool hotkeys")
        self.hotkeys = [x.hotkey for x in self.util.items]
        ac = []
        if os.name == "nt":
            for x, item in enumerate(self.util.items):
                hotkey_event = lambda evt, y = x + 1, k = item.hotkey: self.on_change_tool(evt, y, key=k)
                _id = wx.NewId()
                ac.append((wx.ACCEL_NORMAL, ord(item.hotkey.upper()), _id))
                self.Bind(wx.EVT_MENU, hotkey_event, id=_id)
        else:
            ac = [(wx.ACCEL_CTRL, ord(u'\t'), ID_NEXT),
                  (wx.ACCEL_CTRL | wx.ACCEL_SHIFT, ord(u'\t'), ID_PREV) ]

        tbl = wx.AcceleratorTable(ac)
        self.SetAcceleratorTable(tbl)


    def set_menu_from_config(self):
        """
        Sets up the program's initial menu state from the config parameters
        """
        values = {ID_TOOLBAR: u'toolbar', ID_STATUSBAR: u'statusbar',
                ID_TOOL_PREVIEW: u'tool_preview', ID_COLOUR_GRID: u'colour_grid'}
        for _id, config_key in values.items():
            if self.util.config[config_key]:
                self.menu.check(_id, True)
            else:
                getattr(self, u"on_" + config_key)(None, False)


    def shape_selected(self, shape):
        """
        Shape getting selected (by Select tool)
        """
        self.canvas.select_shape(shape)
        change = (shape.background == wx.TRANSPARENT)
        self.util.transparent = change
        self.control.transparent.SetValue(change)

    def make_media_panel(self, size, media):
        media.mc = MediaPanel(self.canvas, size, media)

    def release_mouse(self):
        self.canvas.release_mouse()

    def shape_popup(self, shape):
        logger.debug("Showing pop up for %s", shape)
        self.PopupMenu(ShapePopup(self.canvas, self, shape))

    def capture_mouse(self):
        self.canvas.capture_mouse()

    def shape_add(self, shape):
        self.canvas.add_shape(shape)

    def on_save(self, event=None):
        """
        Saves file if filename is set, otherwise calls 'save as'.
        """
        logger.debug("Saving file.")
        if not self.util.filename:  # no wtbd file active, prompt for location
            logger.info("Prompting for filename")
            self.on_save_as()
        else:
            self.util.save_file()


    def on_save_as(self, event=None):
        """
        Prompts for the filename and location to save to.
        """
        wildcard = _("Whyteboard file ") + u"(*.wtbd)|*.wtbd"
        _dir = self.util.config.get('last_opened_dir') or u""
        _file = self.util.filename
        if not _file:
            _file = time.strftime(u"%x %X")
            _file = _file.replace(u":", u"-").replace(u"/", u"-")

        name = file_dialog(self, _("Save Whyteboard As..."),
                           wx.SAVE | wx.OVERWRITE_PROMPT, wildcard, _dir, _file)
        if name:
            if not os.path.splitext(name)[1]:  # no file extension
                name += u'.wtbd'

            if is_save_file(name):
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
            wildcard = wildcard[wildcard.find(_(u"Image Files")) :
                                wildcard.find(u"|" + _(u'Whyteboard files')) ]  # image to page
        elif text:
            wildcard = wildcard[wildcard.find(u"PDF/PS/SVG") :
                                wildcard.find(u"*.SVG|")]  # page descriptions

        _dir = self.util.config.get('last_opened_dir') or u""

        filename = file_dialog(self, _("Open file..."), wx.OPEN, wildcard, _dir)
        if filename:
            self.open_file(filename)


    def open_file(self, filename):
        if filename:
            if is_save_file(filename):
                logger.debug("File open with unsaved changes, prompting for save")
                self.prompt_for_save(self.do_open, args=[filename])
            else:
                self.do_open(filename)


    def do_open(self, filename):
        """
        Updates the appropriate variables in the utility class and loads
        the selected file.
        """
        logger.info("Opening file [%s]", filename)
        self.filehistory.AddFileToHistory(filename)
        self.filehistory.Save(self.config)
        self.config.Flush()
        self.util.save_last_path(filename)

        if is_save_file(filename):
            self.util.load_wtbd(filename)
        else:
            self.util.temp_file = filename
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
            self.show_progress_dialog(_("Converting..."), True, True)

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
            config = ConfigObj(filename, configspec=meta.config_scheme)
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
        preferences_file = os.path.join(get_home_dir(), u"user.pref")
        logger.debug("Reloading preference file [%s]", preferences_file)
        if os.path.exists(preferences_file):
            config = ConfigObj(preferences_file, configspec=meta.config_scheme)
            validator = Validator()
            config.validate(validator)
            pref = Preferences(self)
            pref.config = config
            pref.config.filename = preferences_file
            pref.on_okay()


    def export_prompt(self):
        """
        Find out the filename to save to
        """
        val = None  # return value
        wildcard = (u"PNG (*.png)|*.png|JPEG (*.jpg, *.jpeg)|*.jpeg;*.jpg|" +
                    u"BMP (*.bmp)|*.bmp|TIFF (*.tiff)|*.tiff")

        filename = file_dialog(self, _("Export data to..."),
                           wx.SAVE | wx.OVERWRITE_PROMPT, wildcard)
        if filename:
            _name = os.path.splitext(filename)[1].replace(u".", u"")
            types = {0: u"png", 1: u"jpg", 2: u"bmp", 3: u"tiff"}

            if not os.path.splitext(filename)[1]:
                _name = types[dlg.GetFilterIndex()]
                filename += u"." + _name
                val = filename
            if not _name in meta.types[2:]:
                wx.MessageBox(u"%s .%s" % (_("Invalid filetype to export as:"), _name),
                              u"Whyteboard")
            else:
                val = filename
        return val


    def on_new_tab(self, event=None, name=None, wb=None):
        """
        Opens a new tab, selects it, creates a new thumbnail and tree item
        name: unique name, sent by PDF convert/load file.
        wb: Passed by undo_tab to ensure the tab total is correct
        """
        if not wb:
            self.tab_total += 1
        if not name:
            name = u"%s %s" % (_("Sheet"), self.tab_total)
        logger.debug("Opening new sheet [%s]", name)

        self.tab_count += 1
        self.thumbs.new_thumb(name=name)
        self.notes.add_tab(name)
        self.tabs.AddPage(Canvas(self.tabs, self, (self.util.config['default_width'],
                                                   self.util.config['default_height'])), name)

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
        self.control.change_tool()  # updates canvas' shape

        if self.notes.tabs:
            tree_id = self.notes.tabs[self.current_tab]
            self.notes.tree.SelectItem(tree_id, True)
        pub.sendMessage('update_shape_viewer')



    def prompt_for_save(self, method, style=wx.YES_NO | wx.CANCEL, args=None):
        """
        Ask the user to save, quit or cancel (quitting) if they haven't saved.
        Can be called through "Update", "Open (.wtbd)", or "Exit". If updating,
        don't show a cancel button, and explicitly restart if the user cancels
        out of the "save file" dialog
        method(*args) specifies the action to perform if user selects yes or no
        """
        if not args:
            args = []

        if not self.util.saved:
            name = _("Untitled")
            if self.util.filename:
                name = os.path.basename(self.util.filename)

            dialog = PromptForSave(self, name, method, style, args)
            dialog.ShowModal()

        else:
            method(*args)
            if method == self.Destroy:
                logger.info("Program exiting.")
                sys.exit()


    def prompt_for_im(self):
        dlg = FindIM(self.util, self, self.util.check_im_path)
        dlg.ShowModal()


    def on_drop_tab(self, event):
        """
        Update the thumbs/notes so that they're poiting to the new tab position.
        Show a progress dialog, as all thumbnails must be updated.
        """
        if event.GetSelection() == event.GetOldSelection():
            return

        self.show_progress_dialog(_("Loading..."))
        self.dialog.Show()
        self.on_change_tab()

        pub.sendMessage('sheet.move', event=event, tab_count=self.tab_count)
        self.on_done_load()
        wx.MilliSleep(100)  # try and stop user dragging too many tabs quickly
        wx.SafeYield()
        pub.sendMessage('update_shape_viewer')


    def update_panels(self, select):
        """Updates thumbnail panel's text"""
        pub.sendMessage('thumbs.text.highlight', tab=self.current_tab,
                        select=select)


    def on_close_tab(self, event=None):
        """
        Closes the current tab (if there are any to close).
        """
        if not self.tab_count - 1:
            return

        self.tab_count -= 1
        self.notes.remove_tab(self.current_tab)
        self.thumbs.remove(self.current_tab)

        for x in self.canvas.medias:
            x.remove_panel()
        self.create_sheet_undo_point(self.canvas, self.current_tab)

        if os.name == "posix":
            self.tabs.RemovePage(self.current_tab)
        else:
            self.tabs.DeletePage(self.current_tab)

        self.on_change_tab()  # updates self.canvas


    def create_sheet_undo_point(self, canvas, tab_number, recreate_menu=True):
        """
        Creates an undo entry for a tab that's being closed
        """
        if len(self.closed_tabs) == UNDO_SHEET_COUNT:
            del self.closed_tabs[0]

        item = {'shapes': canvas.shapes,
                'undo': canvas.undo_list,
                'redo': canvas.redo_list,
                'size': canvas.area,
                'name': self.tabs.GetPageText(tab_number),
                'medias': canvas.medias,
                'viewport': canvas.GetViewStart()}

        self.closed_tabs.append(item)
        if recreate_menu:
            self.menu.make_closed_tabs_menu()


    def on_close_all_sheets(self, event=None):
        """
        Closes every sheet, creating undo points for each one.
        """
        if not self.tab_count - 1:  # must have at least one sheet open
            return

        for x in reversed(range(self.tab_count)):
            self.create_sheet_undo_point(self.tabs.GetPage(x), x, False)

        self.menu.make_closed_tabs_menu()
        self.remove_all_sheets()
        self.on_new_tab()


    def remove_all_sheets(self):
        self.canvas.shapes = []
        self.canvas.redraw_all()
        self.tabs.DeleteAllPages()
        self.thumbs.remove_all()
        self.notes.remove_all()
        self.tab_count = 0
        self.tab_total = 0


    def on_undo_tab(self, event=None, tab=None):
        """
        Undoes the last closed tab from the list.
        Re-creates the canvas from the saved shapes/undo/redo lists
        """
        if not self.closed_tabs:
            return
        if not tab:
            tab = self.closed_tabs.pop()
        else:
            tab = self.closed_tabs.pop(self.closed_tabs.index(tab))

        self.on_new_tab(name=tab['name'], wb=True)
        self.canvas.restore_sheet(tab['shapes'], tab['undo'], tab['redo'],
                                  tab['size'], tab['medias'], tab['viewport'])
        pub.sendMessage('update_shape_viewer')
        self.menu.make_closed_tabs_menu()


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


    def load_recent_files(self, event):
        """
        Re-creates the Recent Files menu by reloading the config file.
        """
        if self.menu.is_file_menu(event.GetMenu()):
            self.menu.remove_all_recent()
            self.load_history_file()
            self.filehistory.Load(self.config)
        event.Skip()  # otherwise interferes with EVT_UPDATE_UI


    def update_menus(self, event):
        """
        Enables/disables GUI menus and toolbar items.
        It uses a counter for the clipboard check as it can be too performance
        intense and cause segmentation faults
        """
        canvas = self.canvas
        if not canvas:
            return
        _id = event.GetId()

        if _id in [wx.ID_PASTE, ID_PASTE_NEW]:  # check this less frequently, possibly expensive
            self.paste_check_count += 1
            if self.paste_check_count == PASTE_CHECK_COUNT:
                self.can_paste = False

            if check_clipboard():
                self.can_paste = True
                self.paste_check_count = 0
                try:
                    self.menu.enable(ID_PASTE_NEW, self.can_paste)
                    self.menu.enable(wx.ID_PASTE, self.can_paste)
                except wx.PyDeadObjectError:
                    pass
            return

        if _id == ID_TRANSPARENT:
            if canvas.can_swap_transparency():
                if canvas.is_transparent():
                    event.Check(True)
                else:
                    event.Check(False)
                event.Enable(True)
            else:
                event.Enable(False)
            return

        do = False
        if _id == wx.ID_REDO and canvas.redo_list:
            do = True
        elif _id == wx.ID_UNDO and canvas.undo_list:
            do = True
        elif _id == ID_PREV and self.current_tab:
            do = True
        elif (_id == ID_NEXT and self.can_change_next_sheet()):
            do = True
        elif _id in [wx.ID_CLOSE, ID_CLOSE_ALL] and self.tab_count > 1:
            do = True
        elif _id in [ID_UNDO_SHEET, ID_RECENTLY_CLOSED] and self.closed_tabs:
            do = True
        elif _id in [wx.ID_DELETE, ID_DESELECT, ID_FOREGROUND] and canvas.selected:
            do = True
        elif _id == ID_MOVE_UP and canvas.check_move(u"up"):
            do = True
        elif _id == ID_MOVE_DOWN and canvas.check_move(u"down"):
            do = True
        elif _id == ID_MOVE_TO_TOP and canvas.check_move(u"top"):
            do = True
        elif _id == ID_MOVE_TO_BOTTOM and canvas.check_move(u"bottom"):
            do = True
        elif _id in [ID_SWAP_COLOURS, ID_BACKGROUND] and canvas.can_swap_colours():
            do = True
        elif _id == wx.ID_COPY:
            if canvas:
                if canvas.copy:
                    do = True
        event.Enable(do)



    def can_change_next_sheet(self):
        return self.tab_count > 1 and self.current_tab + 1 < self.tab_count

    def on_delete_shape(self, event=None):
        self.canvas.delete_selected()

    def on_deselect_shape(self, event=None):
        self.canvas.deselect_shape()

    def on_copy(self, event):
        set_clipboard(self.canvas.get_selection_bitmap())

    def paste_image(self, bitmap, x, y, ignore=False):
        self.canvas.paste_image(bitmap, x, y, ignore)

    def paste_text(self, text, x, y):
        self.canvas.paste_text(text, x, y, self.util.colour)

    def on_paste_new(self, event):
        """ Pastes the text/image into a new tab """
        self.on_new_tab()
        self.on_paste(ignore=True)

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
            x, y = self.canvas.get_mouse_position()

        if isinstance(data, wx.TextDataObject):
            self.paste_text(data.GetText(), x, y)
        else:
            self.paste_image(data.GetBitmap(), x, y, ignore)


    def on_change_tool(self, event, _id, key):
        """ Change tool -- used when being used as a hotkey """
        if self.canvas.is_not_drawing():
            logger.debug("Hotkey [%s] pressed, changing tools", key)
            self.control.change_tool(_id=_id)

    def pubsub_change_tool(self, new=None):
        if self.canvas:
            self.change_tool(new)


    def change_tool(self, new=None, canvas=None):
        if not canvas:
            canvas = self.canvas

        self.util.change_tool(canvas, new)
        canvas.change_tool()
        pub.sendMessage('gui.preview.refresh')


    def on_fullscreen(self, event=None, val=None):
        """ Toggles fullscreen. val forces fullscreen on/off """
        flag = wx.FULLSCREEN_NOBORDER | wx.FULLSCREEN_NOCAPTION | wx.FULLSCREEN_NOSTATUSBAR
        if not val:
            val = not self.IsFullScreen()

        self.ShowFullScreen(val, flag)
        self.menu.toggle_fullscreen(val)


    def hotkey(self, event=None):
        """
        Checks for hotkeys to either change tools or to move the canvas'
        viewport. Checks for the arrow keys to move shapes about.
        """
        code = event.GetKeyCode()
        if os.name == "posix":
            for x, key in enumerate(self.hotkeys):

                if code in [ord(key), ord(key.upper())]:                    
                    self.on_change_tool(None, _id=x + 1, key=key)
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
        pub.sendMessage('update_shape_viewer')


    def get_canvases(self):
        return [self.tabs.GetPage(x) for x in range(self.tab_count)]

    def get_tab_names(self):
        return [self.tabs.GetPageText(x) for x in range(self.tab_count)]

    def get_background_colour(self):
        return self.control.get_background_colour()

    def get_colour(self):
        return self.control.get_colour()

    def toggle_control(self, menu, control, force=None):
        """Menu ID to check, enable/disable; view: Control to show/hide"""
        val = self.get_toggle_value(menu, force)
        control.Show(val)
        self.menu.check(menu, val)
        self.SendSizeEvent()

    def get_toggle_value(self, menu, force):
        val = False
        if self.menu.is_checked(menu) or force:
            val = True
        if force is False:
            val = False
        return val

    def on_toolbar(self, event=None, force=None):
        self.toggle_control(ID_TOOLBAR, self.toolbar, force)

    def on_tool_preview(self, event=None, force=None):
        self.toggle_control(ID_TOOL_PREVIEW, self.control.preview, force)

    def on_statusbar(self, event=None, force=None):
        self.toggle_control(ID_STATUSBAR, self.statusbar, force)


    def on_colour_grid(self, event=None, force=None):
        val = self.get_toggle_value(ID_COLOUR_GRID, force)
        self.control.toggle_colour_grid(val)
        self.menu.check(ID_COLOUR_GRID, val)
        pub.sendMessage('gui.preview.refresh')


    def convert_dialog(self, cmd):
        """Called when the PDF convert process begins"""
        self.process = wx.Process(self)
        self.pid = wx.Execute(cmd, wx.EXEC_ASYNC, self.process)
        self.show_progress_dialog(_("Converting..."), True, True)


    def on_end_process(self, event=None):
        """ Destroy the progress process after Convert finishes """
        self.process.Destroy()
        self.dialog.Destroy()
        del self.process
        self.pid = None


    def show_text_dialog(self, text):
        dlg = TextInput(self, text=text)
        if dlg.ShowModal() == wx.ID_CANCEL:
            self.canvas.text = None
            self.canvas.redraw_all()
            self.pubsub_change_tool()
            return False

        dlg.transfer_data(self)  # grab font and text data


    def show_text_edit_dialog(self, text_shape):
        dlg = TextInput(self, text_shape)
        if dlg.ShowModal() == wx.ID_CANCEL:
            return False
        dlg.transfer_data(text_shape)  # grab font and text data
        return True


    def show_progress_dialog(self, title, cancellable=False, modal=False):
        self.dialog = ProgressDialog(self, title, cancellable)
        if modal:
            self.dialog.ShowModal()
        else:
            self.dialog.Show()


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
            self.filehistory.Save(self.config)
            self.config.Flush()
            return

        self.filehistory.AddFileToHistory(path)  # move up the list
        self.open_file(path)


    def on_exit(self, event=None):
        logger.info("User requested application to exit.")
        self.prompt_for_save(self.Destroy)

    def tab_popup(self, event):
        self.PopupMenu(SheetsPopup(self, self, event.GetSelection()))

    def on_undo(self, event=None):
        self.canvas.undo()

    def on_redo(self, event=None):
        self.canvas.redo()

    def on_move_top(self, event=None):
        self.canvas.move_top(self.canvas.selected)

    def on_move_bottom(self, event=None):
        self.canvas.move_bottom(self.canvas.selected)

    def on_move_up(self, event=None):
        self.canvas.move_up(self.canvas.selected)

    def on_move_down(self, event=None):
        self.canvas.move_down(self.canvas.selected)


    def on_previous_sheet(self, event=None):
        if not self.current_tab:
            return
        self.tabs.SetSelection(self.current_tab - 1)
        self.on_change_tab()

    def on_next_sheet(self, event=None):
        if not self.can_change_next_sheet():
            return
        self.tabs.SetSelection(self.current_tab + 1)
        self.on_change_tab()


    def on_clear(self, event=None):
        self.canvas.clear(keep_images=True)

    def on_clear_all(self, event=None):
        self.canvas.clear()
        self.thumbs.update_all()

    def on_clear_sheets(self, event=None):
        for tab in range(self.tab_count):
            self.tabs.GetPage(tab).clear(keep_images=True)


    def on_clear_all_sheets(self, event=None):
        for tab in range(self.tab_count):
            self.tabs.GetPage(tab).clear()
        self.thumbs.update_all()


    def on_foreground(self, event):
        self.canvas.change_colour()

    def on_background(self, event):
        self.canvas.change_background()

    def on_refresh(self):
        self.thumbs.update_all()

    def on_transparent(self, event=None):
        self.canvas.toggle_transparent()

    def on_swap_colours(self, event=None):
        self.canvas.swap_colours()

    def on_page_setup(self, evt):
        self._print.page_setup()

    def on_print_preview(self, event):
        self._print.print_preview()

    def on_print(self, event):
        self._print.do_print()

    def on_new_win(self, event=None):
        new_instance()

    def on_translate(self, event):
        open_url(u"https://translations.launchpad.net/whyteboard")

    def on_report_bug(self, event):
        open_url(u"https://bugs.launchpad.net/whyteboard")

    def on_resize(self, event=None):
        show_dialog(Resize(self))

    def on_preferences(self, event=None):
        show_dialog(Preferences(self))

    def on_update(self, event=None):
        show_dialog(UpdateDialog(self))

    def on_history(self, event=None):
        show_dialog(History(self))

    def on_pdf_cache(self, event=None):
        show_dialog(PDFCacheDialog(self, self.util.library))

    def on_feedback(self, event):
        show_dialog(Feedback(self), False)

    def load_history_file(self):
        self.config = wx.Config(u"Whyteboard", style=wx.CONFIG_USE_LOCAL_FILE)


    def on_shape_viewer(self, event=None):
        if not self.shape_viewer_open:
            self.shape_viewer_open = True
            show_dialog(ShapeViewer(self), False)


    def mark_unsaved(self):
        if self.util.saved:
            self.util.saved = False
            self.SetTitle(u"*" + self.GetTitle())


    def find_help(self):
        """Locate the help files, update self.help var"""
        self.help = None

        if os.path.exists(help_file_path()):
            self.help = HtmlHelpController()
            self.help.AddBook(help_file_path())


    def on_help(self, event=None, page=None):
        """
        Shows the help file, if it exists, otherwise prompts the user to
        download it.
        """
        if self.help and os.path.exists(help_file_path()):
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
        inf.Copyright = u"© 2009-2011 Steven Sproat"
        inf.Description = _("A simple whiteboard and PDF annotator")
        inf.Developers = [u"Steven Sproat <sproaty@gmail.com>"]
        inf.Translators = meta.translators
        inf.WebSite = (u"http://www.whyteboard.org", u"http://www.whyteboard.org")
        inf.Licence = u"GPL 3"
        license = os.path.join(get_path(), u"LICENSE.txt")
        if os.path.exists(license):
            with open(license) as f:
                inf.Licence = f.read()

        if os.name == "nt":
            AboutDialog(self, inf)
        else:
            wx.AboutBox(inf)