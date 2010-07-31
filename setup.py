#!/usr/bin/env python

from distutils.core import setup
from whyteboard import meta

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

setup(
    name = 'Whyteboard',
    version = meta.version,
    author = 'Steven Sproat',
    author_email = 'sproaty@gmail.com',
    url = 'http://whyteboard.org',
    license = 'GPL v3',
    description = 'A simple drawing program that can be used to annotate PDF files',
    long_description = text,

    package_dir = {'whyteboard': 'whyteboard/',
                   'whyteboard.gui': 'whyteboard/gui',
                   'whyteboard.lib': 'whyteboard/lib',
                   'whyteboard.lib.pubsub': 'whyteboard/lib/pubsub',
                   'whyteboard.lib.pubsub.core': 'whyteboard/lib/pubsub/core',
                   'whyteboard.lib.pubsub.utils': 'whyteboard/lib/pubsub/utils'},

    packages = ['whyteboard', 'whyteboard.gui', 'whyteboard.lib', 'whyteboard.lib.pubsub',
                'whyteboard.lib.pubsub.core', 'whyteboard.lib.pubsub.utils'],
    py_modules = ['whyteboard'],
    scripts = ['whyteboard.py'],

    classifiers=[
          'Development Status :: 4 - Beta',
          'Environment :: MacOS X',
          'Environment :: Win32 (MS Windows)',
          'Environment :: X11 Applications',
          'Intended Audience :: End Users/Desktop',
          'Intended Audience :: Education',
          'License :: OSI Approved :: GNU General Public License (GPL)',
          'Operating System :: MacOS :: MacOS X',
          'Operating System :: Microsoft :: Windows',
          'Operating System :: POSIX',
          'Programming Language :: Python',
          'Programming Language :: Python :: 2.5',
          'Programming Language :: Python :: 2.6',
          'Programming Language :: Python :: 2.7',
          'Topic :: Multimedia',
          'Topic :: Multimedia :: Graphics',
          'Topic :: Multimedia :: Graphics :: Editors',
          'Topic :: Multimedia :: Graphics :: Editors :: Raster-Based'
          ],

)
