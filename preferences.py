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
from utility import make_bitmap, languages

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
        params = [self.tabs, gui, self.config]
        self.tabs.AddPage(General(*params), _("General"))
        self.tabs.AddPage(FontAndColours(*params), _("Fonts and Color"))
        self.tabs.AddPage(View(*params), _("View"))
        self.tabs.AddPage(PDF(*params), _("PDF Conversion"))

        okay = wx.Button(self, wx.ID_OK, _("&OK"))
        cancel = wx.Button(self, wx.ID_CANCEL, _("&Cancel"))
        help = wx.Button(self, wx.ID_HELP, _("&Help"))
        okay.SetDefault()
        btnSizer = wx.StdDialogButtonSizer()
        btnSizer.AddButton(okay)
        btnSizer.AddButton(cancel)
        btnSizer.Add(help, 0, wx.ALIGN_LEFT | wx.LEFT, 10)
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
        help.Bind(wx.EVT_BUTTON, self.on_help)


    def on_okay(self, event):
        """
        Write the config file - update the *true* config file to new prefs
        Just updates all the GUI instead of figuring out which parts actually
        need updating -- laziness!
        """
        old = self.gui.util.config
        if self.config['language'] != old['language']:
            wx.MessageBox(_("Whyteboard will be translated into %s when restarted")
                          % self.config['language'])

        if self.config['handle_size'] != old['handle_size']:
            tools.HANDLE_SIZE = self.config['handle_size']
            self.gui.board.redraw_all()

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

        undo = wx.StaticText(self, label=_("Number of Recently Closed Sheets"))
        self.undoctrl = wx.SpinCtrl(self, min=5, max=50)
        handle = wx.StaticText(self, label=_("Selection Handle Size"))
        self.handlectrl = wx.SpinCtrl(self, min=3, max=15)

        langText = wx.StaticText(self, label=_("Choose Your Language:"))
        font = langText.GetClassDefaultAttributes().font
        font.SetWeight(wx.FONTWEIGHT_BOLD)
        langText.SetFont(font)
        undo.SetFont(font)
        handle.SetFont(font)

        options = [i[0] for i in languages]
        options.sort()
        self.lang = wx.ComboBox(self, choices=options, style=wx.CB_READONLY)

        if self.config['handle_size']:
            self.handlectrl.SetValue(self.config['handle_size'])
        if self.config['undo_sheets']:
            self.undoctrl.SetValue(self.config['undo_sheets'])
        if self.config['language']:
            self.lang.SetValue(self.config['language'])

        self.lang.Bind(wx.EVT_COMBOBOX, self.on_lang)
        self.undoctrl.Bind(wx.EVT_SPINCTRL, self.on_undo)
        self.handlectrl.Bind(wx.EVT_SPINCTRL, self.on_handle)

        sizer.Add(langText, 0, wx.ALL, 15)
        sizer.Add(self.lang, 0, wx.LEFT, 30)
        sizer.Add(undo, 0, wx.ALL, 15)
        sizer.Add(self.undoctrl, 0, wx.LEFT, 30)
        sizer.Add(handle, 0, wx.ALL, 15)
        sizer.Add(self.handlectrl, 0, wx.LEFT, 30)


    def on_lang(self, event):
        for x in languages:
            if self.lang.GetValue() == x[0]:
                self.config['language'] = x[0]


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
        if os.name == "posix":
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
            if os.name == "nt":
                self.font_label(f) 
                               
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

            self.grid.Remove(self.buttons[id])
            col = make_bitmap(dlg.GetColourData().Colour)
            b = wx.BitmapButton(self, bitmap=col)
            self.buttons[id] = b
            self.grid.Insert(before=id, item=b, proportion=0)

            method = lambda evt, x=id: self.on_colour(evt, x)
            self.buttons[id].Bind(wx.EVT_BUTTON, method)
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
        radio1 = wx.RadioButton(self, label=" " + _("Icons"))
        radio2 = wx.RadioButton(self, label=" " + _("Text"))
        label = wx.StaticText(self, label=_("Toolbox View:"))        
        font = label.GetFont()
        font.SetWeight(wx.FONTWEIGHT_BOLD)
        label.SetFont(font)       
        sizer.Add(label, 0, wx.ALL, 15)
         
        if self.config['toolbox'] == 'icon':
            radio1.SetValue(True)
        else:
            radio2.SetValue(True)        
        if self.config['statusbar']:
            statusbar.SetValue(True)
        if self.config['toolbar']:
            toolbar.SetValue(True)
                    
        for x, btn in enumerate([radio1, radio2]):
           sizer.Add(btn, 0, wx.LEFT, 30)
           sizer.Add((10, 5))
           method = lambda evt, id=x: self.on_view(evt, id)
           btn.Bind(wx.EVT_RADIOBUTTON, method)
           
        sizer.Add((10, 15))
        sizer.Add(statusbar, 0, wx.ALL, 10)
        sizer.Add(toolbar, 0, wx.LEFT, 10)
        statusbar.Bind(wx.EVT_CHECKBOX, self.on_statusbar)
        toolbar.Bind(wx.EVT_CHECKBOX, self.on_toolbar)                        


    def on_statusbar(self, event):
        self.config['statusbar'] = event.Checked()


    def on_toolbar(self, event):
        self.config['toolbar'] = event.Checked()
        
        
    def on_view(self, event, id):
        if id == 0:
            self.config['toolbox'] = 'icon'
        else:
            self.config['toolbox'] = 'text'


#----------------------------------------------------------------------


class PDF(wx.Panel):
    """
    General preferences- language and colour
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
        sizer.Add((10, 5))
        sizer.Add(note, 0, wx.LEFT, 30)

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