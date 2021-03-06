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
Generates the whyteboard.org/latest file for linux or windows, 
updating the filesizes of the exe or source
"""

import config
from ftplib import FTP


latest = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "resources", "latest"))

print "Uploading update file %s via FTP" % latest

ftp = FTP('ftp.whyteboard.org', config.ftp_username, config.ftp_password)
ftp.login()               # user anonymous, passwd anonymous@
ftp.storbinary('STOR /public_html/latest', open(latest))
ftp.close()

print "File stored."