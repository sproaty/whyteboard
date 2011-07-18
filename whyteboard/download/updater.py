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
import sys
import logging

from downloader import Downloader, Download
from extractor import UpdateFileExtractor

from whyteboard.misc import meta, is_exe, is_new_version

logger = logging.getLogger("whyteboard.download.updater")

#----------------------------------------------------------------------

class Updater(object):
    '''
    Can query the server for information on the latest release, check whether
    the program can be downloaded, downloads and extracts the latest files and
    update Whyteboard 
    '''
    def __init__(self):
        self.download = None

    def download_file(self, callback):
        return Downloader.download(self.download, callback)

    def extract(self):
        return UpdateFileExtractor.extract(self.download)

    def get_latest_version_info(self):
        self.download = Downloader.get_latest_version()
        return self.download

    def can_update(self):
        logger.debug("Checking for updates")
        new_version = is_new_version(meta.version, self.download.version)
        if not new_version:
            logger.info("Nothing to update.")
        logger.info("New version available: [%s]. Current version is [%s]", 
                    self.download.version, meta.version)
        return new_version


    def restart_args(self, filename=None):
        """
        Returns command-line arguments to pass to os.execvp when restarting
        after an update
        """
        if is_exe():
            exe_path = os.path.abspath(sys.argv[0])
            args = [exe_path, [exe_path]]
        else:
            args = [u'python', [u'python', sys.argv[0]]]

        if filename:
            name = u'"%s"' % filename
            args[1].append(u"--file")
            args[1].append(name)
        if logger.isEnabledFor(logging.DEBUG):
            args[1].append(u"--debug")
            
        logger.debug("Restarting program, passing command-line args: [%s]", args)
        return args