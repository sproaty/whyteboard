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
import tarfile
import zipfile
import distutils.dir_util

from whyteboard.misc import is_exe, get_home_dir, get_path, meta

logger = logging.getLogger("whyteboard.updater.extractor")

#----------------------------------------------------------------------

class UpdateFileExtractor(object):
    '''
    Handles extracting a downloaded .tar.gz or zip file containing the updated
    application.
    '''
    @staticmethod
    def extract(download):
        """
        Extract either a .zip or a .tar.gz file into the user's home folder,
        backs up the current program directory on Windows that contains the latest Whyteboard
        source code and resources
        """
        extracted_location = os.path.join(get_home_dir(), "whyteboard-" + download.version)
        backup_direcctory = os.path.join(get_home_dir(), "backup", meta.version)
        program_directory = get_path()
        archive = download.filesystem_path()
        logger.debug("Extracting archive file")

        logger.debug("Backing up current program [%s] to [%s]", program_directory, backup_direcctory)
        distutils.dir_util.copy_tree(program_directory, backup_direcctory)
        
        if is_exe():
            os.rename(sys.argv[0], "whyteboard-tmp.exe")
            _file = zipfile.ZipFile(archive)
        else:
            _file = tarfile.open(archive)
        _file.extractall(get_home_dir())
        _file.close()

        logger.debug("Moving extracted file directory [%s] into running program directory [%s]", extracted_location, program_directory)
        distutils.dir_util.copy_tree(extracted_location, program_directory)

        logger.debug("Cleaning up.")
        distutils.dir_util.remove_tree(extracted_location)
        os.remove(archive)