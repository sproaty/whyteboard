#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Mock wxpython widgets for unit testing

The classes and their methods are not complete -- I've just added them as
I needed them. It should be fairly straightforward to add any other classes/methods
you need.

MIT License

Example:
    >>> import fakewidgets
    >>> import wx
    >>> frame = wx.Frame(None, -1, "Frame")
    >>> frame
    <fakewidgets.Frame object at 0x00C5E6D0>
"""

import core
import flatnotebook
import html
import lib.scrolledpanel
import lib.colourselect
import lib.buttons
import media.mediactrl
import sized
import version