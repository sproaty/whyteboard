#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Author: Steven Sproat <sproaty@gmail.com>
# 16 December 2011

import wx
from wx.lib.agw.hyperlink import HyperLinkCtrl

_ = wx.GetTranslation


def button(parent, _id, label, event_handler):
    """
    Button that's auto-bound to an event
    """
    button = wx.Button(parent, _id, label)
    button.Bind(wx.EVT_BUTTON, event_handler)
    return button


class AboutDialog(wx.Dialog):
    """
    A replacement About Dialog for Windows
    """
    def __init__(self, parent, info):
        wx.Dialog.__init__(self, parent, title=_("About %s" % info.Name))
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        image = wx.StaticBitmap(self, bitmap=wx.BitmapFromIcon(info.GetIcon()))
        name = wx.StaticText(self, label="%s %s" % (info.Name, info.Version))
        description = wx.StaticText(self, label=info.Description)
        copyright = wx.StaticText(self, label=info.Copyright)
        url = HyperLinkCtrl(self, label=info.WebSite[0], URL=info.WebSite[1])

        font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        font.SetWeight(wx.FONTWEIGHT_BOLD)
        font.SetPointSize(font.GetPointSize() + 3)
        name.SetFont(font)

        btnSizer = wx.BoxSizer(wx.HORIZONTAL)
        buttons = {_("C&redits"): (wx.ID_ABOUT, wx.LEFT | wx.RIGHT,
                                   lambda evt: CreditsDialog(self, info)),
                  _("&License"): (wx.ID_ANY, wx.RIGHT,
                                   lambda evt: LicenseDialog(self, info)),
                  _("&Close"): (wx.ID_CANCEL, wx.RIGHT,
                                   lambda evt: self.Destroy())}

        for label, values in buttons.items():
            btn = button(self, values[0], label, values[2])
            btnSizer.Add(btn, flag=wx.CENTER | values[1], border=5)
        
        if info.HasIcon():
            sizer.Add(image, flag=wx.CENTER | wx.TOP | wx.BOTTOM, border=5)
        sizer.Add(name, flag=wx.CENTER | wx.BOTTOM, border=10)
        sizer.Add(description, flag=wx.CENTER | wx.BOTTOM, border=10)
        sizer.Add(copyright, flag=wx.CENTER | wx.BOTTOM, border=10)
        sizer.Add(url, flag=wx.CENTER | wx.BOTTOM, border=15)
        sizer.Add(btnSizer, flag=wx.CENTER | wx.BOTTOM, border=5)

        container = wx.BoxSizer(wx.VERTICAL)
        container.Add(sizer, flag=wx.ALL, border=10)
        self.SetSizerAndFit(container)
        self.Centre()
        self.Show(True)


#----------------------------------------------------------------------

