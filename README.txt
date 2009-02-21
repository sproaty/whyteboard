Whyteboard 0.33 - a simple image, PDF and postscript file annotator
https://launchpad.net/whyteboard -- http://code.google.com/p/whyteboard/
Sat 21 Feb 2009 08:39:25 GMT

---- TO RUN WHYTEBOARD ----

First, you need Python, wxPython, and (optionally) ImageMagick/GhostScript:

http://python.org/download/
http://www.wxpython.org/download.php
http://www.imagemagick.net
http://pages.cs.wisc.edu/~ghost/ - Windows users may need this for ImageMagick


Next, download the latest Whyteboard file from Launchpad or Google Code. The
source can be browsed at Launchpad, and is included in the download.

Run any of the .py to launch the program, to installation needed!

If nothing happens, try launching one of the scripts from the console:
 python whyteboard.py
see what error occured and let me know, <sproaty -at- gmail -dot- com>


---- KNOWN BUGS ----

Windows: when drawing an "outlined" shape (Rectangle/Ellipse/Circle/Line/Rounded
Rectangle), the outline will mess up and appear oddly if the outline is dragged
over itself. Currently looking into this, strangely it doesn't happen on Linux.

Windows: issues with ImageMagick conflicting with a built-in Windows application
named convert (also the name of the IM program used to convert PDFs). If you try
to convert a PDF and receive a message in the console such as this:

C:\wb>python whyteboard.py

Invalid Parameter - and

Then you are experiencing the error. The link below offers some insight:
http://savage.net.au/ImageMagick/html/install-convert.html

Also, I experienced ImageMagick giving a bunch of errors converting a PDF - it
turns out that GhostScript needs to be installed too (on Windows XP, SP3)


---- VERSION HISTORY ----

21 Feb 2009 - Text input overhaul, before the text was rendered as a wxPython
              widget - now it's a drawing of a String, with a custom dialog
              for inputting the text and selecting a font. This new method fixes
              many problems with having the text as widget, such as the text
              being un-undoable and drawings not "overwriting" the text.
              * Long text updates the scrollbars, vertically or horizontally
              * Program maximises on startup.
              * History improvements: draw all shapes back in order, not just pen
              * Save files store the version number; loading an older save file
              into a newer Whteboard version which has added save data will say
              the older save file's version
               ...only problem with that is that the previous version's savefile
               versions aren't known since only know they're being stored

20 Feb 2009 - Small fix of a silly bug introduced below on accident where a pen
              would not render in its selected colour/thickness.

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
