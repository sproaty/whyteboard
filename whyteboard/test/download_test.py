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
Unit tests for the downloader and download objects
Mocks out urlllib to return a known file-like object 
"""

import unittest
from StringIO import StringIO

from whyteboard.download.downloader import Download, Downloader
from whyteboard.download.extractor import UpdateFileExtractor
from whyteboard.download.updater import Updater

from whyteboard.lib.mock import patch, Mock

#----------------------------------------------------------------------

def dummy_update_file():
    return StringIO("0.4\nwhyteboard-0.4.zip\n5587799\nwhyteboard-0.4.tar.gz\n372110")

def dummy_download():
    return Download(dummy_update_file().read())


#----------------------------------------------------------------------

class TestDownloader(unittest.TestCase):
    def setUp(self):
        self.download = dummy_download()

    @patch('urllib.urlopen')
    def test_get_latest_version(self, urlopen):
        # given
        urlopen.return_value = dummy_update_file()

        # when
        download = Downloader.get_latest_version()

        # then
        self.assertEqual("0.4", download.version)
        self.assertEqual("whyteboard-0.4.zip", download.executable_filename)
        self.assertEqual("5587799", download.executable_size)
        self.assertEqual("whyteboard-0.4.tar.gz", download.source_filename)
        self.assertEqual("372110", download.source_size)


    @patch('urllib.urlopen')
    def test_get_latest_version_connection_error(self, urlopen):
        # given
        urlopen.side_effect = IOError("oh no!")

        # when
        download = Downloader.get_latest_version()

        # then
        self.assertFalse(download)



    @patch('os.path.join')
    @patch('whyteboard.download.downloader.get_home_dir')
    @patch('urllib.urlretrieve')
    def test_download(self, urlretrieve, get_home_dir, os_path_join):
        # given
        callback = lambda x, y, z: x
        urlretrieve.return_value = StringIO("a file")
        get_home_dir.return_value = "/home/user/dir"
        os_path_join.return_value = get_home_dir() + "/tmp-file.zip"

        # when
        result = Downloader.download(self.download, callback)

        # then
        url = 'http://whyteboard.googlecode.com/files/whyteboard-0.4.tar.gz'
        urlretrieve.assert_called_with(url, '/home/user/dir/tmp-file.zip', callback)


#----------------------------------------------------------------------

@patch('whyteboard.download.downloader.is_exe')
class TestDownload(unittest.TestCase):
    def setUp(self):
        self.download = dummy_download()

    def test_download_filetype_exe(self, is_exe):
        # given
        is_exe.return_value = True

        # when
        filetype = dummy_download().filetype()

        # then
        self.assertEqual("zip", filetype)

    def test_download_filetype_source(self, is_exe):
        # given
        is_exe.return_value = False

        # when
        filetype = dummy_download().filetype()

        # then
        self.assertEqual("tar.gz", filetype)

    def test_download_filesize_exe(self, is_exe):
        # given
        is_exe.return_value = True

        # when
        filesize = dummy_download().filesize()

        # then
        self.assertEqual("5.33MB", filesize)

    def test_download_filesize_source(self, is_exe):
        # given
        is_exe.return_value = False

        # when
        filesize = dummy_download().filesize()

        # then
        self.assertEqual("363.39KB", filesize)


#----------------------------------------------------------------------


class TestUpdateFileExtractor(unittest.TestCase):
    def setUp(self):
        self.download_file = dummy_download()

#    @patch('whyteboard.download.extractor.get_path')
#    @patch('whyteboard.download.extractor.get_home_dir')
#    @patch('whyteboard.download.extractor.distutils.dir_util')
#    @patch('whyteboard.download.extractor.is_exe')
#    @patch('zipfile.ZipFile')
#    @patch('os.remove')
#    def test_extract_is_executable(self, remove, ZipFile, is_exe, dir_uti,
#                                   get_home_dir, get_path):
#        # given
#        is_exe.return_value = True
#        get_path.return_value = "C:\whyteboard-running-directory"
#        get_home_dir.return_value = "C:\ggfdgnfgnjgdjgndgfjdkgfd\frest\\"
#        with patch.dict('whyteboard.misc.meta', {'version': "0.42"}):          
#            
#            # when
#            UpdateFileExtractor.extract(self.download_file)
#    
#            # then
#            ZipFile.assert_called_once_with(self.download_file.filesystem_path())
#            #remove.assert_called_once_with(self.download_file)      


#----------------------------------------------------------------------


class TestUpdate(unittest.TestCase):
    def setUp(self):
        self.updater = Updater()
