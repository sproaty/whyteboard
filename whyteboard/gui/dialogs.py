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
This module contains classes extended from wx.Dialog used by the GUI.
"""

from __future__ import division
from __future__ import with_statement

import os
import sys
import zipfile
import time
import wx
import wx.lib.mixins.listctrl as listmix

from urllib import urlopen, urlretrieve, urlencode

from whyteboard.lib import BaseErrorDialog, pub
import whyteboard.tools as tools

from whyteboard.misc import meta
from whyteboard.misc import (get_home_dir, bitmap_button, is_exe, extract_tar,
                       fix_std_sizer_tab_order, format_bytes, version_is_greater,
                       get_image_path)
_ = wx.GetTranslation

#----------------------------------------------------------------------

class History(wx.Dialog):
    """
    Creates a history replaying dialog and methods for its functionality
    """
    def __init__(self, gui):
        wx.Dialog.__init__(self, gui, title=_("History Player"), size=(400, 200),
                           style=wx.CLOSE_BOX | wx.CAPTION)
        self.gui = gui
        self.looping = False
        self.paused = False
        #count = 0
        #for x in gui.canvas.shapes:
        #    if isinstance(x, tools.Pen):
        #        count += len(x.points)
        #_max = len(gui.canvas.shapes) + count

        #self.slider = wx.Slider(self, minValue=1, maxValue=_max,
        #                        style=wx.SL_AUTOTICKS | wx.SL_HORIZONTAL | wx.SL_LABELS)
        #self.slider.SetTickFreq(5, 1)

        self.playButton = bitmap_button(self, get_image_path(u"icons", u"play"), True, toggle=True)
        self.pauseButton = bitmap_button(self, get_image_path(u"icons", u"pause"), True, toggle=True)
        self.stopButton = bitmap_button(self, get_image_path(u"icons", u"stop"), True, toggle=True)
        closeButton = wx.Button(self, wx.ID_CANCEL, _("&Close"))

        sizer = wx.BoxSizer(wx.VERTICAL)
        historySizer = wx.BoxSizer(wx.HORIZONTAL)
        historySizer.Add(self.playButton, 0,  wx.ALL, 2)
        historySizer.Add(self.pauseButton, 0,  wx.ALL, 2)
        historySizer.Add(self.stopButton, 0,  wx.ALL, 2)

        #sizer.Add(self.slider, 0, wx.EXPAND | wx.ALL, 10)
        sizer.Add(historySizer, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALL, 13)
        sizer.Add((10, 5))
        sizer.Add(closeButton, 0, wx.ALIGN_CENTRE | wx.BOTTOM, 13)
        self.SetSizer(sizer)
        sizer.Fit(self)
        self.SetFocus()
        self.toggle_buttons()

        self.playButton.Bind(wx.EVT_BUTTON, self.play)
        self.pauseButton.Bind(wx.EVT_BUTTON, self.pause)
        self.stopButton.Bind(wx.EVT_BUTTON, self.stop)
        self.Bind(wx.EVT_CLOSE, self.on_close)
        closeButton.Bind(wx.EVT_BUTTON, self.on_close)
        #self.slider.Bind(wx.EVT_SCROLL, self.scroll)


    def play(self, event):
        """
        Starts the replay if it's not already started, unpauses if paused
        """
        if self.looping:
            self.paused = False
            self.toggle_buttons(True, False, False)
            return
        if self.paused:
            self.paused = False

        tmp_shapes = list(self.gui.canvas.shapes)
        shapes = []
        for shape in tmp_shapes:
            if not isinstance(shape, tools.Image):
                shapes.append(shape)

        if shapes:
            self.toggle_buttons(True, False, False)
            self.looping = True
            self.draw(shapes)


    def draw(self, shapes):
        """
        Replays the users' last-drawn pen strokes.
        The loop can be paused/unpaused by the user.
        """
        dc = wx.ClientDC(self.gui.canvas)
        dc.SetBackground(wx.WHITE_BRUSH)
        buff = self.gui.canvas.buffer
        bkgregion = wx.Region(0, 0, buff.GetWidth(), buff.GetHeight())

        dc.SetClippingRegionAsRegion(bkgregion)
        dc.Clear()
        self.gui.canvas.PrepareDC(dc)

        #  paint any images first
        for s in self.gui.canvas.shapes:
            if isinstance(s, tools.Image):
                s.draw(dc)

        for pen in shapes:
            # draw pen outline
            if isinstance(pen, tools.Pen):
                if isinstance(pen, tools.Highlighter):
                    gc = wx.GraphicsContext.Create(dc)
                    colour = (pen.colour[0], pen.colour[1], pen.colour[2], 50)
                    gc.SetPen(wx.Pen(colour, pen.thickness))
                    path = gc.CreatePath()
                else:
                    dc.SetPen(wx.Pen(pen.colour, pen.thickness))

                for x, p in enumerate(pen.points):
                    if self.looping and not self.paused:
                        try:
                            wx.MilliSleep((pen.time[x + 1] - pen.time[x]) * 950)
                            wx.Yield()
                        except IndexError:
                            pass

                        if isinstance(pen, tools.Highlighter):
                            path.MoveToPoint(p[0], p[1])
                            path.AddLineToPoint(p[2], p[3])
                            gc.DrawPath(path)
                        else:
                            dc.DrawLine(p[0], p[1], p[2], p[3])
                    else:  # loop is paused, wait for unpause/close/stop
                        while self.paused:
                            wx.MicroSleep(100)
                            wx.Yield()
            else:
                if self.looping and not self.paused:
                    wx.MilliSleep(350)
                    wx.Yield()
                    pen.draw(dc, True)

                else:  # loop is paused, wait for unpause/close/stop
                    while self.paused:
                        wx.MicroSleep(100)
                        wx.Yield()

        self.stop()  # restore other drawn items


    def pause(self, event=None):
        """Pauses/unpauses the replay."""
        if self.looping:
            self.paused = not self.paused
            self.toggle_buttons(not self.paused, self.paused, False)


    def stop(self, event=None):
        """Stops the replay."""
        if self.looping or self.paused:
            self.toggle_buttons(False, False, True)
            self.looping = False
            self.paused = False
            self.gui.canvas.Refresh()  # restore


    def on_close(self, event=None):
        """
        Called when the dialog is closed; stops the replay and ends the modal
        view, allowing the GUI to Destroy() the dialog.
        """
        self.stop()
        self.EndModal(1)

    def scroll(self, event):
        self.pause()


    def toggle_buttons(self, play=False, pause=False, stop=True):
        """
        Toggles the buttons on/off as indicated by the bool params
        """
        self.playButton.SetValue(play)
        self.pauseButton.SetValue(pause)
        self.stopButton.SetValue(stop)


#----------------------------------------------------------------------

class ProgressDialog(wx.Dialog):
    """
    Shows a Progres Gauge while an operation is taking place. May be cancellable
    which is possible when converting pdf/ps
    """
    def __init__(self, gui, title, cancellable=False):
        """Defines a gauge and a timer which updates the gauge."""
        wx.Dialog.__init__(self, gui, title=title, style=wx.CAPTION)
        self.gui = gui
        self.timer = wx.Timer(self)
        self.gauge = wx.Gauge(self, range=100, size=(180, 30))
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.gauge, 0, wx.ALL, 10)

        if cancellable:
            cancel = wx.Button(self, wx.ID_CANCEL, _("&Cancel"))
            cancel.SetDefault()
            cancel.Bind(wx.EVT_BUTTON, self.on_cancel)
            btnSizer = wx.StdDialogButtonSizer()
            btnSizer.AddButton(cancel)
            btnSizer.Realize()
            sizer.Add(btnSizer, 0, wx.ALIGN_CENTER | wx.TOP | wx.BOTTOM, 10)

        self.SetSizer(sizer)
        sizer.Fit(self)
        self.SetFocus()

        self.Bind(wx.EVT_TIMER, self.on_timer, self.timer)
        self.timer.Start(95)


    def on_timer(self, event):
        """Increases the gauge's progress."""
        self.gauge.Pulse()


    def on_cancel(self, event):
        """Cancels the conversion process"""
        self.SetTitle(_("Cancelling..."))
        self.FindWindowById(wx.ID_CANCEL).Disable()
        self.timer.Stop()
        self.gui.convert_cancelled = True
        if os.name == "nt":
            wx.Kill(self.gui.pid, wx.SIGKILL)
        else:
            wx.Kill(self.gui.pid)


