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
"""

import os
import sys
import wx
from copy import copy

import tools

from dialogs import FindIM
from utility import make_bitmap

_ = wx.GetTranslation

#----------------------------------------------------------------------


class Preferences(wx.Dialog):
    """
    Contains a tabbed bar corresponding to each "page" of different options
    """
    def __init__(self, gui):
        wx.Dialog.__init__(self, gui, title=_("Preferences"), size=(400, 420),
                           style=wx.CLOSE_BOX | wx.CAPTION)
        self.gui = gui
        self.config = copy(gui.util.config)

        sizer = wx.BoxSizer(wx.VERTICAL)
        self.tabs = wx.Notebook(self)
        self.tabs.AddPage(General(self.tabs, gui, self.config), _("General"))
        self.tabs.AddPage(FontAndColours(self.tabs, gui, self.config), _("Fonts and Color"))
        self.tabs.AddPage(PDF(self.tabs, gui, self.config), _("PDF Conversion"))

        okay = wx.Button(self, wx.ID_OK, _("&OK"))
        cancel = wx.Button(self, wx.ID_CANCEL, _("&Cancel"))
        cancel.SetDefault()
        btnSizer = wx.StdDialogButtonSizer()
        btnSizer.AddButton(okay)
        btnSizer.AddButton(cancel)
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

    def on_okay(self, event):
        """
        Write the config file - update the *true* config file to new prefs
        Just updates all the GUI instead of figuring out which parts actually
        need updating -- laziness!
        """
        if self.config['language'] != self.gui.util.config['language']:
            print self.config['language']
            wx.MessageBox(_("Whyteboard will be translated into %s when restarted")
                          % self.config['language'])

        if self.config['handle_size'] != self.gui.util.config['handle_size']:
            tools.HANDLE_SIZE = self.config['handle_size']
            self.gui.board.redraw_all()


        self.config.write()
        self.gui.util.config = self.config

        if self.config['statusbar']:
            self.gui.on_statusbar( None, True)
        else:
            self.gui.on_statusbar(None, False)
        if self.config['toolbar']:
            self.gui.on_toolbar(None, True)
        else:
            self.gui.on_toolbar(None, False)

        ctrl = self.gui.control
        ctrl.grid.Clear(True)
        ctrl.make_colour_grid()
        ctrl.grid.Layout()
        self.Destroy()


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
        self.SetBackgroundColour("White")
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)

        undo = wx.StaticText(self, label=_("Number of Recently Closed Sheets"))
        self.undoctrl = wx.SpinCtrl(self, min=5, max=50)
        handle = wx.StaticText(self, label=_("Selection Handle Size"))
        self.handlectrl = wx.SpinCtrl(self, min=3, max=15)

        langText = wx.StaticText(self, label=_("Choose Your Language:"))
        statusbar = wx.CheckBox(self, label=_("View the status bar"))
        toolbar = wx.CheckBox(self, label=_("View the toolbar"))
        font = langText.GetClassDefaultAttributes().font
        font.SetWeight(wx.FONTWEIGHT_BOLD)
        langText.SetFont(font)
        undo.SetFont(font)
        handle.SetFont(font)

        welsh = wx.LANGUAGE_WELSH
        if os.name == "posix":
            welsh = wx.LANGUAGE_WELSH

        self.choices = [ ["English", wx.LANGUAGE_ENGLISH],
                         [ "Dutch" , wx.LANGUAGE_DUTCH ],
                         [ "German" , wx.LANGUAGE_GERMAN ],
                         [ "Spanish" , wx.LANGUAGE_SPANISH ],
                         [ "Welsh" , welsh ],
                         [ "Czech" , wx.LANGUAGE_CZECH ],
                         [ "Italian" , wx.LANGUAGE_ITALIAN ] ]

        options = [_(i[0]) for i in self.choices]
        options.sort()
        self.lang = wx.ComboBox(self, choices=options, style=wx.CB_READONLY)

        if self.config['statusbar']:
            statusbar.SetValue(True)
        if self.config['toolbar']:
            toolbar.SetValue(True)
        if self.config['handle_size']:
            self.handlectrl.SetValue(self.config['handle_size'])
        if self.config['undo_sheets']:
            self.undoctrl.SetValue(self.config['undo_sheets'])
        if self.config['language']:
            self.lang.SetValue(self.config['language'])

        self.lang.Bind(wx.EVT_COMBOBOX, self.on_lang)
        statusbar.Bind(wx.EVT_CHECKBOX, self.on_statusbar)
        toolbar.Bind(wx.EVT_CHECKBOX, self.on_toolbar)
        self.undoctrl.Bind(wx.EVT_SPINCTRL, self.on_undo)
        self.handlectrl.Bind(wx.EVT_SPINCTRL, self.on_handle)

        sizer.Add(langText, 0, wx.ALL, 15)
        sizer.Add(self.lang, 0, wx.LEFT, 30)
        sizer.Add(undo, 0, wx.ALL, 15)
        sizer.Add(self.undoctrl, 0, wx.LEFT, 30)
        sizer.Add(handle, 0, wx.ALL, 15)
        sizer.Add(self.handlectrl, 0, wx.LEFT, 30)
        sizer.Add((10, 8))
        sizer.Add(statusbar, 0, wx.ALL, 10)
        sizer.Add(toolbar, 0, wx.LEFT, 10)


    def on_lang(self, event):
        for x in self.choices:
            if self.lang.GetValue() == x[0]:
                self.config['language'] = x[0]


    def on_statusbar(self, event):
        self.config['statusbar'] = event.Checked()


    def on_toolbar(self, event):
        self.config['toolbar'] = event.Checked()


    def on_undo(self, event):
        self.config['undo_sheets'] = self.undoctrl.GetValue()


    def on_handle(self, event):
        self.config['handle_size'] = self.handlectrl.GetValue()


#----------------------------------------------------------------------


class FontAndColours(wx.Panel):
    """
    Allows the user to select their custom colours for the grid in the left pane
    Their default font may be chosen, too

    Pretty ugly code to  ensure that
    """
    def __init__(self, parent, gui, config):
        wx.Panel.__init__(self, parent)
        self.SetBackgroundColour("White")
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.gui = gui
        self.parent = parent
        self.config = config
        self.SetSizer(sizer)
        self.buttons = []

        self.grid = wx.GridSizer(cols=3, hgap=2, vgap=2)
        self.button = wx.Button(self, label=_("Select Font"))
        self.button.Bind(wx.EVT_BUTTON, self.on_font)

        font = wx.SystemSettings.GetFont(wx.SYS_SYSTEM_FONT)
        self.font = font  # the correct font, w/ right size
        self.size = font.GetPointSize()  # size to use regardless of font

        if self.config.has_key('default_font'):
            f = wx.FFont(0, 0)
            f.SetNativeFontInfoFromString(self.config['default_font'])
            self.font = f
            self.button.SetFont(f)
            self.button.SetLabel(self.config['default_font'])

            f = wx.FFont(0, 0)
            f.SetNativeFontInfoFromString(self.config['default_font'])
            f.SetPointSize(self.size)
            self.button.SetFont(f)
        else:
            self.button.SetLabel(self.button.GetFont().GetNativeFontInfoDesc())

        labCol = wx.StaticText(self, label=_("Choose Your Custom Colors:"))
        labFont = wx.StaticText(self, label=_("Default Font:"))

        colours = []
        for x in range(1, 10):
            col= self.config["colour"+str(x)]
            colours.append([int(c) for c in col])

        for x, colour in enumerate(colours):
            method = lambda evt, id=x: self.on_colour(evt, id)
            b = wx.BitmapButton(self, bitmap=make_bitmap(colour))
            self.buttons.append(b)
            self.grid.Add(b, 0)
            b.Bind(wx.EVT_BUTTON, method)

        sizer.Add(labCol, 0, wx.ALL, 15)
        sizer.Add(self.grid, 0, wx.LEFT | wx.BOTTOM, 30)
        sizer.Add(labFont, 0, wx.LEFT, 15)
        sizer.Add((10, 15))
        sizer.Add(self.button, 0, wx.LEFT, 30)

        font = wx.Font(self.size, font.GetFamily(), font.GetStyle(), wx.FONTWEIGHT_BOLD)
        labCol.SetFont(font)
        labFont.SetFont(font)


    def on_font(self, event):
        """
        Change the font button's font, and text description of the font, but the
        button's font size must not change, or it'll "grow" too big.
        """
        data = wx.FontData()
        data.SetInitialFont(self.font)
        print self.font.GetPointSize()
        dlg = wx.FontDialog(self, data)

        if dlg.ShowModal() == wx.ID_OK:
            font = dlg.GetFontData().GetChosenFont()
            #if os.name == "nt":
            #w = font.GetWeightString()
            #if w == wx.FONTST
            #    name = font.GetFaceName() + " " + font.GetWeight(), font.GetPointSize()
            #else:
            self.button.SetLabel(font.GetNativeFontInfoDesc())
            self.font = font

            font2 = dlg.GetFontData().GetChosenFont()
            font2.SetPointSize(self.size)
            self.button.SetFont(font2)
            self.GetSizer().Layout()

            self.config['default_font'] = font.GetNativeFontInfoDesc()

        dlg.Destroy()


    def on_colour(self, event, id):
        """
        Change the colour of the selected button. We need to remove the current
        button, create a new one with the newly selected colour, Bind this
        method to that new button and re-layout the sizer
        """
        dlg = wx.ColourDialog(self)
        if dlg.ShowModal() == wx.ID_OK:

            #print
            string = "colour%s" % (id + 1)
            self.config[string] = list(dlg.GetColourData().Colour.Get())

            self.grid.Remove(self.buttons[id])
            col = make_bitmap(dlg.GetColourData().Colour)
            b = wx.BitmapButton(self, bitmap=col)
            self.buttons[id] = b
            self.grid.Insert(before=id, item=b, proportion=0)

            method = lambda evt, x=id: self.on_colour(evt, x)
            self.buttons[id].Bind(wx.EVT_BUTTON, method)
            self.grid.Layout()


        dlg.Destroy()


##----------------------------------------------------------------------


class PDF(wx.Panel):
    """
    General preferences- language and colour
    """
    def __init__(self, parent, gui, config):
        wx.Panel.__init__(self, parent)
        self.config = config
        self.gui = gui
        self.buttons = []  # radio buttons
        self.SetBackgroundColour("White")
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)

        label = wx.StaticText(self, label=_("Conversion Quality:"))
        note = wx.StaticText(self, label=_("Note: Higher quality takes longer to convert"))
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
           self.buttons.append(btn)
        sizer.Add((10, 5))
        sizer.Add(note, 0, wx.LEFT, 30)

        #if os.name == "nt":
        im_label = wx.StaticText(self, label=_("ImageMagick's Location:"))
        im_label.SetFont(font)
        im_button = wx.Button(self, label=_("Find..."))
        im_button.Bind(wx.EVT_BUTTON, self.find_imagemagick)
        sizer.Add((10, 5))
        sizer.Add(im_label, 0, wx.ALL | wx.TOP, 15)
        sizer.Add(im_button, 0, wx.LEFT, 30)

        if self.config['convert_quality'] == 'highest':
            self.buttons[0].SetValue(True)
        if self.config['convert_quality'] == 'high':
            self.buttons[1].SetValue(True)
        if self.config['convert_quality'] == 'normal':
            self.buttons[2].SetValue(True)


    def find_imagemagick(self, event):
        dlg = FindIM(self, self.gui)
        dlg.ShowModal()
        #self.gui.util.prompt_for_im()

    def on_quality(self, event, id):
        if id == 0:
            self.config['convert_quality'] = 'highest'
        elif id == 1:
            self.config['convert_quality'] = 'high'
        else:
            self.config['convert_quality'] = 'normal'


#----------------------------------------------------------------------