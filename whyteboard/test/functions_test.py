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


import os
import wx

from whyteboard.misc import (get_version_int, version_is_greater, get_wx_image_type,
                       get_time, format_bytes, convert_quality)
import whyteboard.misc.functions as functions

#----------------------------------------------------------------------

class TestFunctions:
    """Test the stand-alone application functions."""

    def test_get_version_int(self):
        """A list with the correct version is returned from a string"""
        assert get_version_int("0.4") == [0, 4, 0]
        assert get_version_int("0.4.0") == [0, 4, 0]


    def test_version_is_greater(self):
        """Ensuring certain versions are greater than one another"""
        assert version_is_greater("0.4", "0.4.0") == False
        assert version_is_greater("0.4.0", "0.4.0") == False
        assert version_is_greater("0.4", "0.4.1") == False
        assert version_is_greater("0.4.1", "0.4.15") == False
        assert version_is_greater("0.4.1", "0.3") == True
        assert version_is_greater("0.3.1", "0.3") == True


    def test_get_image_path(self):
        """
        The correct image paths are returned based on directory/file names
        """
        if os.name == "nt":
            functions.get_path = lambda: u"C:\ssss"
            assert functions.get_image_path(u"icons", u"test") == u'C:\ssss\images\icons\\test.png'
        else:
            functions.get_path = lambda: u'/blah'
            assert functions.get_image_path(u"icons", u"test") == u'/blah/images/icons/test.png', functions.get_image_path(u"icons", u"test")


    def test_format_bytes(self):
        """Byte values are correctly formatted to human-readable strings"""
        assert format_bytes(1024) == u"1.00KB"
        assert format_bytes(1030) == u"1.01KB"
        assert format_bytes(1048576) == u"1.00MB"
        assert format_bytes(1059061) == u"1.01MB"


    def test_convert_quality(self):
        """Correct ImageMagick convert strings are created (using Unicode data)"""
        im = u"/usr/bin/convert"
        f = u"/øøø/test.pdf"
        path = u"/øøø/"
        assert convert_quality("highest", im, f, path) == u'"%s" -density 300 "%s" -resample 120 -unsharp 0x.5 -trim +repage -bordercolor white -border 20 "%s"' % (im, f, path)
        assert convert_quality("high", im, f, path) == u'"%s" -density 250 "%s" -resample 100 -unsharp 0x.5 -trim +repage -bordercolor white -border 20 "%s"' % (im, f, path)
        assert convert_quality("normal", im, f, path) == u'"%s" -density 200 "%s" -resample 88 -unsharp 0x.5 -trim +repage -bordercolor white -border 20 "%s"' % (im, f, path)


    def test_get_time(self):
        """The correct time for the media player is returned"""
        assert get_time(0) == "00:00"
        assert get_time(1) == "00:01"
        assert get_time(10) == "00:10"
        assert get_time(45) == "00:45"
        assert get_time(60) == "01:00"
        assert get_time(119) == "01:59"
        assert get_time(3590) == "59:50"
        assert get_time(3600) == "1:00:00"
        assert get_time(7199) == "1:59:59"
        assert get_time(7200) == "2:00:00"


    def test_get_wx_image_type(self):
        """Correct wx.BITMAP_TYPE is returned"""
        assert get_wx_image_type("/blah.png") == wx.BITMAP_TYPE_PNG
        assert get_wx_image_type("blah.TifF") == wx.BITMAP_TYPE_TIF
        assert get_wx_image_type("/blah.JPG") == wx.BITMAP_TYPE_JPEG
        assert get_wx_image_type("/blah.jpeg") == wx.BITMAP_TYPE_JPEG