#----------------------------------------------------------------------


class UpdateDialog(wx.Dialog):
    """
    Updates Whyteboard. First, connect to server, parse HTML to check for new
    version. Then, when the user clicks update, fetch the file and show the
    download progress. Then, depending on exe/python source, we update the
    program accordingly
    """
    def __init__(self, gui):
        """
        Builds the UI - then wx.CallAfter()s the update check to the server
        """
        wx.Dialog.__init__(self, gui, title=_("Updates"), size=(350, 200))
        self.gui = gui
        self.downloaded = 0
        self.new_version = None
        self._file = None
        self._type = None

        self.text = wx.StaticText(self, label=_("Connecting to server..."),
                                  size=(300, 80))
        self.text2 = wx.StaticText(self, label="")  # for download progress
        self.btn = wx.Button(self, wx.ID_OK, _("Update"))
        cancel = wx.Button(self, wx.ID_CANCEL, _("&Cancel"))
        self.btn.Enable(False)
        self.btn.SetDefault()
        btnSizer = wx.StdDialogButtonSizer()
        btnSizer.AddButton(cancel)
        btnSizer.AddButton(self.btn)
        btnSizer.SetCancelButton(cancel)
        btnSizer.Realize()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.text, 0, wx.LEFT | wx.TOP | wx.RIGHT, 10)
        sizer.Add(self.text2, 0, wx.LEFT | wx.RIGHT, 10)
        sizer.Add((10, 20))
        sizer.Add(btnSizer, 0, wx.ALIGN_CENTRE)
        self.SetSizer(sizer)
        self.SetFocus()

        self.btn.Bind(wx.EVT_BUTTON, self.update)
        wx.CallAfter(self.check)  # we want to show the dialog *then* fetch URL


    def check(self):
        """
        Parses the "control" file giving information about the latest release
        """
        try:
            f = urlopen("http://whyteboard.org/latest")
        except IOError:
            self.text.SetLabel(_("Could not connect to server."))
            return
        html = f.read().split(u"\n")
        f.close()
        self.new_version = html[0]

        if version_is_greater(meta.version, self.new_version):
            self.text.SetLabel(_("You are running the latest version."))
            return

        self._file, size = html[3], html[4]
        self._type = u".tar.gz"

        if os.name == "nt" and is_exe():
            self._file, size = html[1], html[2]
            self._type = u".zip"

        s = (_("There is a new version available, %(version)s\nFile: %(filename)s\nSize: %(filesize)s")
             % {'version': html[0], 'filename': self._file, 'filesize': format_bytes(size)} )
        self.text.SetLabel(s)
        self.btn.Enable(True)
        self._file = u"http://whyteboard.googlecode.com/files/%s" % self._file



    def update(self, event=None):
        """
        Updates the program by downloading the correct file and extracting it.
        On Linux, the Tar file is extracted into the current directory, and on
        Windows the .exe is renamed, the new one renamed to replace it and on
        both platforms the program is then restarted (after asking the user to
        save or not)
        """
        path = self.gui.util.path
        args = []  # args to reload running program, may include filename
        tmp = None
        tmp_file = os.path.join(path[0], u'tmp-wb-' + self._type)

        try:
            tmp = urlretrieve(self._file, tmp_file, self.reporter)
        except IOError:
            self.text.SetLabel(_("Could not connect to server."))
            self.btn.SetLabel(_("Retry"))
            return

        if os.name == "nt" and is_exe():
            os.rename(path[1], u"wtbd-bckup.exe")
            _zip = zipfile.ZipFile(tmp_file)
            _zip.extractall()
            _zip.close()
            os.remove(tmp_file)
            wb = os.path.abspath(sys.argv[0])
            args = [wb, [wb]]
        else:
            if os.name == "posix":
                os.system(u"tar -xf %s --strip-components=1" % tmp[0])
            else:
                extract_tar(self.gui.util.path[0], os.path.abspath(tmp[0]),
                            self.new_version, meta.backup_extension)
            os.remove(tmp[0])
            args = [u'python', [u'python', sys.argv[0]]]  # for os.execvp

        if self.gui.util.filename:
            name = u'"%s"' % self.gui.util.filename  # gotta escape for Windows
            args[1].append(u"-f")
            args[1].append(name)  # restart, load .wtbd
        self.gui.prompt_for_save(os.execvp, wx.YES_NO, args)


    def reporter(self, count, block, total):
        self.downloaded += block

        self.text2.SetLabel(_("Downloaded %s of %s") %
                            (format_bytes(self.downloaded), format_bytes(total)))


