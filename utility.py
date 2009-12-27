# -*- coding: utf-8 -*-
#!/usr/bin/python

# Copyright (c) 2009 by Steven Sproat
#
# GNU General Public Licence (GPL)
#
# Whyteboard is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 3 of the License, or (at your option) any later
# version.
# Whyteboard is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
# You should have received a copy of the GNU General Public License along with
# Whyteboard; if not, write to the Free Software Foundation, Inc., 59 Temple
# Place, Suite 330, Boston, MA  02111-1307  USA

"""
This module contains a utility helper class to reduce the amount of code
inside gui.py - whyteboard-file saving/loading, pdf/ps loading/conversion and
loading a standard image.

The saved .wtbd file structure is:

  dictionary { 0: [colour, thickness, tool, tab, version, font], - app settings
               1: shapes { 0: [shape1, shape2, .. shapeN],
                           1: [shape1, shape2, .. shapeN],
                           ..
                           N: [shape1, shape2, .. shapeN]
                         }
               2: files  { 0: { 0: filename,       ----------- not used any more
                                1: temp-file-1.png,
                                2: temp-file-2.png,
                                ...
                              },
                           1: { 0: filename,
                                1: temp-file-1.png,
                                2: temp-file-2.png,
                                ...
                              },
                            ...
                         }
               3: names: [ 0: 'sheet 1'
                           1: 'sheet 2'
                           2: 'sheet 3'
                           ...
                         ]
               4: sizes  [ 0: (canvas_x, canvas_y),
                           1: (canvas_x, canvas_y),
                           .....
                         ]
             }

Image Tools have the assosicated image removed from their class upon saving,
but are restored with it upon loading the file.
"""


import os
import sys
import webbrowser
import urllib
import tarfile
import zipfile
import distutils.dir_util
import wx

try:
    import cPickle as pickle
except ImportError:
    import pickle

from dialogs import ProgressDialog, FindIM
from functions import (save_pasted_images, get_home_dir, load_image,
                       convert_quality, make_filename)

import tools
import whyteboard


cfg = """
bmp_select_transparent = boolean(default=False)
canvas_border = integer(min=10, max=35, default=15)
colour1 = list(min=3, max=3, default=list('280', '0', '0'))
colour2 = list(min=3, max=3, default=list('255', '255', '0'))
colour3 = list(min=3, max=3, default=list('0', '255', '0'))
colour4 = list(min=3, max=3, default=list('255', '0', '0'))
colour5 = list(min=3, max=3, default=list('0', '0', '255'))
colour6 = list(min=3, max=3, default=list('160', '32', '240'))
colour7 = list(min=3, max=3, default=list('0', '255', '255'))
colour8 = list(min=3, max=3, default=list('255', '165', '0'))
colour9 = list(min=3, max=3, default=list('211', '211', '211'))
convert_quality = option('highest', 'high', 'normal', default='normal')
default_font = string
default_width = integer(min=1, max=12000, default=640)
default_height = integer(min=1, max=12000, default=480)
imagemagick_path = string
handle_size = integer(min=3, max=15, default=6)
language = option('English', 'English (United Kingdom)', 'Russian', 'Hindi', 'Portugese', 'Japanese', 'French', 'Traditional Chinese', 'Dutch', 'German', 'Welsh', 'Spanish', 'Italian', 'Czech', 'galician', default='English')
print_title = boolean(default=True)
statusbar = boolean(default=True)
toolbar = boolean(default=True)
toolbox = option('icon', 'text', default='icon')
undo_sheets = integer(min=5, max=50, default=10)
"""

_ = wx.GetTranslation

