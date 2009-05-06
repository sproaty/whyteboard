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
This module contains classes extended from wx.Dialog used by the GUI.
"""

import wx
import wx.html
import urllib
import tarfile
import os
import sys
import distutils.dir_util

from copy import copy
from BeautifulSoup import BeautifulSoup

import tools

#----------------------------------------------------------------------

class History(wx.Dialog):
    """
    Creates a history replaying dialog and methods for its functionality
    """
    def __init__(self, gui):
        wx.Dialog.__init__(self, gui, title="History Player", size=(400, 200),
                           style=wx.CLOSE_BOX | wx.CAPTION)
        self.gui = gui
        self.looping = False
        self.paused = False

        sizer = wx.BoxSizer(wx.VERTICAL)
        #_max = len(gui.board.shapes)+50
        #self.slider = wx.Slider(self, minValue=1, maxValue=_max, size=(200,50),
        #            style=wx.SL_AUTOTICKS | wx.SL_HORIZONTAL )
        #self.slider.SetTickFreq(5, 1)

        historySizer = wx.BoxSizer(wx.HORIZONTAL)
        btn_stop = wx.Button(self, label="Stop", size=(45, 30) )
        btn_pause = wx.Button(self, label="Pause", size=(50, 30) )
        btn_play = wx.Button(self, label="Play", size=(45, 30) )
        historySizer.Add(btn_play, 0,  wx.ALL, 2)
        historySizer.Add(btn_pause, 0,  wx.ALL, 2)
        historySizer.Add(btn_stop, 0,  wx.ALL, 2)

        self.cancelButton = wx.Button(self, wx.ID_CANCEL, "&Cancel")
        self.cancelButton.SetDefault()


        btnSizer = wx.StdDialogButtonSizer()
        btnSizer.Add(self.cancelButton, 0, wx.BOTTOM | wx.LEFT, 5)

        #sizer.Add(self.slider, 0, wx.ALL, 5)
        sizer.Add(historySizer, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALL, 10)
        sizer.Add(btnSizer, 0, wx.ALIGN_CENTRE, 5)

        self.SetSizer(sizer)
        sizer.Fit(self)
        self.SetFocus()

        btn_play.Bind(wx.EVT_BUTTON, self.on_play)
        btn_pause.Bind(wx.EVT_BUTTON, self.pause)
        btn_stop.Bind(wx.EVT_BUTTON, self.stop)
        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.cancelButton.Bind(wx.EVT_BUTTON, self.on_close)
        #self.slider.Bind(wx.EVT_SCROLL, self.scroll)


    def on_play(self, event):
        """
        Starts the replay if it's not already started, unpauses if paused
        """
        if self.looping:
            self.paused = False
            return

        if self.paused:
            self.paused = False

        tmp_shapes = copy(self.gui.board.shapes)
        shapes = []
        for shape in tmp_shapes:
            if not isinstance(shape, tools.Image):
                shapes.append(shape)

        if shapes:
            self.looping = True
            self.draw(shapes)
        else:
            wx.MessageBox("There was nothing to draw.", "Nothing to draw")


    def draw(self, shapes):
        """
        Replays the users' last-drawn pen strokes.
        The loop can be paused/unpaused by the user.
        """
        dc = wx.ClientDC(self.gui.board)
        dc.Clear()
        self.gui.board.PrepareDC(dc)

        #  paint any images first
        for s in self.gui.board.shapes:
            if isinstance(s, tools.Image):
                s.draw(dc)

        for pen in shapes:
            # draw pen outline
            if isinstance(pen, tools.Pen):
                pen.make_pen()
                dc.SetPen(pen.pen)

                for x, p in enumerate(pen.points):

                    if self.looping and not self.paused:
                        try:
                            wx.MilliSleep((pen.time[x + 1] - pen.time[x]) * 950)
                            wx.Yield()
                        except IndexError:
                            pass

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


    def stop(self, event=None):
        """Stops the replay."""
        if self.looping or self.paused:
            self.looping = False
            self.paused = False
            self.gui.board.Refresh()  # restore


    def on_close(self, event=None):
        """
        Called when the dialog is closed; stops the replay and ends the modal
        view, allowing the GUI to Destroy() the dialog.
        """
        self.stop()
        self.EndModal(1)

    def scroll(self, event):
        self.pause()


#----------------------------------------------------------------------


class ProgressDialog(wx.Dialog):
    """
    Shows a Progres Gauge while an operation is taking place.
    """
    def __init__(self, gui, title, to_add=1):
        """Defines a gauge and a timer which updates the gauge."""
        wx.Dialog.__init__(self, gui, title=title,  size=(325, 120),
                          style=wx.CAPTION)
        self.count = 0
        self.to_add = to_add
        self.timer = wx.Timer(self)
        self.gauge = wx.Gauge(self, range=100, size=(180, 30))

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.gauge, 0, wx.ALL, 3)
        self.SetSizer(sizer)
        sizer.Fit(self)
        self.SetFocus()

        self.Bind(wx.EVT_TIMER, self.on_timer, self.timer)
        self.timer.Start(20)

    def on_timer(self, event):
        """Increases the gauge's progress."""
        self.count += self.to_add
        self.gauge.SetValue(self.count)
        if self.count == 100:
            self.count = 0