#----------------------------------------------------------------------


class TextInput(wx.Dialog):
    """
    Shows a text input screen, updates the canvas' text as text is being input
    and has methods for
    """
    def __init__(self, gui, note=None, text=u""):
        """
        Standard constructor - sets text to supplied text variable, if present.
        """
        wx.Dialog.__init__(self, gui, title=_("Enter text"),
              style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER | wx.WANTS_CHARS, size=(350, 280))

        self.ctrl = wx.TextCtrl(self, style=wx.TE_MULTILINE, size=(300, 120))
        fontBtn = wx.Button(self, label=_("Select Font"))
        self.colourBtn = wx.ColourPickerCtrl(self)
        self.okButton = wx.Button(self, wx.ID_OK, _("&OK"))
        self.okButton.SetDefault()
        self.cancelButton = wx.Button(self, wx.ID_CANCEL, _("&Cancel"))

        extent = self.ctrl.GetFullTextExtent(u"Hy")
        lineHeight = extent[1] + extent[3]
        self.ctrl.SetSize(wx.Size(-1, lineHeight * 4))

        if not gui.util.font:
            gui.util.font = self.ctrl.GetFont()
        self.gui = gui
        self.note = None
        self.colour = gui.util.colour
        gap = wx.LEFT | wx.TOP | wx.RIGHT
        font = gui.util.font

        if note:
            self.note = note
            self.colour = note.colour
            text = note.text
            font = wx.FFont(1, 1)
            font.SetNativeFontInfoFromString(note.font_data)

        self.set_text_colour(text)
        self.ctrl.SetFont(font)
        self.colourBtn.SetColour(self.colour)

        _sizer = wx.BoxSizer(wx.HORIZONTAL)
        _sizer.Add(fontBtn, 0, wx.RIGHT, 5)
        _sizer.Add(self.colourBtn, 0)
        btnSizer = wx.StdDialogButtonSizer()
        btnSizer.AddButton(self.okButton)
        btnSizer.AddButton(self.cancelButton)
        btnSizer.Realize()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.ctrl, 1, gap | wx.EXPAND, 10)
        sizer.Add(_sizer, 0, wx.ALIGN_RIGHT | wx.RIGHT | wx.LEFT | wx.TOP, 10)
        sizer.Add((10, 10))  # Spacer.
        sizer.Add(btnSizer, 0, wx.BOTTOM | wx.ALIGN_CENTRE, 10)
        self.SetSizer(sizer)
        fix_std_sizer_tab_order(btnSizer)

        self.set_focus()
        self.Bind(wx.EVT_BUTTON, self.on_font, fontBtn)
        self.Bind(wx.EVT_COLOURPICKER_CHANGED, self.on_colour, self.colourBtn)
        self.Bind(wx.EVT_TEXT, self.update_canvas, self.ctrl)

        ac = [(wx.ACCEL_CTRL, wx.WXK_RETURN, self.okButton.GetId())]
        tbl = wx.AcceleratorTable(ac)
        self.SetAcceleratorTable(tbl)

        if text:
            self.update_canvas()
            self.gui.canvas.redraw_all(True)


    def on_font(self, evt):
        """
        Shows the font dialog, sets the input text's font and returns focus to
        the text input box, at the user's selected point.
        """
        data = wx.FontData()
        data.SetInitialFont(self.ctrl.GetFont())
        dlg = wx.FontDialog(self, data)

        if dlg.ShowModal() == wx.ID_OK:
            data = dlg.GetFontData()
            self.gui.util.font = data.GetChosenFont()
            self.ctrl.SetFont(self.gui.util.font)
            self.set_text_colour()
            self.update_canvas() # Update dialog with new text height
        dlg.Destroy()
        self.set_focus()


    def on_colour(self, event):
        """Change text colour to the chosen one"""
        self.colour = event.GetColour()
        self.set_text_colour()
        self.update_canvas()
        self.set_focus()

    def set_text_colour(self, text=None):
        """Updates (or forces...) the text colour"""
        if not text:
            text = self.ctrl.GetValue()
        self.ctrl.SetValue("")
        self.ctrl.SetForegroundColour(self.colour)
        self.ctrl.SetValue(text)

    def set_focus(self):
        """Gives the text focus, places the cursor at the end of the text"""
        self.ctrl.SetFocus()
        self.ctrl.SetInsertionPointEnd()


    def update_canvas(self, event=None):
        """Updates the canvas with the inputted text"""
        if self.note:
            shape = self.note
            canvas = shape.canvas
        else:
            canvas = self.gui.canvas
            shape = canvas.shape
        self.transfer_data(shape)

        shape.find_extent()
        canvas.redraw_all()  # stops overlapping text


    def transfer_data(self, text_obj):
        """Transfers the dialog's data to an object."""
        text_obj.text = self.ctrl.GetValue()
        text_obj.font = self.ctrl.GetFont()
        text_obj.colour = self.colour


