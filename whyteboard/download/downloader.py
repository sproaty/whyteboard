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
Classes for downloading the latest Whyteboard .zip/.tar.gz or .exe file and
representing that download
"""

import os
import logging
import urllib

from whyteboard.misc import format_bytes, get_home_dir, is_exe

logger = logging.getLogger("whyteboard.download.downloader")

#----------------------------------------------------------------------

BASE_DOWNLOAD_URL = u"http://whyteboard.googlecode.com/files"
UPDATE_FILE_URL = U"http://whyteboard.org/latest"


class Downloader(object):
    """
    Downloads version information for the latest Whyteboard release, and 
    can download the new release.
    """
    @staticmethod
    def get_latest_version():
        """
        Returns a Download object, or False if there was an error
        """
        try:
            html = urllib.urlopen(UPDATE_FILE_URL).read()
        except IOError:
            logger.error("Could not connect to update site [%s]", UPDATE_FILE_URL)
            return False

        logger.debug("Received latest update file: [%s]", html.split("\n"))
        return Download(html)


    @staticmethod
    def download(download, callback):
        """
        Downloads the file to the hard drive, and fires off the urlretrieve
        callback function
        """
        url = u"%s/%s" % (BASE_DOWNLOAD_URL, download.filename())
        
        logger.debug("Downloading file [%s] to [%s]", url, download.filesystem_path())
        
        try:
            urllib.urlretrieve(url, download.filesystem_path(), callback)
            return True
        except IOError:
            return False


class Download(object):
    """
    Represents Whyteboard's download for a new program version 
    """
    def __init__(self, html):
        html = html.split("\n")
        self.version = html[0]
        self.executable_filename = html[1]
        self.executable_size = html[2]
        self.source_filename = html[3]
        self.source_size = html[4]

    def filetype(self):
        return u"zip" if is_exe() else u"tar.gz"

    def filename(self):
        return self.executable_filename if is_exe() else self.source_filename

    def filesize(self):
        return format_bytes(self.executable_size if is_exe() else self.source_size)
    
    def raw_filesize(self):
        return self.executable_size if is_exe() else self.source_size
        
    def filesystem_path(self):
        filename = '~tmp-wb-%s.%s' % (self.version, self.filetype()) 
        return os.path.join(get_home_dir(), filename)