#----------------------------------------------------------------------


class UpdateDialog(wx.Dialog):
    """
    Shows a Progres Gauge while an operation is taking place.
    """
    def __init__(self, gui):
        """Defines a gauge and a timer which updates the gauge."""
        wx.Dialog.__init__(self, gui, title="Updates", size=(350, 300))        
        self.gui = gui
        self.downloaded = 0
        gap = wx.LEFT | wx.TOP | wx.RIGHT
        
        self.text = wx.StaticText(self, label="Connecting to server...")
        self.text2 = wx.StaticText(self, label="")
        font = self.text.GetClassDefaultAttributes().font
        font.SetPointSize(11)
        self.text.SetFont(font) 
        self.text2.SetFont(font)
        
        self.btn = wx.Button(self, label="Update")
        self.btn.Disable() 
        self.cancelButton = wx.Button(self, wx.ID_CANCEL, "&Cancel")
        self.cancelButton.SetDefault()        
        btnSizer = wx.StdDialogButtonSizer()
        btnSizer.Add(self.cancelButton, 0, wx.BOTTOM | wx.LEFT, 2)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.text, 0, gap, 10)
        sizer.Add(self.text2, 0, wx.TOP | wx.LEFT, 48)
        sizer.Add(self.btn, 0, wx.TOP | wx.ALIGN_CENTRE, 10)
        sizer.Add((10, 10)) # Spacer.
        sizer.Add(btnSizer, 0, gap | wx.ALIGN_CENTRE, 5)
        self.SetSizer(sizer)

        self.btn.Bind(wx.EVT_BUTTON, self.update)  
        wx.CallAfter(self.check)  # we want to show the dialog then fetch URL  


    def check(self):  
        """             
        Opens a connection to Google Code's site and uses BeautifulSoup to
        parse the website for the filename and file size. Extract the new
        file's version from its filename, and compare against current version 
        """
        f = urllib.urlopen("http://code.google.com/p/whyteboard/downloads/")
        html = f.read()
        f.close()        
        soup = BeautifulSoup(html)
        
        _type = ".tar.gz"
        if os.name == "nt":
            if self.gui.util.is_exe():
                _type = ".exe"                
                    
        for i, td in enumerate(soup.findAll("td", {"class": "vt id col_0"})):
            _file = td.findNext('a').renderContents().strip()  
            
            if _file.endswith(_type):
                if _type == ".exe" and _file.find("installer") is not -1:
                    break
                start = _file.find("-") + 1
                stop = _file.find(_type)
                version = _file[start : stop]
                
                all = soup.findAll("td", {"class": "vt col_3"})
                size = all[i].findNext('a').renderContents().strip()            
                
                if version != self.gui.version:  
                    s = (" There is a new version available, "+version +"\n"+
                         " File: " +_file +"\n"+
                         " Size: " + size)                
                    self.text.SetLabel(s)
                    self.btn.Enable(True)
                    self._file = td.findNext('a')['href']
                    self._type = _type
                    self.version = version
                else:
                    self.text.SetLabel("You are running the latest version.")        


    def update(self, event=None):
        """
        Updates the program by downloading the correct file and extracting it.
        On Linux, the Tar file is extracted into the current directory, and on
        Windows the .exe is renamed, the new one renamed to replace it and on
        both platforms the program is then restarted (after asking the user to
        save or not)
        """
        path = self.gui.util.path
        args = []        
        _file = os.path.join(path[0], 'tmp'+ self._type)        
        tmp = urllib.urlretrieve(self._file, _file, self.myReportHook)
        
        if self.gui.util.is_exe():
            # rename current exe, rename temp to current
            if os.name == "nt":
                os.rename(path[1], "wtbd-bckup.exe")                             
                os.rename("tmp.exe", "whyteboard.exe")                      
                args = [sys.argv[0], [sys.argv[0]]]                                   
        else:
            if os.name == "posix":
                pass#os.system("tar -xf "+ tmp[0] +" --strip-components=1")     
            else:
                self.extract_tar(os.path.abspath(tmp[0]))
                                
            os.remove(tmp[0])           
            _list = ['python', sys.argv[0]]  # for os.execvp          
            if self.gui.util.filename:                 
                _list.append(self.gui.util.filename)   
                  
        self.gui.util.prompt_for_save(os.execvp, wx.YES_NO, ['python', _list])
        
        
    def extract_tar(self, _file):
        """
        Extract a .tar.gz source file on Windows, without needing to use the
        'tar' command, and with no other downloads!
        """
        path = self.gui.util.path[0]
        tar = tarfile.open(_file)       
        #tar.extractall(path)
        tar.close() 
        # remove 2 folders that will be updated, may not exist   
        src = os.path.join(path, "whyteboard-"+ self.version)
        
        widgs = os.path.join(path, "fakewidgets")
        helps = os.path.join(path, "helpfiles")
        #if os.path.exists(widgs):
        #    distutils.dir_util.remove_tree(widgs)        
        #if os.path.exists(helps):
        #    distutils.dir_util.remove_tree(helps)        
               
        # rename all files - ignore dirs  
        for f in os.listdir(path):
            location = os.path.join(path, f)
            if not os.path.isdir(location):  
                _type = os.path.splitext(f)              
 
                if _type[1] in [".py", ".txt"]:   
                    new_file = (os.path.join(path, _type[0]) 
                                 + self.gui.util.backup_ext)                                                                    
                    #os.rename(location, new_file)
                                
        # move extracted file to current dir, remove tar, remove extracted dir
        #distutils.dir_util.copy_tree(src, path)
        #distutils.dir_util.remove_tree(src) 
               
             
    def myReportHook(self, count, block, total):
        """
        Updates a text label with progress on a download
        """
        self.downloaded += block             
        done = self.downloaded / 1024
                          
        _type2 = "KB"
        total /= 1024
        rem = ""
        if total > 1024:
            rem = "."+ str(total % 1024)
            total /= 1024            
            _type2 = "MB"
                    
        self.text2.SetLabel("Downloaded "+str(done) + "KB of "+ str(total) +                               
                                          rem + _type2)              

            
