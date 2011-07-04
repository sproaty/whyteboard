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

import logging

from whyteboard.misc import meta
from whyteboard.lib import ConfigObj, Validator

logger = logging.getLogger("whyteboard.core.config")

#----------------------------------------------------------------------

class Config(object):
    '''
    An interface for Whyteboard's configuration instead of accessing the config
    dictionary directly.
    '''
    def __init__(self, preferences_file):
        self.config = ConfigObj(preferences_file, configspec=meta.config_scheme, encoding=u"utf-8")
        self.config.validate(Validator())

    def write(self):
        self.config.write()
        
    def colours(self):
        return [x for x in self.config["colour%s" % x]]

    def colour(self, position):
        return self.config["colour%s" % position]

    def bmp_select_transparent(self, value=None):
        if not value:
            return self.config["bmp_select_transparent"]
        self.config["bmp_select_transparent"] = value

    def colour_grid(self, value=None):
        if not value:
            return self.config["colour_grid"]
        self.config["colour_grid"] = value

    def convert_quality(self, value=None):
        if not value:
            return self.config["convert_quality"]
        self.config["convert_quality"] = value

    def default_font(self, value=None):
        if not value:
            return self.config["default_font"]
        self.config["default_font"] = value

    def default_width(self, value=None):
        if not value:
            return self.config["default_width"]
        self.config["default_width"] = value

    def default_height(self, value=None):
        if not value:
            return self.config["default_height"]
        self.config["default_height"] = value

    def imagemagick_path(self, value=None):
        if not value:
            return self.config["imagemagick_path"]
        self.config["imagemagick_path"] = value

    def language(self, value=None):
        if not value:
            return self.config["language"]
        self.config["language"] = value

    def last_opened_dir(self, value=None):
        if not value:
            return self.config["last_opened_dir"]
        self.config["last_opened_dir"] = value

    def print_title(self, value=None):
        if not value:
            return self.config["print_title"]
        self.config["print_title"] = value

    def statusbar(self, value=None):
        if not value:
            return self.config["statusbar"]
        self.config["statusbar"] = value

    def tool_preview(self, value=None):
        if not value:
            return self.config["tool_preview"]
        self.config["tool_preview"] = value

    def toolbar(self, value=None):
        if not value:
            return self.config["toolbar"]
        self.config["toolbar"] = value