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
This is the main module which fires up Whyteboard. It checks if the installed
wxPython version is recent enough, as Whyteboard uses newer versions' features.
"""

import sys
import webbrowser

if not hasattr(sys, 'frozen'):
    WXVER = '2.8.9'
    import wxversion
    if not wxversion.checkInstalled(WXVER):
        import wx
        app = wx.App(False)

        wx.MessageBox("The minimum required version of wxPython, \n%s is not installed." % WXVER,
                      "wxPython Version Error")
        app.MainLoop()
        webbrowser.open("http://www.wxpython.org/download.php")
        sys.exit()


import wx
from whyteboard.gui import WhyteboardApp

WhyteboardApp().MainLoop()