languages = ( (_("English"), wx.LANGUAGE_ENGLISH),
              (_("English (United Kingdom)"), wx.LANGUAGE_ENGLISH_UK),
              (_("Japanese"), wx.LANGUAGE_JAPANESE),
              (_("Portugese"), wx.LANGUAGE_PORTUGUESE),
              (_("Dutch"), wx.LANGUAGE_DUTCH),
              (_("German"), wx.LANGUAGE_GERMAN),
              (_("Russian"), wx.LANGUAGE_RUSSIAN),
              (_("Arabic"), wx.LANGUAGE_ARABIC),
              (_("Hindi"), wx.LANGUAGE_HINDI),
              (_("Spanish"), wx.LANGUAGE_SPANISH),
              (_("French"), wx.LANGUAGE_FRENCH),
              (_("Welsh"), wx.LANGUAGE_WELSH),
              (_("Traditional Chinese"), wx.LANGUAGE_CHINESE_TRADITIONAL),
              (_("Czech"), wx.LANGUAGE_CZECH),
              (_("Italian"), wx.LANGUAGE_ITALIAN),
              (_("Galician"), wx.LANGUAGE_GALICIAN) )

#----------------------------------------------------------------------

class Utility(object):
    """
    The class defines some class variables which are set/accessed through the
    GUI - supported filetypes, names of the drawng tools, a save file's
    associated converted files (e.g. a PDF)

    Trying to achieve a data-driven system, focusing on "don't repeat yourself"
    """
    def __init__(self, gui, config):
        """
        Initialise "shared" variables, and set up a wxPython wildcard from the
        supported filetypes.
        """
        self.gui = gui
        self.filename = None   # ACTIVE .wtbd file
        self.temp_file = None  # selected file (.wtdb/png/pdf - doesn't matter)
        self.to_archive = []  # image files to add to the save archive
        self.is_zipped = False
        self.zip = None  # zip archive to read images from
        self.saved = True
        self.colour = "Black"
        self.background = "White"
        self.transparent = True  # overwrites background
        self.thickness = 1
        self.font = None  # default font for text input
        self.tool = 1  # Current tool ID that is being drawn with
        self.items = tools.items  # shortcut
        self.update_version = True
        self.saved_version = ""
        self.backup_ext = ".blah5bl8ah123bla6h"  # backup file extension
        self.im_location = None  # location of ImageMagick on windows
        self.path = os.path.split(os.path.abspath(sys.argv[0]))
        self.library = os.path.join(get_home_dir(), "library.known")
        self.config = config

        tools.HANDLE_SIZE = self.config['handle_size']
        whyteboard.CANVAS_BORDER = self.config['canvas_border']
        if self.config.has_key('default_font'):
            self.font = wx.FFont(0, 0)
            self.font.SetNativeFontInfoFromString(self.config['default_font'])

        # Make wxPython wildcard filter. Add a new item - new type supported!
        # kinda (!) confusing code
        self.types = ["ps", "pdf", "svg", "jpeg", "jpg", "png", "tiff",
                       "bmp", "pcx", "JPEG", "JPG", "PNG", "TIFF", "BMP", "PCX"]
        images = ', '.join('*.' + i for i in self.types[2:])

        label = [_("All supported files"), _("All files")+" (*.*)",
                _("Whyteboard files")+" (*.wtbd)", _("Image Files")+" ("+images+")",
                "PDF/PS/SVG"]

        res1 = ';'.join('*.' + i for i in self.types[2:])
        res2 = ';'.join('*.' + i for i in self.types[0:2])

        wc_types = ["*.wtbd;" + res1 + res2, "*.*", "*.wtbd", res1, res2]

        wc_list = [x + "|" + y for x, y in zip(label, wc_types)]
        self.wildcard = '|'.join(wc_list)



    def save_file(self):
        """
        Saves the file if there is any drawn data to save. Any loaded Image
        objects must be removed - they will be converted to an Image loading
        a saved file.

        An existing .wtbd zip must be re-created by copying all files except
        the pickled file, otherwise it gets added twice
        """
        if self.filename:
            self.gui.dialog = ProgressDialog(self.gui, _("Saving..."), 30)
            self.gui.dialog.Show()
            mode = 'w'  # to open zip file

            if os.path.exists(self.filename):  # need to remove save.data
                do = True
                try:
                    _zip = zipfile.ZipFile(self.filename, "r")
                except zipfile.BadZipfile:  # old save format
                    do = False

                if do:
                    zout = zipfile.ZipFile('whyteboard_temp_new.wtbd', 'w')
                    for item in _zip.infolist():
                        if item.filename != 'save.data':
                            zout.writestr(item, _zip.read(item.filename))
                    zout.close()
                    _zip.close()

                    os.remove(self.filename)
                    os.rename('whyteboard_temp_new.wtbd', self.filename)

                    if os.stat(self.filename).st_size:  # not a 0-byte file
                        mode = 'a'
                else:
                    for x in range(0, self.gui.tab_count):
                        board = self.gui.tabs.GetPage(x)
                        for shape in board.shapes:
                            if isinstance(shape, tools.Image):
                                if shape.path not in self.to_archive:
                                    self.to_archive.append(shape.path)                                
                                

            _zip = zipfile.ZipFile(self.filename, mode)

            for x in self.to_archive:
                f = open(x)
                _zip.write(x, os.path.join("data", os.path.basename(x)))
                f.close()

            temp = {}
            names, medias, canvas_sizes = [], [], []
            tree_ids = []  # every note's tree ID to restore to

            # load in every shape from every tab
            for x in range(0, self.gui.tab_count):
                board = self.gui.tabs.GetPage(x)

                for m in board.medias:
                    m.save()
                save_pasted_images(board.shapes)
                temp[x] = list(board.shapes)
                canvas_sizes.append(board.area)
                medias.append(board.medias)
                names.append(self.gui.tabs.GetPageText(x))

            if temp:
                for x in temp:
                    for shape in temp[x]:
                        if isinstance(shape, tools.Note):
                            tree_ids.append(shape.tree_id)
                            shape.tree_id = None
                        shape.save()  # need to unlink unpickleable items;

                version = self.gui.version
                if not self.update_version:
                    version = self.saved_version

                # Now the unpickleable objects are gone, build the save file
                tab = self.gui.tabs.GetSelection()
                font = None
                if self.font:
                    font = self.font.GetNativeFontInfoDesc()
                _file = { 0: [self.colour, self.thickness, self.tool, tab,
                              version, font],
                          1: temp,
                          2: None,  # was self.to_convert, but wasn't used.
                          3: names,
                          4: canvas_sizes,
                          5: medias }

                f = open("save.data", 'wb')
                try:
                    pickle.dump(_file, f)
                    t = os.path.split(self.filename)[1] + ' - ' + self.gui.title

                    self.gui.SetTitle(t)
                except pickle.PickleError:
                    wx.MessageBox(_("Error saving file data"))
                    self.saved = False
                    self.filename = None
                finally:
                    f.close()

                _zip.write("save.data")
                _zip.close()
                os.remove("save.data")
                self.to_archive = []

                self.zip = zipfile.ZipFile(self.filename, "r")

                # Fix bug in Windows where the current shapes get reset above
                count = 0
                for x in temp:
                    board = self.gui.tabs.GetPage(x)
                    for shape in temp[x]:
                        shape.board = board
                        if isinstance(shape, tools.Note):
                            shape.load(False)
                            shape.tree_id = tree_ids[count]
                            count += 1
                        else:
                            shape.load()
                    for m in board.medias:
                        m.board = board
                        m.load()

                self.zip.close()
            else:
                wx.MessageBox(_("Error saving file data - no data to save"))
                self.saved = False
                self.filename = None

            self.gui.dialog.Destroy()


    def load_file(self, filename=None):
        """
        Loads in a file, passes it to convert if it is a convertable file,
        then either loads an image or unpickles a whyteboard file
        """
        if filename is None:
            filename = self.temp_file

        _file, _type = os.path.splitext(filename)  # convert to lowercase to
        _type = _type.replace(".", "").lower()  # save typing filename[1:] :)

        if _type in self.types[:3]:
            self.convert()

        elif _type in self.types[3:]:
            load_image(self.temp_file, self.gui.board)
            self.gui.board.redraw_all()
        else:
            wx.MessageBox(_("Whyteboard doesn't support the filetype")+" .%s" % _type)


    def load_wtbd(self, filename):
        """
        Closes all tabs, loads in a Whyteboard save, which can be a zipped file
        or a single pickled file.
        """
        f = None
        try:
            f = zipfile.ZipFile(filename)
        except zipfile.BadZipfile:
            self.is_zipped = False
            self.load_wtbd_pickle(filename)  # old save format            
            return

        data = None
        self.is_zipped = True
        self.zip = f
        try:
            data = f.read("save.data")
        except KeyError:
            wx.MessageBox(_('"%s" is missing the file save.data')
                        % os.path.basename(filename))
            f.close()
            return

        self.load_wtbd_pickle(filename, data)
        self.zip.close()


    def load_wtbd_pickle(self, filename, pickle_data=None):
        """
        Loads in the old .wtbd format (just a pickled file). Takes in either
        a filename (path) or a Python file object (from the zip archive)
        Pretty messy code, to support old save files written in "w", not "wb"
        """
        temp = {}
        method = pickle.load
        if not pickle_data:
            f = open(filename, 'rb')
        else:
            f = pickle_data
            method = pickle.loads

        try:
            temp = method(f)
        except (pickle.UnpicklingError, AttributeError, ValueError, TypeError, EOFError):
            wx.MessageBox(_('"%s" has corrupt Whyteboard data. No action taken.')
                        % os.path.basename(filename))
            return
        except ImportError:  # older windows/linux incompatible type

            if not pickle_data:
                f.close()
                f = open(filename, 'r')

            try:
                temp = method(f)
            except (pickle.UnpicklingError, AttributeError, ValueError, TypeError, EOFError):
                wx.MessageBox(_('"%s" has corrupt Whyteboard data. No action taken.')
                            % os.path.basename(filename))
                return
            finally:
                if not pickle_data:
                    f.close()
        finally:
            if not pickle_data:
                f.close()

                
        self.recreate_save(filename, temp)


    def recreate_save(self, filename, temp):
        """
        Recreates the saved .wtbd file's state
        """
        self.filename = filename
        self.gui.dialog = ProgressDialog(self.gui, _("Loading..."), 30)
        self.gui.dialog.Show()
        self.remove_all_sheets()

        # change program settings and update the Preview window
        self.colour = temp[0][0]
        self.thickness = temp[0][1]
        self.tool = temp[0][2]
        self.gui.control.change_tool(_id = self.tool)  # toggle button
        self.gui.control.colour.SetColour(self.colour)
        self.gui.control.thickness.SetSelection(self.thickness - 1)
        self.gui.SetTitle(os.path.split(filename)[1] + ' - ' + self.gui.title)

        # re-create tabs and its saved drawings
        for x in temp[1]:
            name = None
            try:
                name = temp[3][x]
            except KeyError:
                pass

            self.gui.on_new_tab(name=name)

            try:
                self.gui.board.resize_canvas(temp[4][x])
            except KeyError:
                pass

            media = []
            try:
                media = temp[5][x]
                for m in media:
                    m.board = self.gui.board
                    m.load()
                    self.gui.board.medias.append(m)
            except KeyError:
                pass

            for shape in temp[1][x]:
                shape.board = self.gui.board  # restore board
                shape.load()  # restore unpickleable settings
                self.gui.board.add_shape(shape)
            self.gui.board.redraw_all(True)

        # close progress bar, handle older file versions gracefully
        wx.PostEvent(self.gui, self.gui.LoadEvent())
        self.saved = True
        self.gui.board.select_tool()

        try:
            self.gui.tabs.SetSelection(temp[0][3])
            self.gui.on_change_tab()
        except IndexError:
            pass

        try:
            version = temp[0][4]
        except IndexError:
            version = "0.33"
        self.saved_version = version
        font =  None

        try:
            if temp[0][5]:
                font = wx.FFont(0, 0)
                font.SetNativeFontInfoFromString(temp[0][5])
            self.font = font
        except IndexError:
            pass

        #  Don't save .wtbd file of future versions as current, older version
        num = [int(x) for x in version.split(".")]
        ver = [int(x) for x in self.gui.version.split(".")]
        if len(num) == 2:
            num.append(0)

        if num[1] > ver[1]:
            self.update_version = False
        elif num[1] == ver[1]:
            if num[2] > ver[2]:
                self.update_version = False


    def library_create(self):
        if not os.path.exists(self.library):
            f = open(self.library, "w")
            f.write("")
            pickle.dump({}, f)
            f.close()


    def library_lookup(self, _file, quality):
        """Check whether a file is inside our known file library"""
        self.library_create()
        f = open(self.library)
        files = pickle.load(f)
        f.close()
        for x, key in files.items():
            if files[x]['file'] == _file and files[x]['quality'] == quality:
                return files[x]['images']
        return False


    def library_write(self, location, images, quality):
        """Adds a newly converted file to the library"""
        self.library_create()
        f = open(self.library)
        files = pickle.load(f)
        f.close()
        files[len(files)] = {'file': location, 'images': images,
                             'quality': quality}

        f = open(self.library, "w")
        pickle.dump(files, f)
        f.close()


    def convert(self, _file=None):
        """
        If the filetype is PDF/PS, convert to a (temporary) series of images and
        loads them. Find out the directory length before/after the conversion to
        know how many 'pages' were converted - used then to create a new
        Whyteboard tabs for each page. The PDF's file location, convert quality
        and converted images are written into a "library" file, effectively
        caching the conversion.

        An attempt at randomising the temp. file name is made using alphanumeric
        characters to help minimise conflict.
        """
        if not self.im_location:
            self.prompt_for_im()

        if not self.im_location:  # above will have changed this if IM exists
            return

        if _file is None:
            _file = self.temp_file

        quality = self.config['convert_quality']
        cached = self.library_lookup(_file, quality)
        if cached:
            self.display_converted(_file, cached)
        else:
            path = get_home_dir("wtbd-tmp")  # directory to store the images
            tmp_file = make_filename()
            before = os.walk(path).next()[2]  # file count before convert
            full_path = path + tmp_file + ".png"

            cmd = convert_quality(quality, self.im_location, _file, full_path)
            self.gui.convert_dialog(cmd)  # show progress bar, kick off convert

            if self.gui.convert_cancelled:
                return
            after = os.walk(path).next()[2]
            count = len(after) - len(before)

            if count == 1:
                temp_path = path + tmp_file + ".png"
                load_image(temp_path, self.gui.board)
            else:
                if not count:
                    wx.MessageBox(_("Failed to convert file. Ensure GhostScript is installed; http://pages.cs.wisc.edu/~ghost/"), _("Conversion Failed"))
                    wx.BeginBusyCursor()
                    webbrowser.open_new_tab("http://pages.cs.wisc.edu/~ghost/")
                    wx.CallAfter(wx.EndBusyCursor)
                    return
                images = []
                for x in range(0, count):
                    # store the temp file path for this file in the dictionary
                    temp_file = path + tmp_file + "-%s" % x + ".png"
                    images.append(temp_file)

                self.display_converted(_file, images)
                self.gui.util.library_write(_file, images, quality)

        # Just in case it's a file with many pages
        self.gui.dialog = ProgressDialog(self.gui, _("Loading..."), 30)
        self.gui.dialog.Show()
        self.gui.on_done_load()


    def display_converted(self, _file, images):
        """
        Display converted items. _file: PDF/PS name. Images: list of files
        """
        if self.gui.tab_count == 1 and not self.gui.board.shapes:
            self.remove_all_sheets()

        for x in range(0, len(images)):
            name = os.path.split(_file)[1][:15] + " - %s" % (x + 1)
            self.gui.on_new_tab(name=name)
            load_image(images[x], self.gui.board)

        self.gui.board.redraw_all()


    def export(self, filename):
        """
        Exports the current view as a file. Select the appropriate wx constant
        depending on the filetype. gif is buggered for some reason :-/
        """
        _name = os.path.splitext(filename)[1].replace(".", "").lower()

        types = {"png": wx.BITMAP_TYPE_PNG, "jpg": wx.BITMAP_TYPE_JPEG, "jpeg":
                 wx.BITMAP_TYPE_JPEG, "bmp": wx.BITMAP_TYPE_BMP, "tiff":
                 wx.BITMAP_TYPE_TIF, "pcx": wx.BITMAP_TYPE_PCX }

        const = types[_name]  # grab the right image type from dict. above
        self.gui.board.deselect()
        self.gui.board.redraw_all()

        context = wx.MemoryDC(self.gui.board.buffer)
        memory = wx.MemoryDC()
        x, y = self.gui.board.buffer.GetSize()
        bitmap = wx.EmptyBitmap(x, y, -1)
        memory.SelectObject(bitmap)
        memory.Blit(0, 0, x, y, context, 0, 0)
        memory.SelectObject(wx.NullBitmap)
        bitmap.SaveFile(filename, const)  # write to disk


    def remove_all_sheets(self):
        """  Remove all tabs, thumbnails and tree note items """
        self.gui.board.shapes = []
        self.gui.board.redraw_all()
        self.gui.tabs.DeleteAllPages()
        self.gui.thumbs.remove_all()
        self.gui.notes.remove_all()
        self.gui.tab_count = 0
        self.gui.tab_total = 0


    def prompt_for_save(self, method, style=wx.YES_NO | wx.CANCEL, args=None):
        """
        Ask the user to save, quit or cancel (quitting) if they haven't saved.
        Can be called through "Update", "Open (.wtbd)", or "Exit". If updating,
        don't show a cancel button, and explicitly restart if the user cancels
        out of the "save file" dialog (
        Method(*args) specifies the action to perform if user selects yes or no
        """
        if not args:
            args = []

        if not self.saved:
            name = _("Untitled")
            if self.filename:
                name = os.path.basename(self.filename)
            msg = (_('"%s" has been modified.\nDo you want to save your changes?') % name)
            dialog = wx.MessageDialog(self.gui, msg, _("Save File?"), style |
                                      wx.ICON_EXCLAMATION)
            val = dialog.ShowModal()

            if val == wx.ID_YES:
                self.gui.on_save()
                if self.saved or method == os.execvp:
                    method(*args)  # force restart, otherwise 'cancel'
                                   # returns to application

            if val == wx.ID_NO:
                method(*args)
                if method == self.gui.Destroy:
                    sys.exit()
            if val == wx.ID_CANCEL:
                dialog.Close()
        else:
            method(*args)
            if method == self.gui.Destroy:
                sys.exit()


    def prompt_for_im(self):
        """
        Prompts a Windows user for ImageMagick's directory location on
        initialisation. Save location to config file.
        """
        if os.name == "posix":
            value = os.system("which convert")
            if value == 256:
                wx.MessageBox(_("ImageMagick was not found. You will be unable to load PDF and PS files until it is installed."))
            else:
                self.im_location = "convert"
        elif os.name == "nt":

            if not self.config.has_key('imagemagick_path'):
                dlg = FindIM(self, self.gui, self.check_im_path)
                dlg.ShowModal()
                if self.im_location:
                    self.config['imagemagick_path'] = os.path.dirname(self.im_location)
                    self.config.write()
            else:
                self.check_im_path(self.config['imagemagick_path'])


    def check_im_path(self, path):
        """
        Checks the ImageMagick path before getting/setting the string to ensure
        convert.exe exists
        """
        _file = os.path.join(path, "convert.exe")
        if not os.path.exists(_file):
            wx.MessageBox(path + " does not contain convert.exe")
            return False

        self.im_location = _file
        return True


    def download_help_files(self):
        """
        Downloads the help files to the user's directory and shows them
        """
        _file = os.path.join(self.path[0], "whyteboard-help.tar.gz")
        url = "http://whyteboard.googlecode.com/files/help-files.tar.gz"
        tmp = None
        try:
            tmp = urllib.urlretrieve(url, _file)
        except IOError:
            wx.MessageBox(_("Could not connect to server."), _("Error"))
            raise IOError

        if os.name == "posix":
            os.system("tar -xf "+ tmp[0])
        else:
            tar = tarfile.open(tmp[0])
            tar.extractall(self.path[0])
            tar.close()
        os.remove(tmp[0])


    def extract_tar(self, _file, version):
        """
        Extract a .tar.gz source file on Windows, without needing to use the
        'tar' command, and with no other downloads!
        """
        path = self.path[0]
        tar = tarfile.open(_file)
        tar.extractall(path)
        tar.close()
        # remove 2 folders that will be updated, may not exist
        src = os.path.join(path, "whyteboard-"+ version)

        widgs = os.path.join(path, "fakewidgets")
        helps = os.path.join(path, "helpfiles")
        if os.path.exists(widgs):
            distutils.dir_util.remove_tree(widgs)
        if os.path.exists(helps):
            distutils.dir_util.remove_tree(helps)

        # rename all relevant files - ignore any dirs
        for f in os.listdir(path):
            location = os.path.join(path, f)
            if not os.path.isdir(location):
                _type = os.path.splitext(f)

                if _type[1] in [".py", ".txt"]:
                    new_file = os.path.join(path, _type[0]) + self.backup_ext
                    os.rename(location, new_file)

        # move extracted file to current dir, remove tar, remove extracted dir
        distutils.dir_util.copy_tree(src, path)
        distutils.dir_util.remove_tree(src)


    def is_exe(self):
        """Determine if Whyteboard's being run from an exe"""
        try:
            x = sys.frozen
            return True
        except AttributeError:
            return False


    def get_path(self):
        """Fetch the correct resource"""
        if self.path[0] == "/usr/bin":
            return "/usr/lib/whyteboard"
        return self.path[0]


    def get_clipboard(self):
        """Checks the clipboard for any valid image or text data to paste"""
        bmp = wx.BitmapDataObject()
        wx.TheClipboard.Open()
        success = wx.TheClipboard.GetData(bmp)
        wx.TheClipboard.Close()
        if success:
            return bmp
        text = wx.TextDataObject()
        wx.TheClipboard.Open()
        success = wx.TheClipboard.GetData(text)
        wx.TheClipboard.Close()
        if success:
            return text
        return False


    def set_clipboard(self, rect):
        """Sets the clipboard with a bitmap image data of a selection"""
        if rect.x < 0:
            rect.SetX(0)
        if rect.y < 0:
            rect.SetY(0)
        temp = self.gui.board.buffer.GetSubBitmap(rect)
        bmp = wx.BitmapDataObject()
        bmp.SetBitmap(temp)

        wx.TheClipboard.Open()
        wx.TheClipboard.SetData(bmp)
        wx.TheClipboard.Close()