#----------------------------------------------------------------------


class TextInput(wx.Dialog):
    """
    Shows a text input screen, updates the canvas' text as text is being input
    and has methods for
    """
    def __init__(self, gui, note=None):
        """
        Standard constructor - sets text to supplied text variable, if present.
        """
        wx.Dialog.__init__(self, gui, title="Enter text", pos=(600, 600),
                            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.gui = gui
        self.note = None
        self.ctrl = wx.TextCtrl(self, style=wx.TE_RICH2 | wx.TE_MULTILINE,
                                                    size=(300, 120))
        extent = self.ctrl.GetFullTextExtent("Hy")
        lineHeight = extent[1] + extent[3]
        self.ctrl.SetSize(wx.Size(-1, lineHeight * 4))
        self.font = self.ctrl.GetFont()

        if note:
            self.note = note
            self.ctrl.SetValue(note.text)
            self.ctrl.SetForegroundColour(note.colour)
            self.font.SetNativeFontInfoFromString(note.font_data)
            self.ctrl.SetFont(self.font)
        else:
            self.ctrl.SetForegroundColour(gui.util.colour)

        fontBtn = wx.Button(self, label="Select Font")
        gap = wx.LEFT | wx.TOP | wx.RIGHT

        self.okButton = wx.Button(self, wx.ID_OK, "&OK")
        self.okButton.SetDefault()
        self.cancelButton = wx.Button(self, wx.ID_CANCEL, "&Cancel")

        btnSizer = wx.StdDialogButtonSizer()
        btnSizer.Add(self.okButton, 0, wx.BOTTOM | wx.RIGHT, 5)
        btnSizer.Add(self.cancelButton, 0, wx.BOTTOM | wx.LEFT, 5)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.ctrl, 1, gap | wx.EXPAND, 7)
        sizer.Add(fontBtn, 0, gap | wx.ALIGN_RIGHT, 5)
        sizer.Add((10, 10))  # Spacer.
        btnSizer.Realize()
        sizer.Add(btnSizer, 0, gap | wx.ALIGN_CENTRE, 5)

        self.SetAutoLayout(True)
        self.SetSizer(sizer)
        sizer.Fit(self)

        self.set_focus()
        self.Bind(wx.EVT_BUTTON, self.on_font, fontBtn)
        self.Bind(wx.EVT_TEXT, self.update_canvas, self.ctrl)
        self.Bind(wx.EVT_BUTTON, self.on_close, self.cancelButton)


    def on_font(self, evt):
        """
        Shows the font dialog, sets the input text's font and returns focus to
        the text input box, at the user's selected point.
        """
        data = wx.FontData()
        data.EnableEffects(True)
        data.SetInitialFont(self.font)
        dlg = wx.FontDialog(self, data)

        if dlg.ShowModal() == wx.ID_OK:
            data = dlg.GetFontData()
            self.font = data.GetChosenFont()

            self.ctrl.SetFont(self.font)
            # Update dialog for the new height of the text
            self.GetSizer().Fit(self)
            self.update_canvas()

        dlg.Destroy()
        self.set_focus()


    def set_focus(self):
        """
        Sets the focus to the text and places the cursor at the end of the text
        """
        selection = self.ctrl.GetSelection()
        self.ctrl.SetFocus()
        self.ctrl.SetSelection(*selection)


    def update_canvas(self, event=None):
        """
        Updates the canvas with the inputted text. We want to work with a copy
        of the shape, not the actual shape.
        """
        if self.note:
            shape = self.note
            board = shape.board
        else:
            board = self.gui.board
            shape = board.shape
        self.transfer_data(shape)
        board.redraw_all()  # stops overlapping text

        dc = wx.BufferedDC(None, board.buffer)
        shape.draw(dc)

    def transfer_data(self, text_obj):
        """Transfers the dialog's data to an object."""
        text_obj.text = self.ctrl.GetValue()
        text_obj.font = self.font

    def on_close(self, event):
        """Leaves dialog.ShowModal() == wx.ID_CANCEL to handle closing"""
        event.Skip()

