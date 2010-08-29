Whyteboard 0.41 - A simple image, PDF and postscript file annotator
https://launchpad.net/whyteboard -- http://code.google.com/p/whyteboard/
xxx xx August 2010

---- TO RUN WHYTEBOARD ----

If you have installed the Windows .exe file, simply run Whyteboard from the
start menu. If you have the stand-alone exe, please run whyteboard.exe

To run Whyteboard from source, here are the requirements:

* Python - 2.5, 2.6, 2.7 (untested on other major versions; should work on 2.4)
  Whyteboard does not work with Python 3

http://www.python.org/download

* wxPython - the latest version is -always- recommended (currently 2.8.11.0).
  You will want the unicode build.
  wxPython 2.8.9.0 needed at minimum

http://www.wxpython.org/download.php

* ImageMagick, possibly GhostScript for Windows users (optional)

http://www.imagemagick.net
http://pages.cs.wisc.edu/~ghost/ - Windows users may need this for ImageMagick

***

Run whyteboard.py to launch the application. If nothing happens, try executing
the following command from the console/terminals:

python whyteboard.py

A bunch of errors should be printed - let me know at, <sproaty@gmail.com>, or
report a bug through Launchpad at https://bugs.launchpad.net/whyteboard


If a bug occurs while the program is running, the built-in error reporter will
appear. Use this to send me an e-mail directly, which will contain relevant
system information and a log of the error. This is the best method to report
errors. Please fill in as much detail about what you were doing so that I can
reproduce the error.
Giving your e-mail address will allow me to get back in touch with you to follow
up on the bug, and to confirm a fix.

**

Feedback can be sent from the program, click on "Help", then "Send Feedback",
which will bring up a dialog. Please enter an e-mail address so I can reply
about any issues/feature suggestions.

**

If you are getting an error starting the program on Windows,
"Application failed to start because the application configuration is incorrect.
Reinstalling the application may fix the problem."

...then download the C++ Runtime. 4.0 MB:
http://www.microsoft.com/downloads/details.aspx?familyid=A5C84275-3B97-4AB7-A40D-3802B2AF5FC2

- or use this 64 bit version if you have Windows 64. 4.7MB
http://www.microsoft.com/downloads/details.aspx?familyid=BA9257CA-337F-4B40-8C14-157CFDFFEE4E


---- KNOWN BUGS ----

* Printing quality may be bad
* Exporting PDFs creates an image of your sheets and then places that image into
  the PDF. Be careful with overwriting.
* Media Tool may take several file loads to actually load the file correctly.
* Media Tool may not resize the video/control panel properly
* Dragging and dropping text from Firefox will 'hang' the program until the text
  dialog is closed
* Copying/pasting text with tab characters do not display the tabs on Windows

See up to date reports at https://bugs.launchpad.net/whyteboard
Identified and confirmed bugs are always fixed before a new release.


---- LIBRARIES / SOFTWARE USED ----

Python, core programmling language - http://www.python.org/
wxPython, GUI framework - http://www.wxpython.org
ImageMagick, image editing suite - http://www.imagemagick.net
ConfigObj, Python configuration files - http://www.voidspace.org.uk/python/configobj.html
Editra Control Library, extra wxPython widgets - http://editra.org/eclib
Pubsub, publish/subscribe API -- http://pubsub.sourceforge.net

Tango Icon Library - http://tango.freedesktop.org/Tango_Icon_Library
py2exe, helps compile python files to windows .exe - http://www.py2exe.org/
GUI2Exe, python compiler front-end -  http://code.google.com/p/gui2exe/
InnoSetup - windows installer creator - http://www.jrsoftware.org/isinfo.php
UPX, .exe compressor - http://upx.sourceforge.net/