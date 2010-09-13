#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2009, 2010 by Steven Sproat
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
import wx
from optparse import OptionParser

from whyteboard.gui import GUI
from whyteboard.lib import ConfigObj, Validator
from whyteboard.misc import meta, get_path, get_home_dir, is_exe


#----------------------------------------------------------------------

class WhyteboardApp(wx.App):
    def OnInit(self):
        """
        Load config file, apply translation, parse arguments and delete any
        temporary filse left over from an update
        """
        wx.SetDefaultPyEncoding("utf-8")
        self.SetAppName(u"whyteboard")  # used to identify app in $HOME/

        parser = OptionParser(version="Whyteboard %s" % meta.version)
        parser.add_option("-f", "--file", help="load FILE on load")
        parser.add_option("-c", "--conf", help="load configurations from CONF file")
        parser.add_option("--width", type="int", help="set canvas to WIDTH")
        parser.add_option("--height", type="int", help="set canvas to HEIGHT")
        parser.add_option("-u", "--update", action="store_true", help="check for a newer version of whyteboard")
        parser.add_option("-l", "--lang", help="set language. can be a country code or language (e.g. fr, french; nl, dutch)")

        (options, args) = parser.parse_args()
        path = options.conf or os.path.join(get_home_dir(), u"user.pref")

        config = ConfigObj(path, configspec=meta.config_scheme, encoding=u"utf-8")
        config.validate(Validator())
        self.set_language(config, options.lang)
        self.frame = GUI(config)
        self.frame.Show(True)

        try:
            _file = options.file or sys.argv[1]
            _file = os.path.abspath(_file)
            if os.path.exists(_file):
                print _file.__repr__()
                self.frame.do_open(_file.decode("utf-8"))
        except IndexError:
            pass

        x = options.width or self.frame.canvas.area[0]
        y = options.height or self.frame.canvas.area[1]
        self.frame.canvas.resize((x, y))

        self.delete_temp_files()
        if options.update:
            self.frame.on_update()

        return True


    def delete_temp_files(self):
        """
        Delete temporary files from an update. Remove a backup exe, otherwise
        iterate over the current directory (where the backup files will be) and
        remove any that matches the random file extension
        """
        if is_exe() and os.path.exists(u"wtbd-bckup.exe"):
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

        if option_lang:
            country = wx.Locale.FindLanguageInfo(option_lang)
            if country:
                set_lang = True
                lang_name = country.Description
                self.locale = wx.Locale(country.Language)

        if not set_lang:
            for x in meta.languages:
                if lang_name.capitalize() == 'Welsh':
                    self.locale = wx.Locale()
                    self.locale.Init(u"Cymraeg", u"cy", u"cy_GB.utf8")
                    break
                elif lang_name == x[0]:
                    nolog = wx.LogNull()
                    self.locale = wx.Locale(x[2])

        if not hasattr(self, "locale"):  # now try sytem language
            self.locale = wx.Locale(wx.LANGUAGE_DEFAULT)
            config['language'] = wx.Locale.GetLanguageName(wx.LANGUAGE_DEFAULT)
            config.write()

        if not wx.Locale.IsOk(self.locale):
            wx.MessageBox(u"Error setting language to %s - reverting to English"
                          % lang_name, u"Whyteboard")
            if not set_lang:
                config['language'] = 'English'
                config.write()
            self.locale = wx.Locale(wx.LANGUAGE_ENGLISH)

        langdir = os.path.join(get_path(), u'locale')
        self.locale.AddCatalogLookupPathPrefix(langdir)
        self.locale.AddCatalog(u"whyteboard")

        reload(meta)  # fix for some translated strings not being applied