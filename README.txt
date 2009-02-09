Whyteboard 0.25 - simple image/PDF/postscript file annotator
https://launchpad.net/whyteboard -- http://code.google.com/p/whyteboard/
Mon 09 Feb 2009 01:30:02 GMT

*** TO INSTALL ***

First - you need Python, wxPython and ImageMagick.
See http://code.google.com/p/whyteboard/ for links

Next, download the files from either Launchpad's source code browser or a tarred
archive from Google Code.

Run either gui.py, tools.py, utility.py or whyteboard.py to launch the program

If nothing happens, try launching one of the scripts from the console to see
what error occured - let me know.


*** KNOWN BUGS ***

- Saving your drawings isn't working. (ironically, loading them does)
- No progress bar when convering a PDF or such - shouldn't take too long
- Closing the program doesn't remove temporary PNGs
- History viewer not working
- Undo/redo being slightly broken because you can add "blank" shapes that fills
   up the undo list
- Text input box will overwrite anything drawn "behind" it
- Hard to actually see the text boxes' locations without adding in borders
- Text input - 25 character limit, no multilines, font etc (yet)


*** VERSIONS ***

Ugh, I don't know, haven't really been keeping a log.

09 Feb 2009 - mammoth code refactored, performance increased ten-fold, some bug
              fixes

03 Feb 2009 - minor code cleanup
02 Feb 2009 - Added a toolbar, each whyteboard tab has its own undo/redo history
31 Jan 2009 - Closing the program removes temporary PNG files from PDF convert