Whyteboard 0.37.1 - a simple image, PDF and postscript file annotator
https://launchpad.net/whyteboard -- http://code.google.com/p/whyteboard/
Wed 06 May 2009 17:42:59 BST 

---- TO RUN WHYTEBOARD ----

If you have installed the Windows .exe file, simply run Whyteboard from the
start menu.

First, you need Python, wxPython, and (optionally) ImageMagick/GhostScript:

http://python.org/download/
http://www.wxpython.org/download.php
http://www.imagemagick.net
http://pages.cs.wisc.edu/~ghost/ - Windows users may need this for ImageMagick

***

Run whyteboard.py or gui.py to launch the application, no installation needed!

If nothing happens, try launching one of the scripts from the console:
$ python whyteboard.py
see what error occurred and let me know at, <sproaty -at- gmail -dot- com>

---- KNOWN BUGS ----

Currently none.


---- VERSION HISTORY ----

1x May 2009 - * Select tool: can select shapes to alter their colour/thickness,
                edit text and notes, move shapes and resize them. Selected 
                shapes are drawn with an outline "handle" at their corners
                -- Images and text can also be repositioned
                -- can double click text/notes to edit them
              * Improved undo/redo to support editing, moving and resizing
                of objects as described above. Text edits can also be undone
              * Colour button in text input dialog, instead of always drawing 
                with the user's selected colour
              * Text input dialogs remembers the last font used, and is 
                selected by default when creating more text
                -- the chosen font is also saved into the .wtbd save file
              * The Pen tool will now draw in response to a single mouse click;
                before the mouse needed to be moved to draw
              * Misc existing code improvements and performance increases
              * More/better unit testing to help with adding new features, 
                tracking down potential bugs and increased code confidence
              * Help files updates to reflect new changes and clarify any
                issues before

06 May 2009 - * 'Check for Updates'- Whyteboard can update itself
                -- will download an .exe / .tar.gz as appropriate
                -- on Windows, running via source will download the tar, which
                    is cool because Windows doesn't support .tar.gz by default
                -- shows progress of downloaded file
                -- program restarts with new version loaded, also re-loads the
                    current .wtbd file
                  
              * HTML Help system/manual built into the application
                -- well, via a folder containing HTML help files
                -- if they are not present, they can be downloaded (optional)
              
              * 'About Box' standardised
              * Exit dialog more like other apps: "sure you want to save?"
                (yes/no/cancel), instead of "sure you want to quit?" (yes/no)
                -- also asks when opening a new .wtbd file with an unsaved .wtbd
                   file open
                -- and after downloading the update, before the program restarts
                   it will prompt for save: yes/no

20 Apr 2009 - * Memory use improved from undo closed sheet improved
              * Bugfix: paste / paste as new sheet - not updating the thumbnail
              * Backwards/forwards compability: from this version onwards,
                Whyteboard will not change the version inside saved .wtbd files
                that are created in a newer version of Whyteboard.
                i.e. version 0.36.7 won't change the version inside a file saved
                in 0.36.9 (before, it would). It will update the version from a
                file saved in < 0.36.7 to 0.36.7

13 Apr 2009 - * Undo closed tabs, last 10 tabs are stored
              * Bugfix: closing a sheet would make all other sheet display the
                closed sheets' image until drawn on
              * Bugfix: Saving a document which has Notes would result in
                duplicate notes being visible in the Notes tree view.
              * Windows exe filesize reduced: 14.2MB -> 4.78MB (!)

08 Apr 2009 - * Bugfix with drawing "outlined" shapes having inverted colours
                lines when drawing over other colours.
              * Bugfix with opening new window with Windows EXE
              * Bugfix: thumbnails not being drawn white initially on Windows
              * Added icon into the EXE

08 Apr 2009 - * Paste image from clipboard into a new sheet
              * Toggle full screen view
              * Tool panel is now collapsible to give (a little bit) more room
                in full screen mode.
              * Bugfix with eraser cursor in Windows
              * Bugfix with Windows not drawing new lines from text input
              * Misc. code improvements
              * Performance increase from drawing shape 'fix' added in 0.36.2

07 Apr 2009 - * Tooltips for each item on the toolbox
              * "New Window" menu item to launch a new Whyteboard instance.
              * Important Windows bugfix: .wtbd drawings being "overwritten" on
                load.
              * Important Windows bugfix: .wtbd drawings not restoring the saved
                selected tool.