#----------------------------------------------------------------------

class FindIM(wx.Dialog):
    """
    Asks a user for the location of ImageMagick (Windows-only)
    Method is called on the ok button (for preference use)
    """
    def __init__(self, parent, gui, method):
        wx.Dialog.__init__(self, gui, title=_("ImageMagick Notification"))
        self.gui = gui
        self.method = method
        self.path = u"C:/Program Files/"

        t = (_("Whyteboard uses ImageMagick to load PDF, SVG and PS files. \nPlease select its installed location."))
        text = wx.StaticText(self, label=t)
        btn = wx.Button(self, label=_("Find location..."))
        gap = wx.LEFT | wx.TOP | wx.RIGHT

        self.okButton = wx.Button(self, wx.ID_OK, _("&OK"))
        self.okButton.SetDefault()
        self.cancelButton = wx.Button(self, wx.ID_CANCEL, _("&Cancel"))
        btnSizer = wx.StdDialogButtonSizer()
        btnSizer.AddButton(self.okButton)
        btnSizer.AddButton(self.cancelButton)
        btnSizer.Realize()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(text, 1, gap | wx.EXPAND, 10)
        sizer.Add(btn, 0, gap | wx.ALIGN_CENTRE, 20)
        sizer.Add((10, 20)) # Spacer.
        sizer.Add(btnSizer, 0, wx.BOTTOM | wx.ALIGN_CENTRE, 12)
        self.SetSizer(sizer)
        sizer.Fit(self)
        self.SetFocus()

        btn.Bind(wx.EVT_BUTTON, self.browse)
        self.okButton.Bind(wx.EVT_BUTTON, self.ok)
        self.cancelButton.Bind(wx.EVT_BUTTON, self.cancel)


    def browse(self, event=None):
        dlg = wx.DirDialog(self, _("Choose a directory"), self.path, style=wx.DD_DIR_MUST_EXIST)

        if dlg.ShowModal() == wx.ID_OK:
            self.path = dlg.GetPath()
        else:
            dlg.Destroy()

    def ok(self, event=None):
        if self.method(self.path):
            self.Close()

    def cancel(self, event=None):
        self.Close()

#----------------------------------------------------------------------