#----------------------------------------------------------------------

class FindIM(wx.Dialog):
    """
    Asks a user for the location of ImageMagick.
    """
    t = ("Whyteboard uses ImageMagick to load PDF, SVG and PS files. \n"
    "Please select its installed location.")

    def __init__(self, parent, gui):
        """
        Standard constructor
        """
        wx.Dialog.__init__(self, gui, title="ImageMagick Notification")
        self.parent = parent  # utility class
        self.path = "C:/Program Files/"

        text = wx.StaticText(self, label=self.t)
        btn = wx.Button(self, label="Find location...")
        gap = wx.LEFT | wx.TOP | wx.RIGHT

        self.okButton = wx.Button(self, wx.ID_OK, "&OK")
        self.okButton.SetDefault()
        self.cancelButton = wx.Button(self, wx.ID_CANCEL, "&Cancel")

        btnSizer = wx.StdDialogButtonSizer()
        btnSizer.Add(self.okButton, 0, wx.BOTTOM | wx.RIGHT, 5)
        btnSizer.Add(self.cancelButton, 0, wx.BOTTOM | wx.LEFT, 5)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(text, 1, gap | wx.EXPAND, 10)
        sizer.Add(btn, 0, gap | wx.ALIGN_CENTRE, 20)
        sizer.Add((10, 10)) # Spacer.
        btnSizer.Realize()
        sizer.Add(btnSizer, 0, gap | wx.ALIGN_CENTRE, 5)
        self.SetSizer(sizer)
        sizer.Fit(self)

        btn.Bind(wx.EVT_BUTTON, self.browse)
        self.okButton.Bind(wx.EVT_BUTTON, self.ok)
        self.cancelButton.Bind(wx.EVT_BUTTON, self.cancel)


    def browse(self, event=None):
        dlg = wx.DirDialog(self, "Choose a directory", self.path)

        if dlg.ShowModal() == wx.ID_OK:
            self.path = dlg.GetPath()
        else:
            dlg.Destroy()


    def ok(self, event=None):
        if self.parent.check_im_path(self.path):
            self.Close()

    def cancel(self, event=None):
        self.Close()

