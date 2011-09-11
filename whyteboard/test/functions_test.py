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


import os
from wx import BITMAP_TYPE_PNG, BITMAP_TYPE_JPEG, BITMAP_TYPE_TIF
import unittest

from whyteboard.misc import (get_version_int, version_is_greater, get_wx_image_type,
                       get_time, format_bytes, convert_quality, is_save_file,
                       versions_are_equal, is_new_version)
import whyteboard.misc.functions as functions

#----------------------------------------------------------------------

class TestFunctions(unittest.TestCase):
    """Test the stand-alone application functions."""

    def test_get_version_int(self):
        """
        A list with the correct version is returned from a string
        """
        self.assertEqual([1, 0, 0], get_version_int("1"))
        self.assertEqual([1, 4, 0], get_version_int("1.4"))
        self.assertEqual([1, 4, 4], get_version_int("1.4.4"))


    def test_version_is_greater(self):
        """
        Ensuring certain versions are greater than one another
        """
        self.assertTrue(version_is_greater("1.0.1", "1"))
        self.assertTrue(version_is_greater("1.0.1", "1.0"))
        self.assertTrue(version_is_greater("0.42", "0.41.1"))
        self.assertTrue(version_is_greater("0.4.1", "0.4"))
        self.assertTrue(version_is_greater("0.4.15", "0.4.1"))
        self.assertFalse(version_is_greater("1.0.0", "1"))
        self.assertFalse(version_is_greater("1.0", "1"))
        self.assertFalse(version_is_greater("0.4.0", "0.4"))
        self.assertFalse(version_is_greater("0.4.0", "0.4.0"))

    def test_version_is_equal(self):
        """
        Ensuring certain versions are greater than one another
        """
        self.assertTrue(versions_are_equal("0.4.0", "0.4"))
        self.assertTrue(versions_are_equal("1.0.0", "1"))
        self.assertTrue(versions_are_equal("1.0", "1"))
        self.assertFalse(versions_are_equal("0.4.1", "0.4"))
        self.assertFalse(versions_are_equal("1.0.1", "1"))
        self.assertFalse(versions_are_equal("1.3", "0.3"))
        self.assertFalse(versions_are_equal("0.4.0", "0.4.1"))
        self.assertFalse(versions_are_equal("0.4.1", "0.4.15"))
        self.assertFalse(versions_are_equal("0.4.1", "0.3"))

    def test_is_new_version(self):
        """
        Checking versions trigger an update
        """
        self.assertTrue(is_new_version("0.41.0", "0.41.1"))
        self.assertTrue(is_new_version("0.41.0", "0.42"))
        self.assertFalse(is_new_version("0.41", "0.41.0"))
        self.assertFalse(is_new_version("0.41.1", "0.41.1"))

    def test_get_image_path(self):
        """
        The correct image paths are returned based on directory/file names
        """
        if os.name == "nt":
            functions.get_path = lambda: u"C:\ssss"
            self.assertEquals(functions.get_image_path(u"icons", u"test"), u'C:\ssss\images\icons\\test.png')
        else:
            functions.get_path = lambda: u'/blah'
            self.assertEquals(functions.get_image_path(u"icons", u"test"), u'/blah/images/icons/test.png')


    def test_format_bytes(self):
        """
        Byte values are correctly formatted to human-readable strings
        """
        self.assertEquals(u"1.00KB", format_bytes(1024))
        self.assertEquals(u"1.01KB", format_bytes(1030))
        self.assertEquals(u"1.00MB", format_bytes(1048576))
        self.assertEquals(u"1.01MB", format_bytes(1059061))


    def test_convert_quality(self):
        """
        Correct ImageMagick convert strings are created (using Unicode data)
        """
        im = u"/usr/bin/convert"
        f = u"/øøø/test.pdf"
        path = u"/øøø/"
        assert convert_quality("highest", im, f, path) == u'"%s" -density 300 "%s" -resample 120 -unsharp 0x.5 -trim +repage -bordercolor white -border 20 "%s"' % (im, f, path)
        assert convert_quality("high", im, f, path) == u'"%s" -density 250 "%s" -resample 100 -unsharp 0x.5 -trim +repage -bordercolor white -border 20 "%s"' % (im, f, path)
        assert convert_quality("normal", im, f, path) == u'"%s" -density 200 "%s" -resample 88 -unsharp 0x.5 -trim +repage -bordercolor white -border 20 "%s"' % (im, f, path)


    def test_get_time(self):
        """
        The correct time for the media player is returned
        """
        self.assertEqual("00:00", get_time(0)) 
        self.assertEqual("00:01", get_time(1))
        self.assertEqual("00:10", get_time(10))
        self.assertEqual("01:00", get_time(60))
        self.assertEqual("01:59", get_time(119))
        self.assertEqual("59:50", get_time(3590))
        self.assertEqual("1:00:00", get_time(3600))
        self.assertEqual("1:59:59", get_time(7199))
        self.assertEqual("2:00:00", get_time(7200))


    def test_get_wx_image_type(self):
        """
        Correct wx.BITMAP_TYPE is returned
        """
        self.assertEqual(BITMAP_TYPE_PNG, get_wx_image_type("/blah.png"))
        self.assertEqual(BITMAP_TYPE_TIF, get_wx_image_type("blah.TifF"))
        self.assertEqual(BITMAP_TYPE_JPEG, get_wx_image_type("/blah.JPG"))
        self.assertEqual(BITMAP_TYPE_JPEG, get_wx_image_type("/blah.jpeg"))


    def test_is_save_file(self):
        """
        Filename indicates Whyteboard save type
        """
        self.assertTrue(is_save_file("blah.WTbd"))
        self.assertTrue(is_save_file("blah.wtbd"))
        self.assertFalse(is_save_file("blahwtbd"))
        self.assertFalse(is_save_file("/blah.png"))
        self.assertFalse(is_save_file("wtbd"))