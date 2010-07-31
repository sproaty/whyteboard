#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Fake classes for sized controls.

Right now, we are automatically importing this and doing the same
namespace overrides that wxaddons.sized_controls does. Need to watch
out for changed test/actual behavior because of this.
"""

from core import Dialog, Panel



# Sized controls
class SizedDialog(Dialog):
    def __init__(self, *args, **kwds):
        Dialog.__init__(self, *args, **kwds)
    def GetContentsPane(self):
        return Panel(None)
    def SetButtonSizer(self, sizer):
        self.ButtonSizer = sizer

#import wxaddons.sized_controls as sc
#sc.__dict__.update(locals())

def GetDefaultBorder(self):
    border = 4
    if wx.Platform == "__WXMAC__":
        border = 6
    elif wx.Platform == "__WXMSW__":
        # MSW HIGs use dialog units, not pixels
        pnt = self.ConvertDialogPointToPixels(wx.Point(4, 4))
        border = pnt[0]
    elif wx.Platform == "__WXGTK__":
        border = 3

    return border

def SetDefaultSizerProps(self):
    item = self.GetParent().GetSizer().GetItem(self)
    item.SetProportion(0)
    item.SetFlag(wx.ALL)
    item.SetBorder(self.GetDefaultBorder())

def GetSizerProps(self):
    """
    Returns a dictionary of prop name + value
    """
    props = {}
    item = self.GetParent().GetSizer().GetItem(self)

    props['proportion'] = item.GetProportion()
    flags = item.GetFlag()

    if flags & border['all'] == border['all']:
        props['border'] = (['all'], item.GetBorder())
    else:
        borders = []
        for key in border:
            if flags & border[key]:
                borders.append(key)

        props['border'] = (borders, item.GetBorder())

    if flags & align['center'] == align['center']:
        props['align'] = 'center'
    else:
        for key in halign:
            if flags & halign[key]:
                props['halign'] = key

        for key in valign:
            if flags & valign[key]:
                props['valign'] = key

    for key in minsize:
        if flags & minsize[key]:
            props['minsize'] = key

    for key in misc_flags:
        if flags & misc_flags[key]:
            props[key] = "true"

    return props

def SetSizerProp(self, prop, value):
    pass

def SetSizerProps(self, props={}, **kwargs):
    allprops = {}
    allprops.update(props)
    allprops.update(kwargs)

    for prop in allprops:
        self.SetSizerProp(prop, allprops[prop])

def GetDialogBorder(self):
    border = 6
    if wx.Platform == "__WXMAC__" or wx.Platform == "__WXGTK__":
        border = 12
    elif wx.Platform == "__WXMSW__":
        pnt = self.ConvertDialogPointToPixels(wx.Point(7, 7))
        border = pnt[0]

    return border

def SetHGrow(self, proportion):
    data = self.GetUserData()
    if "HGrow" in data:
        data["HGrow"] = proportion
        self.SetUserData(data)

def GetHGrow(self):
    if self.GetUserData() and "HGrow" in self.GetUserData():
        return self.GetUserData()["HGrow"]
    else:
        return 0

def SetVGrow(self, proportion):
    data = self.GetUserData()
    if "VGrow" in data:
        data["VGrow"] = proportion
        self.SetUserData(data)


def GetVGrow(self):
    if self.GetUserData() and "VGrow" in self.GetUserData():
        return self.GetUserData()["VGrow"]
    else:
        return 0

def GetDefaultPanelBorder(self):
    # child controls will handle their borders, so don't pad the panel.
    return 0

import wx
# Why, Python?! Why do you make it so easy?! ;-)
wx.Dialog.GetDialogBorder = GetDialogBorder
wx.Panel.GetDefaultBorder = GetDefaultPanelBorder
wx.Notebook.GetDefaultBorder = GetDefaultPanelBorder
wx.SplitterWindow.GetDefaultBorder = GetDefaultPanelBorder

wx.Window.GetDefaultBorder = GetDefaultBorder
wx.Window.SetDefaultSizerProps = SetDefaultSizerProps
wx.Window.SetSizerProp = SetSizerProp
wx.Window.SetSizerProps = SetSizerProps
wx.Window.GetSizerProps = GetSizerProps

wx.SizerItem.SetHGrow = SetHGrow
wx.SizerItem.GetHGrow = GetHGrow
wx.SizerItem.SetVGrow = SetVGrow
wx.SizerItem.GetVGrow = GetVGrow