class CreditsDialog(wx.Dialog):
    def __init__(self, parent, info):
        wx.Dialog.__init__(self, parent, title=_("Credits"), size=(475, 320),
                           style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.SetIcon(info.GetIcon())
        self.SetMinSize((300, 200))
        notebook = wx.Notebook(self)
        close = button(self, wx.ID_CANCEL, _("&Close"), lambda evt: self.Destroy())
        close.SetDefault()

        labels = [_("Written by"), _("Translated by")]
        texts = [info.Developers, info.Translators]

        for label, text in zip(labels, texts):
            btn = wx.TextCtrl(notebook, style=wx.TE_READONLY | wx.TE_MULTILINE)
            btn.SetValue(u"\n".join(text))
            notebook.AddPage(btn, text=label)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(notebook, 1, wx.EXPAND | wx.ALL, 10)
        sizer.Add(close, flag=wx.ALIGN_RIGHT | wx.RIGHT | wx.BOTTOM, border=10)
        self.SetSizer(sizer)
        self.Layout()
        self.Show()


#----------------------------------------------------------------------

class LicenseDialog(wx.Dialog):
    def __init__(self, parent, info):
        wx.Dialog.__init__(self, parent, title=_("License"), size=(500, 400),
                           style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.SetMinSize((400, 300))
        self.SetIcon(info.GetIcon())
        close = button(self, wx.ID_CANCEL, _("&Close"), lambda evt: self.Destroy())

        ctrl = wx.TextCtrl(self, style=wx.TE_READONLY | wx.TE_MULTILINE)
        ctrl.SetValue(info.GetLicence())

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(ctrl, 1, wx.EXPAND | wx.ALL, 10)
        sizer.Add(close, flag=wx.ALIGN_RIGHT | wx.RIGHT | wx.BOTTOM, border=10)
        self.SetSizer(sizer)
        self.Layout()
        self.Show()

#---------------------------------------------------

class BaseFrame(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self, None, title=u"New About Box - %s" % self.__class__)
        self.inf = wx.AboutDialogInfo()
        button = wx.Button(self, label=u"Show the about box")
    
        self.Bind(wx.EVT_BUTTON, self.click)
    
    def click(self, event):
        pass
 
class Frame1(BaseFrame):
    def click(self, event):
        self.inf.Name = u"My Application"
        AboutDialog(self, self.inf) 

class Frame2(BaseFrame):
    def click(self, event):
        self.inf.Name = u"My Application"
        self.inf.Version = "1.00"
        AboutDialog(self, self.inf) 

class Frame3(BaseFrame):
    def click(self, event):
        self.inf.Name = u"My Application"
        self.inf.Version = "1.00"
        self.inf.Copyright = u"© 2011 Steven Sproat"
        AboutDialog(self, self.inf) 

class Frame4(BaseFrame):
    def click(self, event):
        self.inf.Name = u"My Application"
        self.inf.Version = "1.00"
        self.inf.Copyright = u"© 2011 Steven Sproat"
        self.inf.Description = "This is a replacement About Box for Windows"
        AboutDialog(self, self.inf)
    
class Frame5(BaseFrame):
    def click(self, event):
        self.inf.Name = u"My Application"
        self.inf.Version = "1.00"
        self.inf.Copyright = u"© 2011 Steven Sproat"
        self.inf.Description = "This is a replacement About Box for Windows"
        self.inf.Developers = [u"Steven Sproat <sproaty@gmail.com>"]
        AboutDialog(self, self.inf)     
        
    
class Frame6(BaseFrame):
    def click(self, event):
        self.inf.Name = u"My Application"
        self.inf.Version = "1.00"
        self.inf.Copyright = u"© 2011 Steven Sproat"
        self.inf.Description = "This is a replacement About Box for Windows"
        self.inf.Developers = [u"Steven Sproat <sproaty@gmail.com>"]
        self.inf.Translators = u"somebody\n" * 20
        AboutDialog(self, self.inf)   

class Frame7(BaseFrame):
    def click(self, event):
        self.inf.Name = u"My Application"
        self.inf.Version = "1.00"
        self.inf.Copyright = u"© 2011 Steven Sproat"
        self.inf.Description = "This is a replacement About Box for Windows"
        self.inf.Developers = [u"Steven Sproat <sproaty@gmail.com>"]
        self.inf.Translators = u"somebody\n" * 20
        self.inf.WebSite = (u"http://www.whyteboard.org", u"http://www.whyteboard.org")
        AboutDialog(self, self.inf)   
                                    
                                    
class Frame8(BaseFrame):
    def click(self, event):
        self.inf.Name = u"My Application"
        self.inf.Version = "1.00"
        self.inf.Copyright = u"© 2011 Steven Sproat"
        self.inf.Description = "This is a replacement About Box for Windows"
        self.inf.Developers = [u"Steven Sproat <sproaty@gmail.com>"]
        self.inf.Translators = u"somebody\n" * 20
        self.inf.WebSite = (u"http://www.whyteboard.org", u"http://www.whyteboard.org")
        self.inf.Licence = u"You may blah de blah da da blarghh\n" * 200
        AboutDialog(self, self.inf)   
                                                                                                                      
app = wx.App(redirect=False)
frames = [Frame1, Frame2, Frame3, Frame4, Frame5, Frame6, Frame7, Frame8]

for frame in frames:
    f = frame()
    f.Show()

app.MainLoop()