#----------------------------------------------------------------------

class Resize(wx.Dialog):
    """
    Allows the user to resize a sheet's canvas
    """
    def __init__(self, gui):
        """
        Two text controls for inputting the size, limited to integers only
        using a Validator class
        """
        wx.Dialog.__init__(self, gui, title="Resize Canvas")

        self.gui = gui
        gap = wx.LEFT | wx.TOP | wx.RIGHT
        width, height = self.gui.board.virtual_size

        csizer = wx.GridSizer(cols=2, hgap=1, vgap=2)
        self.hctrl = wx.TextCtrl(self, validator = IntValidator())
        self.wctrl = wx.TextCtrl(self, validator = IntValidator())
        csizer.Add(wx.StaticText(self, label="Width:"), 0, wx.TOP |
                                                            wx.ALIGN_RIGHT, 10)
        csizer.Add(self.wctrl, 1, gap, 7)
        csizer.Add(wx.StaticText(self, label="Height:"), 0, wx.TOP |
                                                             wx.ALIGN_RIGHT, 7)
        csizer.Add(self.hctrl, 1, gap, 7)

        self.hctrl.SetValue(str(height))
        self.wctrl.SetValue(str(width))

        self.okButton = wx.Button(self, wx.ID_OK, "&OK")
        self.okButton.SetDefault()
        self.cancelButton = wx.Button(self, wx.ID_CANCEL, "&Cancel")

        btnSizer = wx.StdDialogButtonSizer()
        btnSizer.Add(self.okButton, 0, wx.BOTTOM | wx.RIGHT, 5)
        btnSizer.Add(self.cancelButton, 0, wx.BOTTOM | wx.LEFT, 5)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(csizer, 0, gap, 7)
        sizer.Add((10, 10)) # Spacer.
        btnSizer.Realize()
        sizer.Add(btnSizer, 0, gap | wx.ALIGN_CENTRE, 5)

        self.SetSizer(sizer)
        sizer.Fit(self)

        self.okButton.Bind(wx.EVT_BUTTON, self.ok)


    def ok(self, event):
        """
        Set the virtual canvas size
        """
        value = (int(self.wctrl.GetValue()), int(self.hctrl.GetValue()))
        board = self.gui.board
        board.SetVirtualSize(value)
        board.SetSize(value)
        board.SetBackgroundColour("Grey")
        board.ClearBackground()
        self.Close()

#----------------------------------------------------------------------

class IntValidator(wx.PyValidator):
    """
    Only allows integer input for the resize text boxes
    """
    def __init__(self):
        wx.PyValidator.__init__(self)
        self.Bind(wx.EVT_CHAR, self.on_char)

    def Clone(self):
        return IntValidator()

    def TransferFromWindow(self):
        """
        Need to override to stop a message box popping up
        """
        return True

    def TransferToWindow(self):
        """
        Need to override to stop a message box popping up
        """
        return True

    def Validate(self, win):
        """
        The actual validation method called on the input
        """
        tc = self.GetWindow()
        val = tc.GetValue()

        for x in val:
            if not x.isdigit:
                return False
        return True


    def on_char(self, event):
        """
        Ensure a keypress is a digit
        """
        key = event.GetKeyCode()

        if key < wx.WXK_SPACE or key == wx.WXK_DELETE or key > 255:
            event.Skip()
            return

        if chr(key) in '0123456789':
            event.Skip()
            return
        return

#----------------------------------------------------------------------

if __name__ == '__main__':
    from gui import WhyteboardApp
    app = WhyteboardApp(redirect=True)
    app.MainLoop()
