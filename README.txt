Whyteboard 0.39.0 - A simple image, PDF and postscript file annotator
https://launchpad.net/whyteboard -- http://code.google.com/p/whyteboard/
Wed 28 Oct October 2009

---- TO RUN WHYTEBOARD ----

If you have installed the Windows .exe file, simply run Whyteboard from the
start menu.

Otherwise, here are the requirements:

* Python - 2.5.4 or 2.6.3 (untested on other major versions; should work on 2.4)
* wxPython - latest version is -always- recommended (currently 2.8.10.1)
* ImageMagick, possibly GhostScript for Windows users (optional)

http://python.org/download/
http://www.wxpython.org/download.php
http://www.imagemagick.net
http://pages.cs.wisc.edu/~ghost/ - Windows users may need this for ImageMagick

***

Run whyteboard.py or gui.py to launch the application, no installation needed!
If nothing happens, try launching one of the scripts from the console:

$ python whyteboard.py

see what error occurred and let me know at, <sproaty@gmail.com>, report a bug at 
Launchpad at the link below.

You can also use the built-in error reporter to send me an e-mail directly, 
containing relevant system information and a log of the error. This is the best
method to report errors.
 

If you are getting an error on Windows, 
"Application failed to start because the application configuration is incorrect. 
Reinstalling the application may fix the problem."

then download the C++ Runtime (4.0 MB) at:
http://www.microsoft.com/downloads/details.aspx?familyid=A5C84275-3B97-4AB7-A40D-3802B2AF5FC2
http://www.microsoft.com/downloads/details.aspx?familyid=BA9257CA-337F-4B40-8C14-157CFDFFEE4E (64 bit version if you have win64)


---- KNOWN BUGS ----

See up to date reports at https://bugs.launchpad.net/whyteboard
Identified and confirmed bugs are always fixed before a new release.