#----------------------------------------------------------------------

class WhyteboardDropTarget(wx.PyDropTarget):
    """Implements drop target functionality to receive files and text"""
    def __init__(self, gui):
        wx.PyDropTarget.__init__(self)
        self.gui = gui
        self.do = wx.DataObjectComposite()
        self.filedo = wx.FileDataObject()
        self.textdo = wx.TextDataObject()
        self.bmpdo = wx.BitmapDataObject()
        self.do.Add(self.filedo)
        self.do.Add(self.bmpdo)
        self.do.Add(self.textdo)
        self.SetDataObject(self.do)


    def OnData(self, x, y, d):
        """
        Handles drag/dropping files/text or a bitmap
        """
        if self.GetData():
            df = self.do.GetReceivedFormat().GetType()

            if df == wx.DF_UNICODETEXT or df == wx.DF_TEXT:

                shape = tools.Text(self.gui.board, self.gui.util.colour, 1)
                shape.text = self.textdo.GetText()

                self.gui.board.shape = shape
                shape.left_down(x, y)
                shape.left_up(x, y)
                self.gui.board.text = None
                self.gui.board.select_tool()
                self.gui.board.redraw_all(True)

            elif df == wx.DF_FILENAME:
                for x, name in enumerate(self.filedo.GetFilenames()):
                    if x or self.gui.board.shapes:
                        self.gui.on_new_tab()

                    if name.endswith(".wtbd"):
                        self.gui.util.prompt_for_save(self.gui.do_open, args=[name])
                    else:
                        self.gui.do_open(name)

            elif df == wx.DF_BITMAP:
                bmp = self.bmpdo.GetBitmap()
                shape = tools.Image(self.gui.board, bmp, None)
                shape.left_down(x, y)
                wx.Yield()
                self.gui.board.redraw_all(True)

        return d

#----------------------------------------------------------------------
