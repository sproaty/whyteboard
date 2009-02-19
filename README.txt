Whyteboard 0.32.5 - simple image/PDF/postscript file annotator
https://launchpad.net/whyteboard -- http://code.google.com/p/whyteboard/
Thu 19 Feb 2009 21:59:41 GMT


---- TO RUN ----

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


---- KNOWN BUGS ----

- Text input box will overwrite anything drawn "over" it
- Placing a Text onto the Whyteboard tab can't be undone (but will be saved)
- Some operations can't be undone
- Hard to actually see the text boxes' locations without adding in borders
- Text input - 25 character limit, no multilines, font etc (yet)


all will be fixed in time :)


---- VERSION HISTORY ----

19 Feb 2009 - Added GPL.txt + fixed a bug with multiple images loaded into one
              tab. Fixed 'sure you want to open this file?' message dialog so
              that it only appears if you're loading in a Whyteboard file, not
              a PDF or PNG, for instance. Fixed a bug on Windows involving
              rectangles/circles/ellipses, yet another persists.

14 Feb 2009 - Added line drawing tool.
              "Sure you want to quit?" dialog when user hasn't saved.
              Only allowing one .wtbd file to be loaded at once
              Last Selected tab is stored in the .wtdb file
              Undo/redo tool/menu bar items are disabled/enabled as appropriate

12 Feb 2009 - Fixed saving/loading text controls, scrollbars adjust to screen
              resolution on resize. Fixed undo/redo visual and clear/clear all.
              Change clear/clear all to 4 options:
                * remove all drawings from current tab, keeping images
                * from all from current tab
                * remove all drawings from all tabs, keeping images
                * clear all tabs

12 Feb 2009 - Scrolling works properly. Loading an image will expand the scroll
              bars to the image size if the image is too big. Improvements to
              the history replaying, rewrote most of the drawing code again.

11 Feb 2009 - Saving/loading working. Currently keeping temporary files from
              PDF/PS conversions to make loading a saved file faster (would
              need to convert any 'linked' PDF/PS files for every .wtdb load)
              Saving text works, program also saves its settings.

11 Feb 2009 - Fixed history replaying, added pause/ stop the replay. Fixed a bug
              with the converting progress where the bar increased in response
              to mouse movement - now it's increased by a timer.

10 Feb 2009 - Converting PDF/PS pops up a "converting" progress bar
10 Feb 2009 - More code "unification", cleaner code, deleting temporary files,
              loading multiple PDF/PS/SVG files
09 Feb 2009 - Code refactored, performance increased ten-fold, some bug fixes
03 Feb 2009 - Minor code cleanup
02 Feb 2009 - Added a toolbar, each whyteboard tab has its own undo/redo history
31 Jan 2009 - Closing the program removes temporary PNG files from PDF convert
