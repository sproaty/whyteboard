# -*- coding: utf-8 -*-
#!usr/bin/python

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
This module contains a class which implements Whyteboard's preference dialog.
It has been separated from the dialog module as it may become rather large.

NOTE: A ConfigObj is stored inside my gui class, so the module first creates its
own copy of the obj, so any changes made don't affect the original.

All changes are then written to this object. Only when the user presses ok on
the preferences dialog window will be updated configobj be written to disk and
updates the GUI's config too. The on_okay() method of Preferences updates the
GUI too.

"""

import os
import wx
import lib.flatnotebook as fnb
from copy import copy
from wx.lib.wordwrap import wordwrap as wordwrap


import tools
import whyteboard
from functions import make_bitmap
from utility import languages

_ = wx.GetTranslation

#----------------------------------------------------------------------


class Preferences(wx.Dialog):
    """
    Contains a tabbed bar corresponding to each "page" of different options
    """
    def __init__(self, gui):
        wx.Dialog.__init__(self, gui, title=_("Preferences"), size=(400, 450),
                           style=wx.CLOSE_BOX | wx.CAPTION)
        self.gui = gui
        self.config = copy(gui.util.config)

        sizer = wx.BoxSizer(wx.VERTICAL)
        self.tabs = wx.Notebook(self)
        params = [self.tabs, gui, self.config]
        self.tabs.AddPage(General(*params), _("General"))
        self.tabs.AddPage(FontAndColours(*params), _("Fonts and Color"))
        self.tabs.AddPage(View(*params), _("View"))
        self.tabs.AddPage(PDF(*params), _("PDF Conversion")) 

        okay = wx.Button(self, wx.ID_OK, _("&OK"))
        cancel = wx.Button(self, wx.ID_CANCEL, _("&Cancel"))
        _help = wx.Button(self, wx.ID_HELP, _("&Help"))
        okay.SetDefault()
        btnSizer = wx.StdDialogButtonSizer()
        btnSizer.AddButton(okay)
        btnSizer.AddButton(cancel)
        btnSizer.Add(_help, 0, wx.ALIGN_LEFT | wx.LEFT, 10)
        btnSizer.SetCancelButton(cancel)
        btnSizer.Realize()

        sizer.Add(self.tabs, 2, wx.EXPAND | wx.ALL, 10)
        sizer.Add((10, 10))
        sizer.Add(btnSizer, 0, wx.ALIGN_CENTRE | wx.BOTTOM, 10)
        self.SetSizer(sizer)
        sizer.Layout()
        self.SetFocus()

        cancel.Bind(wx.EVT_BUTTON, self.on_cancel)
        okay.Bind(wx.EVT_BUTTON, self.on_okay)
        _help.Bind(wx.EVT_BUTTON, self.on_help)


    def on_okay(self, event=None):
        """
        Write the config file - update the *true* config file to new prefs
        Just updates all the GUI instead of figuring out which parts actually
        need updating -- laziness!
        """
        old = self.gui.util.config
        if self.config['language'] != old['language']:
            wx.MessageBox(_("Whyteboard will be translated into %s when restarted")
                          % _(self.config['language']))

        if self.config['handle_size'] != old['handle_size']:
            tools.HANDLE_SIZE = self.config['handle_size']

        if self.config['canvas_border'] != old['canvas_border']:
            whyteboard.CANVAS_BORDER = self.config['canvas_border']
            self.gui.board.resize_canvas(self.gui.board.area)


        if self.config.has_key('default_font'):
            if self.config['default_font'] and not self.gui.util.font:
                self.gui.util.font = wx.FFont(0, 0)
                self.gui.util.font.SetNativeFontInfoFromString(self.config['default_font'])

        if self.config['statusbar']:
            self.gui.on_statusbar(None, True)
        else:
            self.gui.on_statusbar(None, False)
        if self.config['toolbar']:
            self.gui.on_toolbar(None, True)
        else:
            self.gui.on_toolbar(None, False)

        self.config.write()
        self.gui.util.config = self.config
        ctrl = self.gui.control

        if self.config['toolbox'] != old['toolbox']:
            ctrl.toolsizer.Clear(True)
            if self.config['toolbox'] == 'text':
                ctrl.toolsizer.SetCols(1)
            else:
                ctrl.toolsizer.SetCols(2)
            ctrl.make_toolbox(self.config['toolbox'])
            ctrl.toolsizer.Layout()

        #  too lazy to check if each colour has changed
        self.gui.board.redraw_all()
        ctrl.grid.Clear(True)
        ctrl.make_colour_grid()
        ctrl.grid.Layout()
        self.Destroy()


    def on_help(self, event=None):
        self.gui.on_help(page="preferences")


    def on_cancel(self, event):
        self.Destroy()

#----------------------------------------------------------------------


class General(wx.Panel):
    """
    Select language and toolbar/status bar visiblity
    """
    def __init__(self, parent, gui, config):
        wx.Panel.__init__(self, parent)
        self.config = config
        self.gui = gui
        if os.name == "posix":
            self.SetBackgroundColour("White")
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)

        # we want to show the translated messages, but keep them in the same
        # order as the English ones, to set the config in English
        self.options = [i[0] for i in languages]
        self.options.sort()
        self.translated = [_(i) for i in self.options]
        translated = list(self.translated)
        translated.sort()
        self.lang = wx.ComboBox(self, choices=translated, style=wx.CB_READONLY)

        undo = wx.StaticText(self, label=_("Number of Recently Closed Sheets"))
        self.undoctrl = wx.SpinCtrl(self, min=5, max=50)
        handle = wx.StaticText(self, label=_("Selection Handle Size"))
        self.handlectrl = wx.SpinCtrl(self, min=3, max=15)

        border = wx.StaticText(self, label=_("Canvas Border"))
        self.borderctrl = wx.SpinCtrl(self, min=10, max=35)

        langText = wx.StaticText(self, label=_("Choose Your Language:"))
        font = langText.GetClassDefaultAttributes().font
        font.SetWeight(wx.FONTWEIGHT_BOLD)
        langText.SetFont(font)
        undo.SetFont(font)
        handle.SetFont(font)
        border.SetFont(font)

        self.handlectrl.SetValue(self.config['handle_size'])
        self.undoctrl.SetValue(self.config['undo_sheets'])
        self.lang.SetValue(_(self.config['language']))
        self.borderctrl.SetValue(self.config['canvas_border'])

        self.lang.Bind(wx.EVT_COMBOBOX, self.on_lang)
        self.undoctrl.Bind(wx.EVT_SPINCTRL, self.on_undo)
        self.handlectrl.Bind(wx.EVT_SPINCTRL, self.on_handle)
        self.borderctrl.Bind(wx.EVT_SPINCTRL, self.on_border)

        sizer.Add(langText, 0, wx.ALL, 15)
        sizer.Add(self.lang, 0, wx.LEFT, 30)
        sizer.Add(undo, 0, wx.ALL, 15)
        sizer.Add(self.undoctrl, 0, wx.LEFT, 30)
        sizer.Add(handle, 0, wx.ALL, 15)
        sizer.Add(self.handlectrl, 0, wx.LEFT, 30)
        sizer.Add(border, 0, wx.ALL, 15)
        sizer.Add(self.borderctrl, 0, wx.LEFT, 30)

    def on_lang(self, event):
        for x, lang in enumerate(self.translated):
            if self.lang.GetValue() == lang:
                self.config['language'] = self.options[x]  # english


    def on_undo(self, event):
        self.config['undo_sheets'] = self.undoctrl.GetValue()

    def on_handle(self, event):
        self.config['handle_size'] = self.handlectrl.GetValue()

    def on_border(self, event):
        self.config['canvas_border'] = self.borderctrl.GetValue()

#----------------------------------------------------------------------


class FontAndColours(wx.Panel):
    """
    Allows the user to select their custom colours for the grid in the left pane
    Their default font may be chosen, too

    Pretty ugly code to  ensure that
    """
    def __init__(self, parent, gui, config):
        wx.Panel.__init__(self, parent)
        if os.name == "posix":
            self.SetBackgroundColour("White")
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.gui = gui
        self.parent = parent
        self.config = config
        self.SetSizer(sizer)
        self.buttons = []
        self.grid = wx.GridSizer(cols=3, hgap=2, vgap=2)

        colours = []
        for x in range(1, 10):
            col = self.config["colour" + str(x)]
            colours.append([int(c) for c in col])

        for x, colour in enumerate(colours):
            method = lambda evt, id=x: self.on_colour(evt, id)
            b = wx.BitmapButton(self, bitmap=make_bitmap(colour))
            self.buttons.append(b)
            self.grid.Add(b, 0)
            b.Bind(wx.EVT_BUTTON, method)
            self.grid.Layout()

        self.button = wx.Button(self, label=_("Select Font"))
        self.button.Bind(wx.EVT_BUTTON, self.on_font)
        font = wx.SystemSettings.GetFont(wx.SYS_SYSTEM_FONT)
        self.font = font  # the correct font, w/ right size
        self.size = font.GetPointSize()  # size to use regardless of font

        labCol = wx.StaticText(self, label=_("Choose Your Custom Colors:"))
        labFont = wx.StaticText(self, label=_("Default Font:"))

        new_font = labFont.GetClassDefaultAttributes().font
        new_font.SetWeight(wx.FONTWEIGHT_BOLD)
        labCol.SetFont(new_font)
        labFont.SetFont(new_font)

        if self.config.has_key('default_font'):
            f = wx.FFont(0, 0)
            f.SetNativeFontInfoFromString(self.config['default_font'])
            self.font = f
            self.button.SetFont(f)
            self.button.SetLabel(self.config['default_font'])
            if os.name == "nt":
                self.font_label(f)

            f = wx.FFont(0, 0)
            f.SetNativeFontInfoFromString(self.config['default_font'])
            f.SetPointSize(self.size)
            self.button.SetFont(f)
        else:
            if os.name == "nt":
                self.font_label(self.font)
            else:
                self.button.SetLabel(self.button.GetFont().GetNativeFontInfoDesc())

        sizer.Add(labCol, 0, wx.ALL, 15)
        sizer.Add(self.grid, 0, wx.LEFT | wx.BOTTOM, 30)
        sizer.Add(labFont, 0, wx.LEFT, 15)
        sizer.Add((10, 15))
        sizer.Add(self.button, 0, wx.LEFT, 30)



    def on_font(self, event):
        """
        Change the font button's font, and text description of the font, but the
        button's font size must not change, or it'll "grow" too big.
        """
        data = wx.FontData()
        data.SetInitialFont(self.font)
        dlg = wx.FontDialog(self, data)

        if dlg.ShowModal() == wx.ID_OK:
            font = dlg.GetFontData().GetChosenFont()
            if os.name == "nt":
                self.font_label(font)
            else:
                self.button.SetLabel(font.GetNativeFontInfoDesc())
            self.font = font

            font2 = dlg.GetFontData().GetChosenFont()
            font2.SetPointSize(self.size)
            self.button.SetFont(font2)
            self.GetSizer().Layout()

            self.config['default_font'] = font.GetNativeFontInfoDesc()

        dlg.Destroy()


    def font_label(self, font):
        """Sets the font label on Windows"""
        size = font.GetPointSize()
        weight = font.GetWeightString()
        style = font.GetStyle()
        w = s = ""

        if weight == "wxBOLD":
            w = "Bold"
        elif weight == "wxLIGHT":
            w = "Light"
        if style == wx.ITALIC:
            s = "Italic"

        self.button.SetLabel("%s %s %s %s" % (font.GetFaceName() , w, s, size))


    def on_colour(self, event, id):
        """
        Change the colour of the selected button. We need to remove the current
        button, create a new one with the newly selected colour, Bind this
        method to that new button and re-layout the sizer
        """
        pref = "colour%s" % (id + 1)
        colour = ([int(c) for c in self.config[pref]])
        data = wx.ColourData()
        data.SetColour(colour)
        dlg = wx.ColourDialog(self, data)

        if dlg.ShowModal() == wx.ID_OK:

            self.config[pref] = list(dlg.GetColourData().Colour.Get())

            #self.grid.Remove(self.buttons[id])
            col = make_bitmap(dlg.GetColourData().Colour)
            self.buttons[id].SetBitmapLabel(col)
            #b = wx.BitmapButton(self, bitmap=col)
            #self.buttons[id] = b
            #self.grid.Insert(before=id, item=b, proportion=0)

            #method = lambda evt, x=id: self.on_colour(evt, x)
            #self.buttons[id].Bind(wx.EVT_BUTTON, method)
            self.grid.Layout()

        dlg.Destroy()


#----------------------------------------------------------------------


class View(wx.Panel):
    """
    Select language and toolbar/status bar visiblity
    """
    def __init__(self, parent, gui, config):
        wx.Panel.__init__(self, parent)
        self.config = config
        self.gui = gui
        if os.name == "posix":
            self.SetBackgroundColour("White")
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)

        statusbar = wx.CheckBox(self, label=_("View the status bar"))
        toolbar = wx.CheckBox(self, label=_("View the toolbar"))
        title = wx.CheckBox(self, label=_("Show the title when printing"))
        radio1 = wx.RadioButton(self, label=" " + _("Icons"))
        radio2 = wx.RadioButton(self, label=" " + _("Text"))
        label = wx.StaticText(self, label=_("Toolbox View:"))

        width = wx.StaticText(self, label=_("Default Canvas Width"))
        self.width = wx.SpinCtrl(self, min=1, max=12000)
        height = wx.StaticText(self, label=_("Default Canvas Height"))
        self.height = wx.SpinCtrl(self, min=1, max=12000)

        font = label.GetFont()
        font.SetWeight(wx.FONTWEIGHT_BOLD)
        label.SetFont(font)
        width.SetFont(font)
        height.SetFont(font)
        sizer.Add(label, 0, wx.ALL, 15)

        if self.config['toolbox'] == 'icon':
            radio1.SetValue(True)
        else:
            radio2.SetValue(True)
        if self.config['statusbar']:
            statusbar.SetValue(True)
        if self.config['toolbar']:
            toolbar.SetValue(True)
        if self.config['print_title']:
            title.SetValue(True)
                        
        self.width.SetValue(self.config['default_width'])
        self.height.SetValue(self.config['default_height'])
        
        for x, btn in enumerate([radio1, radio2]):
            sizer.Add(btn, 0, wx.LEFT, 30)
            sizer.Add((10, 5))
            method = lambda evt, id=x: self.on_view(evt, id)
            btn.Bind(wx.EVT_RADIOBUTTON, method)

        sizer.Add(width, 0, wx.ALL, 15)
        sizer.Add(self.width, 0, wx.LEFT, 30)
        sizer.Add(height, 0, wx.ALL, 15)
        sizer.Add(self.height, 0, wx.LEFT, 30)
        sizer.Add((10, 15))
        sizer.Add(statusbar, 0, wx.ALL, 10)
        sizer.Add(toolbar, 0, wx.LEFT | wx.BOTTOM, 10)
        sizer.Add(title, 0, wx.LEFT, 10)
        statusbar.Bind(wx.EVT_CHECKBOX, self.on_statusbar)
        toolbar.Bind(wx.EVT_CHECKBOX, self.on_toolbar)
        title.Bind(wx.EVT_CHECKBOX, self.on_title)
        self.width.Bind(wx.EVT_SPINCTRL, self.on_width)
        self.height.Bind(wx.EVT_SPINCTRL, self.on_height)


    def on_statusbar(self, event):
        self.config['statusbar'] = event.Checked()

    def on_toolbar(self, event):
        self.config['toolbar'] = event.Checked()
        
    def on_title(self, event):
        self.config['print_title'] = event.Checked()
        
    def on_width(self, event):
        self.config['default_width'] = self.width.GetValue()

    def on_height(self, event):
        self.config['default_height'] = self.height.GetValue()


    def on_view(self, event, id):
        if id == 0:
            self.config['toolbox'] = 'icon'
        else:
            self.config['toolbox'] = 'text'


#----------------------------------------------------------------------


class PDF(wx.Panel):
    """
    PDF conversion quality
    """
    def __init__(self, parent, gui, config):
        wx.Panel.__init__(self, parent)
        self.config = config
        self.gui = gui
        if os.name == "posix":
            self.SetBackgroundColour("White")
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)

        label = wx.StaticText(self, label=_("Conversion Quality:"))
        note = wx.StaticText(self, label=wordwrap(_("Note: Higher quality takes longer to convert"), 350, wx.ClientDC(gui)))
        radio1 = wx.RadioButton(self, label=" " + _("Highest"))
        radio2 = wx.RadioButton(self, label=" " + _("High"))
        radio3 = wx.RadioButton(self, label=" " + _("Normal"))                       

        font = label.GetFont()
        font.SetWeight(wx.FONTWEIGHT_BOLD)
        label.SetFont(font)
        sizer.Add(label, 0, wx.ALL, 15)
        
        for x, btn in enumerate([radio1, radio2, radio3]):
            sizer.Add(btn, 0, wx.LEFT, 30)
            sizer.Add((10, 5))
            method = lambda evt, id=x: self.on_quality(evt, id)
            btn.Bind(wx.EVT_RADIOBUTTON, method)
        
        sizer.Add((10, 10))    
        sizer.Add(note, 0, wx.ALL, 15)

        if self.config['convert_quality'] == 'highest':
            radio1.SetValue(True)
        if self.config['convert_quality'] == 'high':
            radio2.SetValue(True)
        if self.config['convert_quality'] == 'normal':
            radio3.SetValue(True)
            
            

    def on_quality(self, event, id):
        if id == 0:
            self.config['convert_quality'] = 'highest'
        elif id == 1:
            self.config['convert_quality'] = 'high'
        else:
            self.config['convert_quality'] = 'normal'


#----------------------------------------------------------------------                     