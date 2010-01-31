Whyteboard 0.39.4 - A simple image, PDF and postscript file annotator
https://launchpad.net/whyteboard -- http://code.google.com/p/whyteboard/
xx xx February 2010

---- TO RUN WHYTEBOARD ----

If you have installed the Windows .exe file, simply run Whyteboard from the
start menu. If you have the stand-alone exe, please run whyteboard.exe

Otherwise, here are the requirements:

* Python - 2.5.4 or 2.6.4 (untested on other major versions; should work on 2.4)
* wxPython - latest version is -always- recommended (currently 2.8.10.1).
    ---- WXPYTHON 2.8.9.0 NEEDED AT MINIMUM
* ImageMagick, possibly GhostScript for Windows users (optional)

http://www.python.org/download/
http://www.wxpython.org/download.php
http://www.imagemagick.net
http://pages.cs.wisc.edu/~ghost/ - Windows users may need this for ImageMagick

***

Run whyteboard.py to launch the application, no installation needed!
If nothing happens, try launching one of the scripts from the console:

$ python whyteboard.py

see what error occurred and let me know at, <sproaty@gmail.com>, report a bug at
Launchpad at the link below.

You can also use the built-in error reporter to send me an e-mail directly,
containing relevant system information and a log of the error. This is the best
method to report errors. Please fill in as much detail about what you were doing
to produce the error.
Giving your e-mail address will allow me to get back in touch with you to follow
up on the bug, and to confirm a fix. Several people have done this, thanks.

**

Feedback can be sent from the program, click on "Help", then "Send Feedback",
which will bring up a dialog. Please enter an e-mail address so I can reply
about any issues/feature suggestions.


**

If you are getting an error on Windows,
"Application failed to start because the application configuration is incorrect.
Reinstalling the application may fix the problem."

...then download the C++ Runtime (4.0 MB) at:
http://www.microsoft.com/downloads/details.aspx?familyid=A5C84275-3B97-4AB7-A40D-3802B2AF5FC2

- 64 bit version if you have Windows 64, 4.7MB:
http://www.microsoft.com/downloads/details.aspx?familyid=BA9257CA-337F-4B40-8C14-157CFDFFEE4E



---- KNOWN BUGS ----

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
BeautifulSoup, Python HTML parser - http://www.crummy.com/software/BeautifulSoup/
ConfigObj, Python configuration files - http://www.voidspace.org.uk/python/configobj.html
Editra Control Library, extra wxPython widgets - http://editra.org/eclib
Pubsub, publish/subscribe API -- http://pubsub.sourceforge.net

Tango Icon Library - http://tango.freedesktop.org/Tango_Icon_Library
py2exe, helps compile python files to windows .exe - http://www.py2exe.org/
GUI2Exe, python compiler front-end -  http://code.google.com/p/gui2exe/
InnoSetup - windows installer creator - http://www.jrsoftware.org/isinfo.php
UPX, .exe compressor - http://upx.sourceforge.net/