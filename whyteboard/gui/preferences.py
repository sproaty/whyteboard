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
This module contains a base Dialog class and several Panel classes that create
Whyteboard's preferences dialog. It has been separated from the dialog module
as it's a large unit of functionality.

NOTE: A ConfigObj is stored inside the GUI, so this module first creates its own
copy of the ConfigObj. All changes are then written to this object. Only when
the user presses ok on the preferences dialog window will be updated configobj
be written to disk and updates the GUI to its new state, and updated its config
file.
"""

import os
import logging
import wx
from copy import copy
from wx.lib.wordwrap import wordwrap as wordwrap

from whyteboard.gui import FindIM
from whyteboard.lib import pub
from whyteboard.misc import meta, create_colour_bitmap, create_bold_font

_ = wx.GetTranslation
logger = logging.getLogger("whyteboard.preferences")

#----------------------------------------------------------------------

class Preferences(wx.Dialog):
    """
    Contains a tabbed bar corresponding to each "page" of different options
    """
    def __init__(self, gui):
        wx.Dialog.__init__(self, gui, title=_("Preferences"), size=(450, 500))
        self.gui = gui
        self.config = copy(gui.util.config)

        sizer = wx.BoxSizer(wx.VERTICAL)
        self.tabs = wx.Notebook(self)
        params = [self.tabs, gui, self.config]
        self.tabs.AddPage(General(*params), _("General"))
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
                          % _(self.config['language']), u"Whyteboard")

        if 'default_font' in self.config:
            if self.config['default_font'] and not self.gui.util.font:
                self.gui.util.font = wx.FFont(1, wx.FONTFAMILY_DEFAULT)
                self.gui.util.font.SetNativeFontInfoFromString(self.config['default_font'])

        # Toggles the items under "View" menu. Ignore the colour grid for now
        for menu_item in ['statusbar', 'toolbar', 'tool_preview']:
            method = getattr(self.gui, "on_" + menu_item)
            if self.config[menu_item]:
                method(None, True)
            else:
                method(None, False)


        self.config.write()
        self.gui.util.config = self.config

        if self.config['bmp_select_transparent'] != old['bmp_select_transparent']:
            self.gui.canvas.copy = None

        if not self.config['tool_preview']:
            self.gui.control.preview.Hide()
        else:
            self.gui.control.preview.Show()
            pub.sendMessage('gui.preview.refresh')

        wx.CallAfter(self.gui.on_colour_grid, None, self.config['colour_grid'])

        #  too lazy to check if each colour has changed - just remake it
        self.gui.canvas.redraw_all()
        self.gui.control.grid.Clear(True)
        self.gui.control.make_colour_grid()
        self.gui.control.grid.Layout()
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
        self.buttons = []
        self.grid = wx.GridSizer(cols=3, hgap=2, vgap=2)

        translated = [i[1] for i in meta.languages]
        translated.sort()
        self.lang = wx.ComboBox(self, choices=translated, style=wx.CB_READONLY, size=(240, 30))
        self.lang.Layout()
        self.lang.SetValue(_(self.config['language']))

        langText = wx.StaticText(self, label=_("Choose Your Language:"))
        labCol = wx.StaticText(self, label=_("Choose Your Custom Colors:"))
        labFont = wx.StaticText(self, label=_("Default Font:"))
        langText.SetFont(create_bold_font())
        labCol.SetFont(create_bold_font())
        labFont.SetFont(create_bold_font())

        colours = []
        for x in range(1, 10):
            col = self.config["colour%s" % x]
            colours.append([int(c) for c in col])

        for x, colour in enumerate(colours):
            method = lambda evt, _id = x: self.on_colour(evt, _id)
            b = wx.BitmapButton(self, bitmap=create_colour_bitmap(colour))
            self.buttons.append(b)
            self.grid.Add(b, 0)
            b.Bind(wx.EVT_BUTTON, method)
            self.grid.Layout()

        self.fontBtn = wx.Button(self, label=_("Select Font"))
        self.fontBtn.Bind(wx.EVT_BUTTON, self.on_font)
        font = wx.SystemSettings.GetFont(wx.SYS_SYSTEM_FONT)
        self.font = font  # the correct font, w/ right size
        self.size = font.GetPointSize()  # size to use regardless of font

        if 'default_font' in self.config:
            f = wx.FFont(1, wx.FONTFAMILY_DEFAULT)
            f.SetNativeFontInfoFromString(self.config['default_font'])
            self.font = f
            self.fontBtn.SetFont(f)
            self.fontBtn.SetLabel(self.config['default_font'])
            if os.name == "nt":
                self.font_label(f)

            f = wx.FFont(1, wx.FONTFAMILY_DEFAULT)
            f.SetNativeFontInfoFromString(self.config['default_font'])
            f.SetPointSize(self.size)
            self.fontBtn.SetFont(f)
        else:
            if os.name == "nt":
                self.font_label(self.font)
            else:
                self.fontBtn.SetLabel(self.fontBtn.GetFont().GetNativeFontInfoDesc())

        sizer.Add(langText, 0, wx.ALL, 15)
        sizer.Add(self.lang, 0, wx.LEFT, 30)
        sizer.Add((10, 15))
        sizer.Add(labCol, 0, wx.ALL, 15)
        sizer.Add(self.grid, 0, wx.LEFT | wx.BOTTOM, 30)
        sizer.Add(labFont, 0, wx.LEFT, 15)
        sizer.Add((10, 15))
        sizer.Add(self.fontBtn, 0, wx.LEFT, 30)
        self.lang.Bind(wx.EVT_COMBOBOX, self.on_lang)



    def on_lang(self, event):
        for lang in meta.languages:
            if self.lang.GetValue() == lang[1]:
                self.config['language'] = lang[0]  # english string

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
                self.fontBtn.SetLabel(font.GetNativeFontInfoDesc())
            self.font = font

            font2 = dlg.GetFontData().GetChosenFont()
            font2.SetPointSize(self.size)
            self.fontBtn.SetFont(font2)
            self.GetSizer().Layout()

            self.config['default_font'] = font.GetNativeFontInfoDesc()

        dlg.Destroy()


    def font_label(self, font):
        """Sets the font label on Windows"""
        size = font.GetPointSize()
        weight = font.GetWeightString()
        style = font.GetStyle()
        w = s = u""

        if weight == "wxBOLD":
            w = _("Bold")
        elif weight == "wxLIGHT":
            w = _("Light")
        if style == wx.ITALIC:
            s = _("Italic")

        self.fontBtn.SetLabel(u"%s %s %s %s" % (font.GetFaceName() , w, s, size))


    def on_colour(self, event, _id):
        """
        Change the colour of the selected button. We need to remove the current
        button's button, recreate it with the new colour and re-layout the sizer
        """
        pref = "colour%s" % (_id + 1)
        colour = ([int(c) for c in self.config[pref]])
        data = wx.ColourData()
        data.SetColour(colour)
        dlg = wx.ColourDialog(self, data)

        if dlg.ShowModal() == wx.ID_OK:
            self.config[pref] = list(dlg.GetColourData().Colour.Get())

            col = create_colour_bitmap(dlg.GetColourData().Colour)
            self.buttons[_id].SetBitmapLabel(col)
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

        self.width = wx.SpinCtrl(self, min=1, max=12000)
        self.height = wx.SpinCtrl(self, min=1, max=12000)

        statusbar = wx.CheckBox(self, label=_("View the status bar"))
        toolbar = wx.CheckBox(self, label=_("View the toolbar"))
        title = wx.CheckBox(self, label=_("Show the title when printing"))
        preview = wx.CheckBox(self, label=_("Show the tool preview"))
        colour = wx.CheckBox(self, label=_("Show the color grid"))
        transparency = wx.CheckBox(self, label=wordwrap(_("Transparent Bitmap Select (may draw slowly)"), 350, wx.ClientDC(self)))

        width = wx.StaticText(self, label=_("Default Canvas Width"))
        height = wx.StaticText(self, label=_("Default Canvas Height"))

        width.SetFont(create_bold_font())
        height.SetFont(create_bold_font())

        if self.config['statusbar']:
            statusbar.SetValue(True)
        if self.config['toolbar']:
            toolbar.SetValue(True)
        if self.config['print_title']:
            title.SetValue(True)
        if self.config['tool_preview']:
            preview.SetValue(True)
        if self.config['colour_grid']:
            colour.SetValue(True)
        if self.config['bmp_select_transparent']:
            transparency.SetValue(True)

        self.width.SetValue(self.config['default_width'])
        self.height.SetValue(self.config['default_height'])

        sizer.Add(width, 0, wx.ALL, 15)
        sizer.Add(self.width, 0, wx.LEFT, 30)
        sizer.Add(height, 0, wx.ALL, 15)
        sizer.Add(self.height, 0, wx.LEFT, 30)
        sizer.Add((10, 15))
        sizer.Add(statusbar, 0, wx.ALL, 10)
        sizer.Add(toolbar, 0, wx.LEFT | wx.BOTTOM, 10)
        sizer.Add(title, 0, wx.LEFT | wx.BOTTOM, 10)
        sizer.Add(preview, 0, wx.LEFT | wx.BOTTOM, 10)
        sizer.Add(colour, 0, wx.LEFT, 10)
        sizer.Add((10, 25))
        sizer.Add(transparency, 0, wx.LEFT, 10)

        statusbar.Bind(wx.EVT_CHECKBOX, self.on_statusbar)
        toolbar.Bind(wx.EVT_CHECKBOX, self.on_toolbar)
        title.Bind(wx.EVT_CHECKBOX, self.on_title)
        preview.Bind(wx.EVT_CHECKBOX, self.on_preview)
        colour.Bind(wx.EVT_CHECKBOX, self.on_colour)

        self.width.Bind(wx.EVT_SPINCTRL, self.on_width)
        self.height.Bind(wx.EVT_SPINCTRL, self.on_height)


    def on_statusbar(self, event):
        self.config['statusbar'] = event.Checked()

    def on_toolbar(self, event):
        self.config['toolbar'] = event.Checked()

    def on_preview(self, event):
        self.config['tool_preview'] = event.Checked()

    def on_colour(self, event):
        self.config['colour_grid'] = event.Checked()

    def on_title(self, event):
        self.config['print_title'] = event.Checked()

    def on_width(self, event):
        self.config['default_width'] = self.width.GetValue()

    def on_height(self, event):
        self.config['default_height'] = self.height.GetValue()

    def on_transparency(self, event):
        self.config['bmp_select_transparent'] = event.Checked()

#----------------------------------------------------------------------


class PDF(wx.Panel):
    """
    PDF conversion quality
    """
    def __init__(self, parent, gui, config):
        wx.Panel.__init__(self, parent)
        self.config = config
        self.gui = gui
        self.im_result = None
        if os.name == "posix":
            self.SetBackgroundColour("White")
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)

        label = wx.StaticText(self, label=_("Conversion Quality:"))
        note = wx.StaticText(self, label=wordwrap(_("Note: Higher quality takes longer to convert"), 350, wx.ClientDC(gui)))
        label.SetFont(create_bold_font())
        sizer.Add(label, 0, wx.ALL, 15)
        
        buttons = {'highest': _("Highest"),
                   'high': _("High"),
                   'normal': _("Normal")}

        for key, value in buttons.items():
            btn = wx.RadioButton(self, label=value)
            sizer.Add(btn, 0, wx.LEFT, 30)
            sizer.Add((10, 5))
            method = lambda evt, x=key: self.on_quality(evt, x)
            btn.Bind(wx.EVT_RADIOBUTTON, method)
            
            if self.config['convert_quality'] == key:
                btn.SetValue(True)

        sizer.Add((10, 10))
        sizer.Add(note, 0, wx.LEFT | wx.BOTTOM, 30)

        if os.name == "nt":
            label_im = wx.StaticText(self, label=_("ImageMagick Location"))
            label_im.SetFont(create_bold_font())
            self.im_button = wx.Button(self)
            self.im_button.Bind(wx.EVT_BUTTON, self.on_im)
            self.set_im_button()

            sizer.Add(label_im, 0, wx.LEFT, 15)
            sizer.Add((10, 15))
            sizer.Add(self.im_button, 0, wx.LEFT, 30)


    def on_quality(self, event, value):
        self.config['convert_quality'] = value


    def set_im_button(self):
        """Sets the label to IM's path"""
        s = _("Find...")
        if "imagemagick_path" in self.config:
            s = self.config["imagemagick_path"]
        self.im_button.SetLabel(s)
        self.GetSizer().Layout()


    def on_im(self, event):
        dlg = FindIM(self, self.gui, self.check_im_path)
        dlg.ShowModal()
        if self.im_result:
            self.config['imagemagick_path'] = self.im_result
        self.set_im_button()


    def check_im_path(self, path):
        _file = os.path.join(path, u"convert.exe")
        if not os.path.exists(_file):
            wx.MessageBox(_('Folder "%s" does not contain convert.exe') % path, u"Whyteboard")
            self.im_result = None
            return False

        self.im_result = path
        return True

#----------------------------------------------------------------------
