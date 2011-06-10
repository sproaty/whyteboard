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
Contains the application that is used to launch the program, provide command
line arguments/parsing and setting the program's locale/language.
"""

import os
import sys
import logging
import time
import wx
from optparse import OptionParser

from whyteboard.gui import GUI
from whyteboard.lib import ConfigObj, Validator
from whyteboard.misc import meta, get_path, get_home_dir, is_exe, to_unicode

logger = logging.getLogger('whyteboard')

#----------------------------------------------------------------------

class WhyteboardApp(wx.App):
    def OnInit(self):
        """
        Load config file, apply translation, parse arguments and delete any
        temporary filse left over from an update
        """
        startup_time = time.time()
        wx.SetDefaultPyEncoding("utf-8")
        self.SetAppName(u"whyteboard")  # used to identify app in $HOME/

        parser = OptionParser(version="Whyteboard %s" % meta.version)
        parser.add_option("-f", "--file", help="load FILE on load")
        parser.add_option("-c", "--conf", help="load configurations from CONF file")
        parser.add_option("--width", type="int", help="set canvas to WIDTH")
        parser.add_option("--height", type="int", help="set canvas to HEIGHT")
        parser.add_option("-u", "--update", action="store_true", help="check for a newer version of whyteboard")
        parser.add_option("-l", "--lang", help="set language. can be a country code or language (e.g. fr, french; nl, dutch)")
        parser.add_option("-d", "--debug", action="store_true", help="debug mode. more information about the program is logged")

        (options, args) = parser.parse_args()
        self.setup_logging(options.debug)
        logger.info("Program starting")
        logger.debug("Received command line options [%s] and args [%s]", options, args)

        preferences_file = options.conf or os.path.join(get_home_dir(), u"user.pref")      
        logger.debug("Setting up configuration from preferences file [%s]", preferences_file)

        config = ConfigObj(preferences_file, configspec=meta.config_scheme, encoding=u"utf-8")
        config.validate(Validator())
        
        self.set_language(config, options.lang)
        self.frame = GUI(config)
        self.frame.Show(True)

        try:
            _file = options.file or sys.argv[1]
            _file = os.path.abspath(to_unicode(_file))
            if os.path.exists(_file):
                self.frame.do_open(_file)
        except IndexError:
            pass

        x = options.width or self.frame.canvas.area[0]
        y = options.height or self.frame.canvas.area[1]
        self.frame.canvas.resize((x, y))

        self.delete_temp_files()
        if options.update:
            self.frame.on_update()

        logger.info("Startup complete, time taken: %.3fms", (time.time() - startup_time))
        return True

    def setup_logging(self, debug):
        logfile = os.path.join(get_home_dir(), u"whyteboard.log")
        fh = logging.FileHandler(logfile)
        ch = logging.StreamHandler()
        if debug:
            logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(levelname)s %(asctime)s %(message)s')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        logger.addHandler(fh)
        logger.addHandler(ch)
        

    def delete_temp_files(self):
        """
        Delete temporary files from an update. Remove a backup exe, otherwise
        iterate over the current directory (where the backup files will be) and
        remove any that matches the random file extension
        """
        if is_exe() and os.path.exists(u"wtbd-bckup.exe"):
            logger.debug("Removing backup EXE after performing an update")
            os.remove(u"wtbd-bckup.exe")
        else:
            path = get_path()
            for f in os.listdir(path):
                if f.find(meta.backup_extension) is not - 1:
                    os.remove(os.path.join(path, f))


    def set_language(self, config, option_lang=None):
        """
        Sets the user's language.
        """
        set_lang = False
        lang_name = config.get('language', '')
        logger.debug("Found language [%s] in config", lang_name)
        
        if option_lang:
            logger.debug("Attempting to set language from command line: [%s]", option_lang)
            country = wx.Locale.FindLanguageInfo(option_lang)
            if country:
                set_lang = True
                lang_name = country.Description
                self.locale = wx.Locale(country.Language)
                logger.debug("Using command-line set language [%s]", lang_name)
            else:
                logger.warning("Could not parse [%s] into a known locale/language", option_lang)
                
        if not set_lang:
            for x in meta.languages:
                if lang_name.capitalize() == 'Welsh':
                    self.locale = wx.Locale()
                    self.locale.Init(u"Cymraeg", u"cy", u"cy_GB.utf8")
                    break
                elif lang_name == x[0]:
                    logger.debug("Attempting to set language to [%s] from config", lang_name)
                    nolog = wx.LogNull()
                    self.locale = wx.Locale(x[2])

        if not hasattr(self, "locale"):
            logger.debug("No locale set, reverting to system language")
            self.locale = wx.Locale(wx.LANGUAGE_DEFAULT)
            config['language'] = wx.Locale.GetLanguageName(wx.LANGUAGE_DEFAULT)
            config.write()

        if not wx.Locale.IsOk(self.locale):
            logger.warning("Could not set language to [%s]", lang_name)
            wx.MessageBox(u"Error setting language to %s - reverting to English"
                          % lang_name, u"Whyteboard")
            if not set_lang:
                config['language'] = 'English'
                config.write()
            self.locale = wx.Locale(wx.LANGUAGE_ENGLISH)

        logger.info("Whyteboard is running in [%s]", wx.Locale.GetLanguageName(self.locale.GetLanguage()))
        langdir = os.path.join(get_path(), u'locale')
        logger.debug("Adding locale catalogue [%s]", langdir)
        self.locale.AddCatalogLookupPathPrefix(langdir)
        self.locale.AddCatalog(u"whyteboard")
        self.locale.AddCatalog(u'wxstd')

        # nasty fix for some translated strings not being applied
        meta.languages = meta.define_languages() 
        meta.types, meta.dialog_wildcard = meta.define_filetypes()