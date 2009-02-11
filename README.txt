Whyteboard 0.28 - simple image/PDF/postscript file annotator
https://launchpad.net/whyteboard -- http://code.google.com/p/whyteboard/
Wed 11 Feb 2009 03:57:20 GMT

*** TO RUN ***

First, you need Python, wxPython and ImageMagick.
http://python.org/download/
http://www.wxpython.org/download.php
http://www.imagemagick.net

Next, download the files from either Launchpad's source code browser or a tarred
archive from Google Code.

Run any of the .py to launch the program

If nothing happens, try launching one of the scripts from the console:
 python whyteboard.py
see what error occured and let me know, <sproaty -at- gmail -dot- com>


*** KNOWN BUGS ***

- Saving/loading your drawings isn't working.
- Scrolling horizontally/vertically isn't working correctly - major issue
- Undo/redo being slightly broken because you can add "blank" shapes that fills
   up the undo list
- Text input box will overwrite anything drawn "over" it
- Hard to actually see the text boxes' locations without adding in borders
- Text input - 25 character limit, no multilines, font etc (yet)


*** VERSION HISTORY ***

11 Feb 2009 - Fixed history replaying, added pause/ stop the replay. Fixed a bug
               with the converting progress where the bar increased in response
               to mouse movement - now it's increased by a timer.
10 Feb 2009 - Converting PDF pops up a "converting" progress bar
10 Feb 2009 - More code "unification", cleaner code, deleting temporary files,
               loading multiple PDF/PS/SVG files
09 Feb 2009 - Code refactored, performance increased ten-fold, some bug fixes
03 Feb 2009 - Minor code cleanup
02 Feb 2009 - Added a toolbar, each whyteboard tab has its own undo/redo history
31 Jan 2009 - Closing the program removes temporary PNG files from PDF convert
