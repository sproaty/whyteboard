Whyteboard 0.42 - A simple image, PDF and postscript file annotator
https://launchpad.net/whyteboard -- http://code.google.com/p/whyteboard/
xx xx 2011

---- TO RUN WHYTEBOARD ----

*** Windows users

If you have installed the Windows .exe file, simply run Whyteboard from the
start menu. If you have the stand-alone exe, please run whyteboard.exe


*** Package-based Linux distributions 

Whyteboard comes available in .deb and .rpm package formats.
There are also OpenSuse and Gentoo builds available on the web, though they
may not be up to date (and are not maintained by the program developer).


*** From source (Windows/Linux/Mac)

Whyteboard has a few requirements to be run from source:

* Python - http://www.python.org/download
  Version 2.6 or 2.7  (2.7 is recommended)
  Whyteboard will not work with Python 3, 2.4 or 2.5 (wxPython is unavilable)


* wxPython 2.8 - http://www.wxpython.org/download.php#stable
  2.8.9.0 at minimum, 2.8.12.0 is recommended
  Make sure you download the unicode build, not the ansii.


* ImageMagick - http://www.imagemagick.net

* Windows users may also need GhostScript - http://pages.cs.wisc.edu/~ghost/


***

To launch the application, run the whyteboard.py file. If nothing happens,
try executing the following command from a terminal/command prompt:

python whyteboard.py --debug

This will enable debug mode, which will print out reports of what the program
is doing. This can help to track down bugs and errors.
It would be appreciated if you could paste the log to me at <sproaty@gmail.com>
or, report a bug through Launchpad at https://bugs.launchpad.net/whyteboard


---- FEEDBACK AND BUG REPORTING ----

If a bug occurs while the program is running, the built-in error reporter will
appear. You can use this dialog to send me an e-mail directly, containing
diagnostic information of your system (e.g. operating system, language, display
resolution), and a log of the error. 
This is the best method to report errors. Please fill in as much detail about 
what you were doing so that I can reproduce the error.
Giving your e-mail address will allow me to get back in touch with you to follow
up on the bug, and to confirm a fix.

***

Feedback can be sent from the program, click on "Help", then "Send Feedback",
which will bring up a dialog. From here you can e-mail me directly.
If you give your e-mail address then I can reply to discuss any issues/feature
suggestions.


---- KNOWN BUGS ----

If you are getting an error starting the program on Windows,
"Application failed to start because the application configuration is incorrect.
Reinstalling the application may fix the problem."

...then download the C++ Runtime. 4.0 MB:
http://www.microsoft.com/downloads/details.aspx?familyid=A5C84275-3B97-4AB7-A40D-3802B2AF5FC2

- or use this 64 bit version if you have Windows 64. 4.7MB
http://www.microsoft.com/downloads/details.aspx?familyid=BA9257CA-337F-4B40-8C14-157CFDFFEE4E


* Printing quality may be bad
* Exporting PDFs creates an image of your sheets and then places that image into
  the PDF. Be careful with overwriting.
* Media Tool may take several file loads to actually load the file correctly.
* Media Tool may not resize the video/control panel properly
* Dragging and dropping text from Firefox will 'hang' the program until the text
  dialog is closed
* Copying/pasting text with tab characters do not display the tabs on Windows

See up to date reports at https://bugs.launchpad.net/whyteboard
An attempt is made to identify and fix as many bugs as possible before a new
release.


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
InnoSetup, windows installer creator - http://www.jrsoftware.org/isinfo.php
UPX, .exe compressor - http://upx.sourceforge.net/