class Feedback(wx.Dialog):
    """
    Sends feedback to myself by POSTing to a PHP script
    """
    def __init__(self, gui):
        wx.Dialog.__init__(self, gui, title=_("Send Feedback"))

        t_lbl = wx.StaticText(self, label=_("Your Feedback:"))
        email_label = wx.StaticText(self, label=_("E-mail Address"))
        self.feedback = wx.TextCtrl(self, size=(350, 250), style=wx.TE_MULTILINE)
        self.email = wx.TextCtrl(self)

        cancel_b = wx.Button(self, wx.ID_CANCEL, _("&Cancel"))
        send_b = wx.Button(self, wx.ID_OK, _("Send &Feedback"))
        send_b.SetDefault()
        btnSizer = wx.StdDialogButtonSizer()
        btnSizer.AddButton(send_b)
        btnSizer.AddButton(cancel_b)
        btnSizer.Realize()

        font = t_lbl.GetClassDefaultAttributes().font
        font.SetWeight(wx.FONTWEIGHT_BOLD)
        t_lbl.SetFont(font)
        email_label.SetFont(font)

        vsizer = wx.BoxSizer(wx.VERTICAL)
        vsizer.Add((10, 10))
        vsizer.Add(t_lbl, 0, wx.LEFT | wx.RIGHT, 10)
        vsizer.Add(self.feedback, 0, wx.EXPAND | wx.ALL, 10)
        vsizer.Add((10, 10))
        vsizer.Add(email_label, 0, wx.ALL, 10)
        vsizer.Add(self.email, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        vsizer.Add((10, 10))
        vsizer.Add(btnSizer, 0, wx.TOP | wx.BOTTOM | wx.ALIGN_CENTRE, 15)

        self.SetSizerAndFit(vsizer)
        self.SetFocus()
        self.SetAutoLayout(True)
        self.Bind(wx.EVT_BUTTON, self.submit, send_b)


    def submit(self, event):
        """Submit feedback."""
        if not self.email.GetValue() or self.email.GetValue().find("@") == -1:
            wx.MessageBox(_("Please fill out your email address"), u"Whyteboard")
            return
        if len(self.feedback.GetValue()) < 10:
            wx.MessageBox(_("Please provide some feedback"), u"Whyteboard")
            return
        params = urlencode({'submitted': 'fgdg',
                            'feedback': self.feedback.GetValue(),
                            'email': self.email.GetValue()})
        f = urlopen(u"http://www.whyteboard.org/feedback_submit.php", params)
        wx.MessageBox(_("Your feedback has been sent, thank you."), _("Feedback Sent"))
        self.Destroy()

#----------------------------------------------------------------------


class PromptForSave(wx.Dialog):
    """
    Prompts the user to confirm quitting without saving. Style can be
    wx.YES_NO | wx.CANCEL or just wx.YES_NO. 2nd is used when prompting the user
    after updating the program.
    """
    def __init__(self, gui, name, method, style, args):

        wx.Dialog.__init__(self, gui, title=_("Save File?"))
        self.gui = gui
        self.method = method
        self.args = args

        warning = wx.ArtProvider.GetBitmap(wx.ART_WARNING, wx.ART_CMN_DIALOG)
        bmp = wx.StaticBitmap(self, bitmap=warning)
        btnSizer = wx.StdDialogButtonSizer()
        mainSizer = wx.BoxSizer(wx.VERTICAL)
        iconSizer = wx.BoxSizer(wx.HORIZONTAL)
        textSizer = wx.BoxSizer(wx.VERTICAL)
        container = wx.BoxSizer(wx.HORIZONTAL)

        top_message = wx.StaticText(self, label=_('Save changes to "%s" before closing?') % name)
        bottom_message = wx.StaticText(self, label=self.get_time())

        font = top_message.GetClassDefaultAttributes().font
        font.SetWeight(wx.FONTWEIGHT_BOLD)
        font.SetPointSize(font.GetPointSize() + 1)
        top_message.SetFont(font)

        if not self.gui.util.filename:
            saveButton = wx.Button(self, wx.ID_SAVE, _("Save &As..."))
        else:
            saveButton = wx.Button(self, wx.ID_SAVE, _("&Save"))

        if style == wx.YES_NO | wx.CANCEL:
            cancelButton = wx.Button(self, wx.ID_CANCEL, _("&Cancel"))
            btnSizer.AddButton(cancelButton)

        noButton = wx.Button(self, wx.ID_NO, _("&Don't Save"))
        saveButton.SetDefault()

        btnSizer.AddButton(noButton)
        btnSizer.AddButton(saveButton)
        btnSizer.Realize()
        iconSizer.Add(bmp, 0)

        textSizer.Add(top_message)
        textSizer.Add((10, 10))
        textSizer.Add(bottom_message)

        container.Add(iconSizer, 0, wx.LEFT, 15)
        container.Add((15, -1))
        container.Add(textSizer, 1, wx.RIGHT, 15)
        container.Layout()

        mainSizer.Add((10, 15))
        mainSizer.Add(container, wx.ALL, 30)
        mainSizer.Add((10, 10))
        mainSizer.Add(btnSizer, 0, wx.TOP | wx.BOTTOM | wx.ALIGN_CENTRE, 15)

        self.SetSizerAndFit(mainSizer)
        self.SetFocus()
        self.SetAutoLayout(True)
        fix_std_sizer_tab_order(btnSizer)
        self.Bind(wx.EVT_BUTTON, self.okay, saveButton)
        self.Bind(wx.EVT_BUTTON, self.no, noButton)


    def get_time(self):
        m, s = divmod(time.time() - self.gui.util.save_time, 60)
        h, m = divmod(m, 60)
        hours, mins, seconds = "", "", ""

        # ugly....
        if m > 0 and h < 1:
            mins = (u"%i " % m) + _("minutes")
        if m == 1 and h < 1:
            mins = _("minute")
        if h > 0:
            hours = (u"%i " % h) + _("hours")
        if h == 1:
            hours = _("hour")
        if s == 1 and m < 1:
            seconds = _("second")
        elif s > 1 and m < 1:
            seconds = (u"%i " % s) + _("seconds")

        ms = u"%s%s%s" % (hours, mins, seconds)

        return _("If you don't save, changes from the last\n%s will be permanently lost.") % ms


    def okay(self, event):
        self.gui.on_save()
        if self.gui.util.saved:
            self.Close()
        if self.gui.util.saved or self.method == os.execvp:
            self.method(*self.args)  # force restart, otherwise 'cancel'
                                     # returns to application

    def no(self, event):
        self.method(*self.args)
        self.Close()
        if self.method == self.gui.Destroy:
            sys.exit()

    def cancel(self, event):
        self.Close()


#----------------------------------------------------------------------

class Resize(wx.Dialog):
    """
    Allows the user to resize a sheet's canvas
    """
    def __init__(self, gui):
        """
        Two spinctrls are used to set the width/height. Canvas updates as the
        values change
        """
        wx.Dialog.__init__(self, gui, title=_("Resize Canvas"))

        self.gui = gui
        gap = wx.LEFT | wx.TOP | wx.RIGHT
        width, height = self.gui.canvas.buffer.GetSize()
        self.size = (width, height)

        self.wctrl = wx.SpinCtrl(self, min=1, max=12000)
        self.hctrl = wx.SpinCtrl(self, min=1, max=12000)

        csizer = wx.GridSizer(cols=2, hgap=1, vgap=2)
        csizer.Add(wx.StaticText(self, label=_("Width:")), 0, wx.TOP |
                                                            wx.ALIGN_RIGHT, 10)
        csizer.Add(self.wctrl, 1, gap, 7)
        csizer.Add(wx.StaticText(self, label=_("Height:")), 0, wx.TOP |
                                                             wx.ALIGN_RIGHT, 7)
        csizer.Add(self.hctrl, 1, gap, 7)

        self.wctrl.SetValue(width)
        self.hctrl.SetValue(height)

        okButton = wx.Button(self, wx.ID_OK, _("&OK"))
        okButton.SetDefault()
        cancelButton = wx.Button(self, wx.ID_CANCEL, _("&Cancel"))
        applyButton = wx.Button(self, wx.ID_APPLY, _("&Apply"))

        btnSizer = wx.StdDialogButtonSizer()
        btnSizer.AddButton(okButton)
        btnSizer.AddButton(cancelButton)
        btnSizer.AddButton(applyButton)
        btnSizer.Realize()
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(csizer, 0, gap, 7)
        sizer.Add((10, 15))
        sizer.Add(btnSizer, 0, wx.ALIGN_CENTRE | wx.ALL, 5)
        sizer.Add((10, 5))
        self.SetSizer(sizer)
        self.SetFocus()
        sizer.Fit(self)

        cancelButton.Bind(wx.EVT_BUTTON, self.cancel)
        okButton.Bind(wx.EVT_BUTTON, self.ok)
        applyButton.Bind(wx.EVT_BUTTON, self.apply)
        self.hctrl.Bind(wx.EVT_SPINCTRL, self.resize)
        self.wctrl.Bind(wx.EVT_SPINCTRL, self.resize)
        fix_std_sizer_tab_order(sizer)


    def apply(self, event):
        self.size = self.gui.canvas.buffer.GetSize()

    def ok(self, event):
        self.resize()
        self.Close()

    def resize(self, event=None):
        value = (self.wctrl.GetValue(), self.hctrl.GetValue())
        self.gui.canvas.resize(value)

    def cancel(self, event):
        self.gui.canvas.resize(self.size)
        self.Close()

#----------------------------------------------------------------------


class ErrorDialog(BaseErrorDialog):
    def __init__(self, msg):
        BaseErrorDialog.__init__(self, None, title=_("Error Report"), message=msg)
        self.SetDescriptionLabel(_("An error has occured - please report it"))
        self.gui = wx.GetTopLevelWindows()[0]

    def Abort(self):
        self.gui.prompt_for_save(self.gui.Destroy)

    def GetEnvironmentInfo(self):
        """
        Need to stick in extra information: preferences, helps with debugging
        """
        info = super(ErrorDialog, self).GetEnvironmentInfo()

        info = info.split(os.linesep)
        path = os.path.join(get_home_dir(), u"user.pref")
        if os.path.exists(path):
            info.append(u"#---- Preferences ----#")
            with open(path) as f:
                for x in f:
                    info.append(x.rstrip())
            info.append(u"")
            info.append(u"")
        return os.linesep.join(info)

    def GetProgramName(self):
        return u"Whyteboard %s" % meta.version


    def Send(self):
        """Send the error report. PHP script calls isset($_POST['submitted'])"""
        params = urlencode({'submitted': 'fgdg',
                            'message': self._panel.err_msg,
                            'desc': self._panel.action.GetValue(),
                            'email': self._panel.email.GetValue()})
        f = urlopen(u"http://www.whyteboard.org/bug_submit.php", params)

        self.gui.prompt_for_save(self.gui.Destroy)


 #----------------------------------------------------------------------

def ExceptionHook(exctype, value, trace):
    """
    Handler for all unhandled exceptions
    """
    ftrace = ErrorDialog.FormatTrace(exctype, value, trace)
    print ftrace  # show in console

    if ErrorDialog.ABORT:
        os._exit(1)
    if not ErrorDialog.REPORTER_ACTIVE and not ErrorDialog.ABORT:
        dlg = ErrorDialog(ftrace)
        dlg.ShowModal()
        dlg.Destroy()

#----------------------------------------------------------------------


class WhyteboardList(wx.ListCtrl, listmix.ListRowHighlighter):

    def __init__(self, parent):
        wx.ListCtrl.__init__(self, parent, style=wx.DEFAULT_CONTROL_BORDER |
                             wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.LC_HRULES)
        listmix.ListRowHighlighter.__init__(self, (206, 218, 255))


#----------------------------------------------------------------------


class ShapeViewer(wx.Dialog):
    """
    Presents a list of the current sheet's shapes, in accordance to their
    position in the list, which is the order that the shapes are drawn in.
    Allows the user to move shapes up/down/to top/to bottom, as well as info
    about the shape such as its colour/thickness
    """
    def __init__(self, gui):
        """
        Initialise and populate the listbox
        """
        wx.Dialog.__init__(self, gui, title=_("Shape Viewer"), size=(550, 400),
                           style=wx.DEFAULT_DIALOG_STYLE | wx.MAXIMIZE_BOX |
                           wx.MINIMIZE_BOX | wx.RESIZE_BORDER | wx.WANTS_CHARS)
        self.gui = gui
        self.count = 0
        #self.SetExtraStyle(wx.WS_EX_PROCESS_IDLE)
        self.shapes = list(self.gui.canvas.shapes)
        self.SetSizeHints(550, 400)

        label = wx.StaticText(self, label=_("Shapes at the top of the list are drawn over shapes at the bottom"))
        sizer = wx.BoxSizer(wx.VERTICAL)
        bsizer = wx.BoxSizer(wx.HORIZONTAL)
        nextprevsizer = wx.BoxSizer(wx.HORIZONTAL)

        self.moveUp = self.make_button(u"move-up", _("Move Shape Up"))
        self.moveDown = self.make_button(u"move-down", _("Move Shape Down"))
        self.moveTop = self.make_button(u"move-top", _("Move Shape To Top"))
        self.moveBottom = self.make_button(u"move-bottom", _("Move Shape To Bottom"))
        self.deleteBtn = self.make_button(u"delete", _("Delete Shape"))
        self.prev = self.make_button(u"prev_sheet", _("Previous Sheet"))
        self.next = self.make_button(u"next_sheet", _("Next Sheet"))

        self.pages = wx.ComboBox(self, size=(125, 25), style=wx.CB_READONLY)
        self.list = WhyteboardList(self)

        bsizer.AddMany([(self.moveUp, 0, wx.RIGHT, 5), (self.moveDown, 0, wx.RIGHT, 5),
                        (self.moveTop, 0, wx.RIGHT, 5), (self.moveBottom, 0, wx.RIGHT, 5),
                        (self.deleteBtn, 0, wx.RIGHT, 5)])
        nextprevsizer.Add(self.prev, 0, wx.RIGHT, 5)
        nextprevsizer.Add(self.next)

        bsizer.Add((1, 1), 1, wx.EXPAND)  # align to the right
        bsizer.Add(nextprevsizer, 0, wx.RIGHT, 10)
        bsizer.Add(self.pages, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 10)

        okButton = wx.Button(self, wx.ID_OK, _("&OK"))
        okButton.SetDefault()
        cancelButton = wx.Button(self, wx.ID_CANCEL, _("&Cancel"))
        applyButton = wx.Button(self, wx.ID_APPLY, _("&Apply"))
        btnSizer = wx.StdDialogButtonSizer()
        btnSizer.AddButton(okButton)
        btnSizer.AddButton(cancelButton)
        btnSizer.AddButton(applyButton)
        btnSizer.Realize()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(label, 0, wx.ALL, 15)
        sizer.Add((10, 5))
        sizer.Add(bsizer, 0, wx.LEFT | wx.EXPAND, 10)
        sizer.Add((10, 15))
        sizer.Add(self.list, 1, wx.LEFT | wx.RIGHT |wx.EXPAND, 10)
        sizer.Add((10, 5))
        sizer.Add(btnSizer, 0, wx.TOP | wx.BOTTOM | wx.ALIGN_CENTRE, 15)
        self.SetSizer(sizer)
        self.populate()
        self.Fit()
        self.SetFocus()

        cancelButton.Bind(wx.EVT_BUTTON, self.cancel)
        okButton.Bind(wx.EVT_BUTTON, self.ok)
        applyButton.Bind(wx.EVT_BUTTON, self.apply)
        self.moveUp.Bind(wx.EVT_BUTTON, self.on_up)
        self.moveDown.Bind(wx.EVT_BUTTON, self.on_down)
        self.moveTop.Bind(wx.EVT_BUTTON, self.on_top)
        self.moveBottom.Bind(wx.EVT_BUTTON, self.on_bottom)
        self.prev.Bind(wx.EVT_BUTTON, self.on_prev)
        self.next.Bind(wx.EVT_BUTTON, self.on_next)
        self.deleteBtn.Bind(wx.EVT_BUTTON, self.on_delete)
        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.pages.Bind(wx.EVT_COMBOBOX, self.on_change_sheet)

        ac = [(wx.ACCEL_NORMAL, wx.WXK_DELETE, self.deleteBtn.GetId())]
        tbl = wx.AcceleratorTable(ac)
        self.list.SetAcceleratorTable(tbl)
        self.Bind(wx.EVT_CHAR_HOOK, self.delete_key)

        pub.subscribe(self.shape_add, 'shape.add')
        pub.subscribe(self.sheet_rename, 'sheet.rename')

        ids = [self.moveUp.GetId(), self.moveTop.GetId(), self.moveDown.GetId(),
               self.moveBottom.GetId(), self.deleteBtn.GetId(), self.prev.GetId(), self.next.GetId()]

        [self.Bind(wx.EVT_UPDATE_UI, self.update_buttons, id=x) for x in ids]


    def make_button(self, filename, tooltip):
        btn = bitmap_button(self, get_image_path(u"icons", filename), False)
        btn.SetToolTipString(tooltip)
        return btn

    def shape_add(self, shape):
        self.shapes.append(shape)
        self.populate()

    def sheet_rename(self, _id, text):
        self.populate()

    def populate(self):
        """
        Creates all columns and populates with the current sheets' data
        """
        choices = [self.gui.tabs.GetPageText(x) for x in range(self.gui.tab_count)]
        self.pages.SetItems(choices)
        self.pages.SetSelection(self.gui.current_tab)

        self.list.ClearAll()
        self.list.InsertColumn(0, _("Position"))
        self.list.InsertColumn(1, _("Type"))
        self.list.InsertColumn(2, _("Thickness"))
        self.list.InsertColumn(3, _("Color"))
        self.list.InsertColumn(4, _("Properties"))

        if not self.shapes:
            index = self.list.InsertStringItem(sys.maxint, "")
            self.list.SetStringItem(index, 3, _("No shapes drawn"))
            self.list.SetColumnWidth(4, 70)
        else:
            for x, shape in enumerate(reversed(self.shapes)):
                index = self.list.InsertStringItem(sys.maxint, str(x + 1))
                self.list.SetStringItem(index, 0,  str(x + 1))
                self.list.SetStringItem(index, 1, _(shape.name))
                self.list.SetStringItem(index, 2, str(shape.thickness))
                self.list.SetStringItem(index, 3, str(shape.colour))
                self.list.SetStringItem(index, 4, shape.properties())
            self.list.SetColumnWidth(4, wx.LIST_AUTOSIZE)

        self.list.SetColumnWidth(0, 60)
        self.list.SetColumnWidth(1, 70)
        self.list.SetColumnWidth(2, 70)
        self.list.SetColumnWidth(3, wx.LIST_AUTOSIZE)


    def update_buttons(self, event):
        _id = event.GetId()
        do = False

        if _id == self.next.GetId() and self.gui.current_tab + 1 < self.gui.tab_count:
            do = True
        elif _id == self.prev.GetId() and self.gui.current_tab > 0:
            do = True
        elif _id == self.deleteBtn.GetId() and self.shapes and self.list.GetFirstSelected() >= 0:
            do = True
        elif _id in [self.moveUp.GetId(), self.moveTop.GetId()] and self.list.GetFirstSelected() > 0:
            do = True
        elif (_id in [self.moveDown.GetId(), self.moveBottom.GetId()] and
            self.list.GetFirstSelected() != len(self.shapes) - 1  and self.shapes
            and self.list.GetFirstSelected() >= 0):
            do = True

        event.Enable(do)
        #self.Refresh()
        #self.count += 1
        #if self.count == 5:
        #    self.Refresh()
        #    self.count = 0


    def find_shape(self):
        """Find the selected shape's index and actual object"""
        count = 0
        for x in reversed(self.shapes):
            if count == self.list.GetFirstSelected():
                return (self.shapes.index(x), x)
            count += 1

    def move_shape(fn):
        """
        Passes the selected shape and its index to the decorated function, which
        handles moving the shape. function returns the list index to select
        """
        def wrapper(self, event, index=None, item=None):
            index, item = self.find_shape()
            self.shapes.pop(index)
            x = fn(self, event, index, item)

            self.populate()
            self.list.Select(x)
        return wrapper

    @move_shape
    def on_top(self, event, index=None, item=None):
        self.shapes.append(item)
        return 0

    @move_shape
    def on_bottom(self, event, index=None, item=None):
        self.shapes.insert(0, item)
        return len(self.shapes) - 1

    @move_shape
    def on_up(self, event, index=None, item=None):
        self.shapes.insert(index + 1, item)
        return self.list.GetFirstSelected() - 1

    @move_shape
    def on_down(self, event, index=None, item=None):
        self.shapes.insert(index - 1, item)
        return self.list.GetFirstSelected() + 1

    @move_shape
    def on_delete(self, event, index=None, item=None):
        #self.gui.canvas.selected = item
        #self.gui.canvas.delete_selected()
        if self.list.GetFirstSelected() - 1 <= 0:
            return 0
        return self.list.GetFirstSelected() - 1

    def delete_key(self, event):
        if event.GetKeyCode() == wx.WXK_DELETE and self.shapes:
            self.on_delete(None)
        event.Skip()


    def change(self, selection):
        """Change the sheet, repopulate"""
        self.gui.tabs.SetSelection(selection)
        self.pages.SetSelection(selection)
        self.gui.on_change_tab()
        self.shapes = list(self.gui.canvas.shapes)
        self.populate()


    def on_change_sheet(self, event):
        self.change(self.pages.GetSelection())

    def on_next(self, event):
        self.change(self.gui.current_tab + 1)

    def on_prev(self, event):
        self.change(self.gui.current_tab - 1)

    def ok(self, event):
        self.apply()
        self.Close()

    def cancel(self, event=None):
        self.Close()

    def on_close(self, event):
        self.gui.viewer = False
        event.Skip()

    def apply(self, event=None):
        self.gui.canvas.add_undo()
        self.gui.canvas.shapes = self.shapes
        self.gui.canvas.redraw_all(True)


#----------------------------------------------------------------------

class PDFCacheDialog(wx.Dialog):
    """
    Views a list of all cached PDFs - showing the amount of pages, location,
    conversion quality and date saved. Has options to remove items to re-convert
    """
    def __init__(self, gui, cache):
        wx.Dialog.__init__(self, gui, title=_("PDF Cache Viewer"), size=(450, 300),
                           style=wx.DEFAULT_DIALOG_STYLE | wx.MAXIMIZE_BOX |
                           wx.MINIMIZE_BOX | wx.RESIZE_BORDER)
        self.cache = cache
        self.files = cache.entries()
        self.original_files = dict(cache.entries())
        self.list = WhyteboardList(self)
        self.SetSizeHints(450, 300)

        label = wx.StaticText(self, label=_("Whyteboard will load these files from its cache instead of re-converting them"))
        sizer = wx.BoxSizer(wx.VERTICAL)
        bsizer = wx.BoxSizer(wx.HORIZONTAL)

        self.deleteBtn = bitmap_button(self, get_image_path(u"icons", u"delete"), False)
        self.deleteBtn.SetToolTipString(_("Remove cached item"))
        bsizer.Add(self.deleteBtn, 0, wx.RIGHT, 5)

        okButton = wx.Button(self, wx.ID_OK, _("&OK"))
        cancelButton = wx.Button(self, wx.ID_CANCEL, _("&Cancel"))
        okButton.SetDefault()
        btnSizer = wx.StdDialogButtonSizer()
        btnSizer.AddButton(okButton)
        btnSizer.AddButton(cancelButton)
        btnSizer.Realize()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(label, 0, wx.ALL, 15)
        sizer.Add((10, 5))
        sizer.Add(bsizer, 0, wx.LEFT | wx.EXPAND, 10)
        sizer.Add((10, 5))
        sizer.Add(self.list, 1, wx.LEFT | wx.RIGHT |wx.EXPAND, 10)
        sizer.Add((10, 5))
        sizer.Add(btnSizer, 0, wx.TOP | wx.BOTTOM | wx.ALIGN_CENTRE, 15)
        self.SetSizer(sizer)
        self.populate()
        self.check_buttons()
        self.Fit()

        okButton.Bind(wx.EVT_BUTTON, self.ok)
        self.deleteBtn.Bind(wx.EVT_BUTTON, self.on_remove)
        cancelButton.Bind(wx.EVT_BUTTON, lambda x: self.Close())
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, lambda x: self.check_buttons())
        self.Bind(wx.EVT_LIST_ITEM_DESELECTED, lambda x: self.check_buttons())


    def populate(self):
        """
        Creates all columns and populates them with the PDF cache list
        """
        self.list.ClearAll()
        self.list.InsertColumn(0, _("File Location"))
        self.list.InsertColumn(1, _("Quality"))
        self.list.InsertColumn(2, _("Pages"))
        self.list.InsertColumn(3, _("Date Cached"))

        if not self.files:
            index = self.list.InsertStringItem(sys.maxint, "")
            self.list.SetStringItem(index, 0, _("There are no cached items to display"))
        else:
            for x, key in self.files.items():
                f = self.files[x]
                index = self.list.InsertStringItem(sys.maxint, str(x + 1))

                self.list.SetStringItem(index, 0, f['file'])
                self.list.SetStringItem(index, 1, f['quality'].capitalize())
                self.list.SetStringItem(index, 2, u"%s" % len(f['images']))
                self.list.SetStringItem(index, 3, f.get('date', _("No Date Saved")))

        self.list.SetColumnWidth(0, wx.LIST_AUTOSIZE)
        self.list.SetColumnWidth(1, 70)
        self.list.SetColumnWidth(2, 60)
        self.list.SetColumnWidth(3, wx.LIST_AUTOSIZE)


    def check_buttons(self):
        """ Enable / Disable the appropriate buttons """
        if not self.list.GetItemCount() or self.list.GetFirstSelected() == -1:
            self.deleteBtn.Disable()
        else:
            self.deleteBtn.Enable()
        self.SetFocus()


    def ok(self, event):
        self.cache.write_dict(self.files)
        self.Close()

    def on_remove(self, event):
        """Remove the dictionary item that matches the selected item's path"""
        item = self.list.GetFirstSelected()
        if item == -1:
            return

        quality = self.list.GetItem(item, 1).GetText()
        text = self.list.GetItemText(item)
        files = dict(self.files)

        for x, key in self.files.items():
            if (self.files[x]['file'] == text and
                self.files[x]['quality'].capitalize() == quality):
                del files[x]

        self.files = files
        self.populate()


#----------------------------------------------------------------------