05 Apr 2009 - * Paste image support. Pasted images will be saved to a temporary
                directory; duplicated pasted images will be saved in one file.
              * Copy selection as bitmap with new tool: RectSelect
              * Popup menu on the sheet bar. Added "rename" option for sheets,
                which are saved into a save file. Can also close a sheet, open
                a new sheet or export the selected one from the menu
              * Cleaner code for managing UI button enabling/disabling
              * Bugfix: Editing a note and pressing backspace updates the note
                properly
              * Bugfix: drawing outlined shapes weirdness outside the default
                scrollbar region (introduced in 0.35.8)
              * Bugfix: exporting image saves whole sheet, not just the visible
                area
              * Bugfix: Adding a line sometimes wasn't being actually added


02 Apr 2009 - * Fixed an issue with 'flickering' on Windows
              * Bugfix: "edit" right-click popup menu on the Note root node.
              * Preview for the eyedrop (just shows current colour)

30 Mar 2009 - * Windows UI improvement: change the thickness by scrolling the
                mousewheel on the drop-down box, no need to click it. (this is
                the default behaviour under GNOME)
              * Next/Previous sheet in the "Sheets" menu (which previously was
                "Image") - Ctrl+Tab / Ctrl-Shift+Tab shortcut keys
              * Side panel is now "collapsible" instead of a "toggle" menu item
              * Menus renamed, organised differently
              * Popup context menu on Notes tree: Edit (note), Switch To (sheet)
              * Text/notes appear on the canvas as you type
              * Eraser has a custom rectangle cursor, depending on its size
              * Escape button exits "History" dialog
              * Updated "About" menu
              * Bugfix: can no longer add a blank text/note object

25 Mar 2009 - * Misc. UI improvements: more labels/small grid of drawing colours
              * Added eraser tool
              * Flood fill temporarily removed, was too buggy
              * Tabs renamed to Sheets
              * Import -> PDF/PS/Image menu items (as well as through Open)

20 Mar 2009 - * Windows bugfix: outlined shapes not drawing properly
              * Windows bugfix: wxPython errors on closing the application with
                loaded images
              * Bugfix with the eyedropper not updating the colour label.

18 Mar 2009 - * Bugfix: toggling side panel on/off caused a lot of lag, should
              only be noticeable now with around 65+ tabs open.
              * Drag and drop support: drop any file that Whyteboard supports
              into the drawing panel to load it
              * Hold down the middle mouse button to scroll (was the right btn)

18 Mar 2009 - * Improved undo/redo functionality. It is now possible to undo and
              redo the clear all drawings/clear all tabs' drawings functionality
              * Redo is also fixed to more like other applications now: when you
              undo twice and then draw a new shape, your redo history is lost.
              Before you could redo the two undone shapes after the new drawing

              * The ImageMagick folder locator will only pop-up when trying to
              convert a file and when the directory is not set, not at
              application start-up

17 Mar 2009 - Added dragging around Whyteboard by holding down the right button
              and moving the mouse

15 Mar 2009 - Big bugfix on Windows: ImageMagick's convert program not being
              found. Whyteboard prompts for its installed location and remembers
              it. (will also notify Linux users if ImageMagick isn't installed)

11 Mar 2009 - Bugfix: thumbnails getting cut off with too many tabs
              Can load in a file from the commmand line when running Whyteboard

10 Mar 2009 - Bugfix: Can no longer cancel file load progress dialogs.
              Performance increase: loading large .wtbd files
              Notification of "updating thumbnails" after load/converting a file

09 Mar 2009 - Bugfix: thumbnails not updating on file load

08 Mar 2009 - * Side panel is now tabbed to select between thumbnails and a
              "tree" view of all Notes (new feature) for each tab.
              ..Notes are similar to how text is input, except a light yellow
              background is drawn around it to indicate it's a note. In the
              tree control, a note item can be double clicked upon to bring up
              the text input dialog to change a note's text.

              Bugfix: a thumbnail's text  labelnot being removed when the
              thumbnail was removed.

04 Mar 2009 - Bugfix under Windows: toggling thumbnails would cause an error.

22 Feb 2009 - Bugfix with drawing 'outlined' shapes. Began work on text 'notes'.
              F5 will refresh all thumbnails since they're not refreshed upon
              loading a save, PDF or PostScript file.

21 Feb 2009 - * Export current tab's view as an image.
              * Live thumbnails, get updated when the selected tab is drawn upon
              * Thumbnail panel toggleable on/off
              * Drawing Preview window now shows a preview of the actual shape
                instead of always showing a line.

21 Feb 2009 - Text input overhaul, before the text was rendered as a wxPython
              widget - now it's a drawing of a String, with a custom dialog
              for inputting the text and selecting a font. This new method fixes
              many problems with having the text as widget, such as the text
              being un-undoable and drawings not "overwriting" the text.
              * Long text updates the scrollbars, vertically or horizontally
              * Program maximises on startup.
              * History improvements: draw all shapes back in the correct order
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

