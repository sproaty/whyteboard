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
Popup menu items.
"""

import wx

from whyteboard.gui import (ID_BACKGROUND, ID_CLOSE_ALL, ID_FOREGROUND, ID_MOVE_DOWN,
                       ID_MOVE_TO_BOTTOM, ID_MOVE_TO_TOP, ID_MOVE_UP, ID_SWAP_COLOURS,
                       ID_TRANSPARENT)

_ = wx.GetTranslation

#----------------------------------------------------------------------

class Popup(wx.Menu):
    """
    A general pop-up menum providing default menu items. Easy to subclass to add
    new functionality. The "extra" (of type wx.Event*) variable must be passed
    around a lot as different subclasses access different functions of different
    events e.g. a TreeCtrl event to get its item, or a notebook tab change event
    """
    def __init__(self, parent, gui, extra):
        wx.Menu.__init__(self)
        self.parent = parent
        self.gui = gui
        self.item = None
        self.set_item(extra)
        self.make_menu(extra)

    def make_menu(self, extra):
        SELECT, RENAME, EXPORT = wx.NewId(), wx.NewId(), wx.NewId()

        self.Append(SELECT, _("&Select"))
        self.AppendSeparator()
        self.Append(wx.ID_NEW, _("&New Sheet"))
        self.Append(wx.ID_CLOSE, _("Re&move Sheet"))
        self.Append(ID_CLOSE_ALL, _("Close All Sheets"))
        self.AppendSeparator()
        self.Append(RENAME, _("&Rename..."))
        self.Append(EXPORT, _("&Export..."))

        self.Bind(wx.EVT_MENU, self.select_tab_method(extra), id=SELECT)
        self.Bind(wx.EVT_MENU, self.rename, id=RENAME)
        self.Bind(wx.EVT_MENU, self.export, id=EXPORT)
        self.Bind(wx.EVT_MENU, self.close, id=wx.ID_CLOSE)
        self.Bind(wx.EVT_MENU, self.close_all, id=ID_CLOSE_ALL)


    def select_tab_method(self, extra):
        """Guess this is the class' interface..."""
        pass

    def set_item(self, extra):
        self.item = extra

    def close(self, event):
        self.gui.current_tab = self.item
        self.gui.canvas = self.gui.tabs.GetPage(self.item)
        self.gui.on_close_tab()

    def close_all(self, event):
        self.gui.on_close_all_sheets()

    def export(self, event):
        """
        Change canvas temporarily to 'trick' the gui into exporting the selected
        tab. Then, restore the GUI to the correct one
        """
        canvas = self.gui.canvas  # reference to restore
        self.gui.canvas = self.gui.tabs.GetPage(self.item)
        self.gui.on_export()
        self.gui.canvas = canvas

    def rename(self, event):
        self.gui.on_rename(sheet=self.item)


#----------------------------------------------------------------------


class NotesPopup(Popup):
    """
    Parent = Notes panel - needs access to tree's events and methods. Overwrites
    the menu for a note, adding in extra items
    """
    def make_menu(self, extra):
        if self.item is None:  # root node
            return
        if isinstance(self.item, int):  # sheet node
            super(NotesPopup, self).make_menu(extra)
        else:
            SELECT, EDIT, DELETE = wx.NewId(), wx.NewId(), wx.NewId()
            text = _("&Select")

            if self.item.selected:
                text = _("De&select")
            self.Append(SELECT, text)
            self.Append(EDIT, _("&Edit Note..."))
            self.AppendSeparator()
            self.Append(DELETE, _("&Delete"))

            self.Bind(wx.EVT_MENU, lambda x: self.parent.select(extra), id=SELECT)
            self.Bind(wx.EVT_MENU, self.select_tab_method(extra), id=EDIT)
            self.Bind(wx.EVT_MENU, lambda x: self.parent.delete(extra), id=DELETE)


    def select_tab_method(self, extra):
        return lambda x: self.parent.on_click(extra)

    def set_item(self, extra):
        self.item = self.parent.tree.GetPyData(extra.GetItem())

#----------------------------------------------------------------------


class SheetsPopup(Popup):
    """
    Brought up by right-clicking the tab list. Its parent is the GUI
    """
    def select_tab_method(self, extra):
        return lambda x: self.bleh()

    def bleh(self):
        self.parent.tabs.SetSelection(self.item)
        self.parent.on_change_tab()


#----------------------------------------------------------------------


class ShapePopup(Popup):
    """
    Brought up by right-clicking on a shape with the Select tool
    """
    def make_menu(self, extra):
        SELECT, EDIT, POINT = wx.NewId(), wx.NewId(), wx.NewId()

        self.SetTitle(_(self.item.name))
        text, _help = _("&Select"), _("Selects this shape")
        if self.item.selected:
            text, _help = _("De&select"), _("Deselects this shape")
        self.Append(SELECT, text, _help)

        self.Append(EDIT, _("&Edit..."), _("Edit the text"))
        self.Append(POINT, _("&Add New Point"), _("Adds a new point to the Polygon"))
        self.Append(wx.ID_DELETE, _("&Delete"))
        self.AppendSeparator()
        self.AppendCheckItem(ID_TRANSPARENT, _("T&ransparent"))
        self.Append(ID_FOREGROUND, _("&Color..."))
        self.Append(ID_BACKGROUND, _("&Background Color..."))
        self.Append(ID_SWAP_COLOURS, _("Swap &Colors"))
        self.AppendSeparator()
        self.Append(ID_MOVE_UP, _("Move &Up"))
        self.Append(ID_MOVE_DOWN, _("Move &Down"))
        self.Append(ID_MOVE_TO_TOP, _("Move To &Top"))
        self.Append(ID_MOVE_TO_BOTTOM, _("Move To &Bottom"))

        if not self.item.name in [u"Text", u"Note"]:
            self.Enable(EDIT, False)
        if not self.item.name == u"Polygon":
            self.Enable(POINT, False)

        self.Bind(wx.EVT_MENU, lambda x: self.select(), id=SELECT)
        self.Bind(wx.EVT_MENU, lambda x: self.edit(), id=EDIT)
        self.Bind(wx.EVT_MENU, lambda x: self.add_point(), id=POINT)


    def edit(self):
        self.item.edit()

    def select(self, draw=True):
        if not self.item.selected:
            self.gui.canvas.deselect_shape()
            self.item.selected = True
            self.gui.canvas.selected = self.item
        else:
            self.gui.canvas.deselect_shape()

        if draw:
            self.gui.canvas.redraw_all()


    def add_point(self):
        self.gui.canvas.add_undo()
        self.item.points = list(self.item.points)
        x, y = self.gui.canvas.ScreenToClient(wx.GetMousePosition())
        x, y = self.gui.canvas.CalcUnscrolledPosition(x, y)
        self.item.points.append((float(x), float(y)))
        self.gui.canvas.redraw_all()

#----------------------------------------------------------------------

class ThumbsPopup(SheetsPopup):
    """
    Just need to set the item to the current tab number. parent: thumb panel
    """
    def bleh(self,):
        self.parent.gui.tabs.SetSelection(self.item)
        self.parent.gui.on_change_tab()

#----------------------------------------------------------------------