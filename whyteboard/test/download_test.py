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

import os
import sys
import unittest
from StringIO import StringIO

from whyteboard.updater.downloader import Download, Downloader
from whyteboard.updater.extractor import UpdateFileExtractor
from whyteboard.updater.updater import Updater

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
    @patch('whyteboard.updater.downloader.get_home_dir')
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

@patch('whyteboard.updater.downloader.is_exe')
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

#    @patch('whyteboard.updater.extractor.get_path')
#    @patch('whyteboard.updater.extractor.get_home_dir')
#    @patch('whyteboard.updater.extractor.distutils.dir_util')
#    @patch('whyteboard.updater.extractor.is_exe')
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


class TestUpdater(unittest.TestCase):
    def setUp(self):
        self.updater = Updater()
        self.updater.download = dummy_download()
        
        
    def test_can_update_download_is_newer(self):
        # given               
        with patch.dict('whyteboard.misc.meta.__dict__', {'version': "0.3"}):
            # when
            can_update = self.updater.can_update()
                
            # then
            self.assertTrue(can_update)
            
            
    def test_can_update_download_is_same_version(self):
        # given
        with patch.dict('whyteboard.misc.meta.__dict__', {'version': "0.4"}):
            # when
            can_update = self.updater.can_update()
                
            # then
            self.assertFalse(can_update)   


    def test_can_update_download_is_older(self):
        # given
        with patch.dict('whyteboard.misc.meta.__dict__', {'version': "0.5"}):
            # when
            can_update = self.updater.can_update()
                
            # then
            self.assertFalse(can_update)       
            


    @patch('whyteboard.updater.updater.is_exe')
    def test_restart_args_windows_exe(self, is_exe):
        # given
        is_exe.return_value = True
        argv = ['whyteboard.exe']
        current_dir = os.path.dirname(os.path.abspath(sys.argv[1]))
        
        with patch.dict('sys.__dict__', {'argv': argv}):
            # when
            arguments = self.updater.restart_args()
            
            # then
            expected = os.path.join(current_dir, argv[0])
            self.assertEqual([expected, [expected]], arguments)        
            
            
            
    @patch('whyteboard.updater.updater.is_exe')
    def test_restart_args_windows_exe_with_file(self, is_exe):
        # given
        is_exe.return_value = True
        _file = u"c:\test\whyteboard file.wtbd"
        argv = ['whyteboard.exe']
        current_dir = os.path.dirname(os.path.abspath(sys.argv[1]))
        
        with patch.dict('sys.__dict__', {'argv': argv}):
            # when
            arguments = self.updater.restart_args(_file)
            
            # then
            expected = os.path.join(current_dir, argv[0])
            self.assertEqual([expected, [expected, u"--file", '"%s"' % _file]], arguments)     
            
            
    @patch('whyteboard.updater.updater.is_exe')
    @patch('whyteboard.updater.updater.logger')
    def test_restart_args_windows_exe_with_debug_enabled(self, logger, is_exe):
        # given
        is_exe.return_value = True
        logger.is_enabled_for.return_value = True
        argv = ['whyteboard.exe']
        current_dir = os.path.dirname(os.path.abspath(sys.argv[1]))
        
        with patch.dict('sys.__dict__', {'argv': argv}):
            # when
            arguments = self.updater.restart_args()
            
            # then
            expected = os.path.join(current_dir, argv[0])
            self.assertEqual([expected, [expected, u"--debug"]], arguments)   
            
            
    @patch('whyteboard.updater.updater.is_exe')
    def test_restart_args_source(self, is_exe):
        # given
        is_exe.return_value = False
        argv = ['whyteboard.py']
        
        with patch.dict('sys.__dict__', {'argv': argv}):
            # when
            arguments = self.updater.restart_args()
            
            # then
            self.assertEqual(['python', ['python', argv[0]]], arguments)
            
                                                         
    @patch('whyteboard.updater.updater.is_exe')
    def test_restart_args_source_with_filename(self, is_exe):
        # given
        is_exe.return_value = False
        argv = ['whyteboard.py']
        _file = "c:\test\whyteboard test.wtbd"
        
        with patch.dict('sys.__dict__', {'argv': argv}):
            # when
            arguments = self.updater.restart_args(_file)
            
            # then
            self.assertEqual(['python', ['python', argv[0], "--file", '"%s"' % _file]], arguments)  
            
                                                                                                                               
    @patch('whyteboard.updater.updater.is_exe')
    @patch('whyteboard.updater.updater.logger')
    def test_restart_args_source_with_debug_and_filename(self, logger, is_exe):
        # given
        is_exe.return_value = False
        logger.is_enabled_for.return_value = True
        argv = ['whyteboard.py']
        _file = "c:\test\whyteboard test.wtbd"
        
        with patch.dict('sys.__dict__', {'argv': argv}):
            # when
            arguments = self.updater.restart_args(_file)
            
            # then
            self.assertEqual(['python', ['python', argv[0], "--file", '"%s"' % _file, "--debug"]], arguments)    