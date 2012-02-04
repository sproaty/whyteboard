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
import logging

from whyteboard.misc import meta, get_home_dir
from whyteboard.lib import ConfigObj, Validator

logger = logging.getLogger("whyteboard.core.config")

#----------------------------------------------------------------------

class Config(object):
    '''
    An interface for Whyteboard's configuration instead of accessing the config
    dictionary directly.
    This is implemented as a singleton.
    '''
    _instance = None
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Config, cls).__new__(cls, *args, **kwargs)
        return cls._instance
    
    def init(self, preferences_file=None):                       
        if not preferences_file:
            preferences_file = os.path.join(get_home_dir(), u"user.pref")

        logger.debug("Setting up configuration from preferences file [%s]", preferences_file)              
        self.config = ConfigObj(preferences_file, configspec=meta.config_scheme, encoding=u"utf-8",
                                default_encoding=u'utf-8')
        self.config.validate(Validator())
    
    def clone(self):
        config = super(Config, Config).__new__(Config)
        config.init()
        return config
    
    def filename(self):
        return self.config.filename
    
    def write(self):
        self.config.write()
        
    def get(self, attr):
        return self.config.get(attr, '')
        
    def colours(self):
        return [x for x in self.config["colour%s" % x]]

    def colour(self, position, new_colour=None):
        if not new_colour:
            return self.config["colour%s" % position]
        self.config["colour%s" % position] = new_colour

    def bmp_select_transparent(self, value=None):
        if value is None:
            return self.config["bmp_select_transparent"]
        self.config["bmp_select_transparent"] = value

    def colour_grid(self, value=None):
        if value is None:
            return self.config["colour_grid"]
        self.config["colour_grid"] = value

    def convert_quality(self, value=None):
        if not value:
            return self.config["convert_quality"]
        self.config["convert_quality"] = value

    def default_font(self, value=None):
        if not value:
            if 'default_font' in self.config:
                return self.config["default_font"]
            return None
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
            if 'imagemagick_path' in self.config:
                return self.config["imagemagick_path"]
            return None        
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
        if value is None:
            return self.config["print_title"]
        self.config["print_title"] = value

    def statusbar(self, value=None):
        if value is None:
            return self.config["statusbar"]
        self.config["statusbar"] = value

    def tool_preview(self, value=None):
        if value is None:
            return self.config["tool_preview"]
        self.config["tool_preview"] = value

    def toolbar(self, value=None):
        if value is None:
            return self.config["toolbar"]
        self.config["toolbar"] = value