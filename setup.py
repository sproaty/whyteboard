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

from whyteboard.misc import meta
from distutils.core import setup
from py2exe.build_exe import py2exe

import glob
import os

text = """
===========
Whyteboard
===========

Whyteboard is a free painting application for Linux, Windows and Mac. It is
suited towards creating visual presentations and for overlaying PDF images
with annotations


Features
=========

* Draw on a canvas using common tools: pen, rectangle, circle, text
* Annotate over PDF files
* Drawn shapes can be resized, moved, rotated and re-coloured
* Tabbed drawing: each tab represents a whiteboard "sheet". Each sheet has unlimited undo/redo operations
* Your drawing history can be replayed on a per-sheet basis
* Each sheet has a thumbnail of the canvas that updates as you draw
* Closed sheets can be re-opened, restoring their data
* Notes, similar to Post-It Notes. A tree in a side panel gives an overview of all notes
* Resize the canvas easily by dragging it around
* Embed an audio/video player onto the canvas
* Translated into many languages (French, German, Spanish, Italian, Galician, Russian, Dutch, and more)
"""


def find_data_files(source,target,patterns):
    """Locates the specified data-files and returns the matches
    in a data_files compatible format.

    source is the root of the source data tree.
        Use '' or '.' for current directory.
    target is the root of the target data tree.
        Use '' or '.' for the distribution directory.
    patterns is a sequence of glob-patterns for the
        files you want to copy.
    """
    if glob.has_magic(source) or glob.has_magic(target):
        raise ValueError("Magic not allowed in src, target")
    ret = {}
    for pattern in patterns:
        pattern = os.path.join(source,pattern)
        for filename in glob.glob(pattern):
            if os.path.isfile(filename):
                targetpath = os.path.join(target,os.path.relpath(filename,source))
                path = os.path.dirname(targetpath)
                ret.setdefault(path,[]).append(filename)
    return sorted(ret.items())



# manifest_template = """
# <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
# <assembly xmlns="urn:schemas-microsoft-com:asm.v1"
# manifestVersion="1.0">
# <assemblyIdentity version="0.64.1.0" processorArchitecture="x86" name="Controls" type="win32" />
# <description>Whyteboard</description>
# <dependency>
#     <dependentAssembly>
#         <assemblyIdentity type="win32" name="Microsoft.Windows.Common-Controls" version="6.0.0.0" processorArchitecture="X86" publicKeyToken="6595b64144ccf1df" language="*" />
#     </dependentAssembly>
# </dependency>
# </assembly>
# """

class Target(object):
    """ A simple class that holds information on our executable file. """
    def __init__(self, **kw):
        """ Default class constructor. Update as you need. """
        self.__dict__.update(kw)


includes = []
excludes = ['_ctypes', '_gtkagg', '_ssl', '_tkagg', 'bsddb', 'bz2',
            'calendar', 'compiler', 'curses', 'difflib', 'email',
            'ftplib', 'pywin.debugger', 'pywin.debugger.dbgcon',
            'pywin.dialogs', 'pywintypes26.dll', 'tcl', 'Tkconstants',
            'Tkinter', 'unittest', 'win32api', 'win32con', 'doctest', 'pdb', 'unicodedata', 'pyexpat', 'xml']
packages = []
dll_excludes = ['libgdk-win32-2.0-0.dll', 'libgobject-2.0-0.dll', 'pyexpat',
                'pywintypes32.dll', 'tcl84.dll', 'tk84.dll']
icon_resources = [(1, os.path.join(os.path.dirname(os.path.abspath(__file__)), "buildfiles/resources/whyteboard.ico"))]
#other_resources = [(24, 1, manifest_template)]


GUI2Exe_Target_1 = Target(
    script = "whyteboard.py",
    icon_resources = icon_resources,
    #other_resources = other_resources,
    dest_base = "whyteboard",
    version = meta.version,
    company_name = "Steven Sproat",
    author = "Steven Sproat",
    author_email = "sproaty@gmail.com",
    copyright = "GPL 3",
    name = "Whyteboard"
)

setup(
    data_files = find_data_files('', '', ['README.txt', 'DEVELOPING.txt', 'LICENSE.txt', 'TODO.txt', 'CHANGELOG.txt',
                                          'images/*/*', 'locale/*/*/*', 'whyteboard-help/*']),

    options = {"py2exe": {"compressed": 2,
                          "optimize": 2,
                          "includes": includes,
                          "excludes": excludes,
                          "packages": packages,
                          "dll_excludes": dll_excludes,
                          "bundle_files": 1,
                          "dist_dir": "dist",
                          "xref": False,
                          "skip_archive": False,
                          "ascii": False,
                          "custom_boot_script": '',
                         }
              },

    zipfile = None,
    windows = [GUI2Exe_Target_1],

    description = 'A simple drawing program',
    long_description = text,
    classifiers = [
          'Development Status :: 4 - Beta',
          'Environment :: MacOS X',
          'Environment :: Win32 (MS Windows)',
          'Environment :: X11 Applications',
          'Intended Audience :: End Users/Desktop',
          'Intended Audience :: Education',
          'License :: OSI Approved :: GNU General Public License (GPL)',
          'Natural Language :: Arabic',
          'Natural Language :: Catalan',
          'Natural Language :: Chinese (Traditional)',
          'Natural Language :: Czech',
          'Natural Language :: Dutch',
          'Natural Language :: English',
          'Natural Language :: French',
          'Natural Language :: Galician',
          'Natural Language :: German',
          'Natural Language :: Hindi',
          'Natural Language :: Italian',
          'Natural Language :: Japanese',
          'Natural Language :: Portuguese',
          'Natural Language :: Russian',
          'Natural Language :: Spanish',
          'Operating System :: OS Independent',
          'Programming Language :: Python',
          'Programming Language :: Python :: 2.5',
          'Programming Language :: Python :: 2.6',
          'Programming Language :: Python :: 2.7',
          'Topic :: Multimedia',
          'Topic :: Multimedia :: Graphics',
          'Topic :: Multimedia :: Graphics :: Editors',
          'Topic :: Multimedia :: Graphics :: Editors :: Raster-Based',
          'Topic :: Multimedia :: Graphics :: Presentation',
          'Topic :: Multimedia :: Graphics :: Viewers'
          ],
)