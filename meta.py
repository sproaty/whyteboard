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
Contains meta data for the program, such as version, whether transparency is
supported, language mappings.

This is a static class with no dependencies besides wx, to allow it to be used 
by other modules easily
"""

import wx

class Singleton(type):
    """
    Singleton metaclass. Code taken from Task Coach, www.taskcoach.org
    """             
    def __call__(class_, *args, **kwargs):
        if not class_.hasInstance():
            class_.instance = super(Singleton, class_).__call__(*args, **kwargs)
        return class_.instance
    
    def deleteInstance(class_):
        """
        Delete the (only) instance. This method is mainly for unittests so
        they can start with a clean slate.
        """
        if class_.hasInstance():
            del class_.instance
    
    def hasInstance(class_):
        """
        Has the (only) instance been created already?
        """
        return hasattr(class_, 'instance')


#----------------------------------------------------------------------


#class MetaData(object):
#    """
#    The MetaData class containing static methods
#    """
#    __metaclass__ = Singleton
#    #transparent = False
#    version = "0.39.4"
#    
#    def __init__(self):
#        pass
version = "0.39.4"
#transparent = False
    
def find_transparent():
    global transparent
    try:
        dc = wx.MemoryDC()
        dc.SelectObject(wx.EmptyBitmap(10, 10))
        x = wx.GCDC(dc)
        transparent = True
    except NotImplementedError:
        transparent = False        