#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2009, 2010 by Steven Sproat
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

from __future__ import with_statement

import os
import sys
import webbrowser
#import poppler
import time
import zipfile
import wx
import shutil

try:
    import cPickle as pickle
except ImportError:
    import pickle

from lib.pubsub import pub

from dialogs import FindIM
from functions import (get_home_dir, load_image, convert_quality, make_filename,
                       get_wx_image_type, version_is_greater)

import meta
import tools

_ = wx.GetTranslation

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
        self.save_time = time.time()
        self.colour = wx.BLACK
        self.background = u"White"
        self.transparent = True  # overwrites background
        self.thickness = 1
        self.font = None  # default font for text input
        self.tool = 1  # Current tool ID that is being drawn with
        self.items = tools.items  # shortcut
        self.update_version = True
        self.saved_version = u""
        self.backup_ext = u".blah5bl8ah123bla6h"  # backup file extension
        self.im_location = None  # location of ImageMagick on windows
        self.path = os.path.split(os.path.abspath(sys.argv[0]))
        self.library = PDFCache(u"library.known")
        self.config = config
        self.pdf = False

        tools.HANDLE_SIZE = self.config['handle_size']
        pub.sendMessage('canvas.set_border', border_size=self.config['canvas_border'])
        if 'default_font' in self.config:
            self.font = wx.FFont(1, 1)
            self.font.SetNativeFontInfoFromString(self.config['default_font'])



    def save_file(self):
        """
        Saves the file by wrapping a pickled dictionary into a .data file and
        added any images into a zip archive along with the .data file.
        """
        if not self.filename:
            return

        version = meta.version
        if not self.update_version:
            version = self.saved_version

        self.is_zipped = True
        self.saved = True
        self.save_time = time.time()
        self.save_last_path(self.filename)
        self.gui.show_progress_dialog(_("Saving..."))

        canvases = self.gui.get_canvases()
        save = Save(self, canvases, self.gui.get_tab_names())
        save.save_items()

        data = save.create_save_list(self.gui.current_tab, version)
        self.write_save_file(data)

        self.zip = zipfile.ZipFile(self.filename, "r")
        save.restore_items(canvases)
        self.zip.close()

        self.gui.dialog.Destroy()
        self.gui.SetTitle(u"%s - %s" % (os.path.basename(self.filename), self.gui.title))


    def write_save_file(self, data):
        """
        An existing .wtbd zip must be re-created by copying all files except
        the pickled file, otherwise it gets added twice
        """
        tmp_file = os.path.join(os.path.dirname(self.filename), u'whyteboard_temp_new.wtbd')
        _zip = zipfile.ZipFile(tmp_file, 'w')
        self.save_bitmap_data(_zip)

        with open("save.data", 'wb') as f:
            try:
                pickle.dump(data, f)
            except pickle.PickleError:
                wx.MessageBox(_("Error saving file data"), u"Whyteboard")
                self.saved = False
                self.filename = None

        _zip.write("save.data")
        _zip.close()
        os.remove("save.data")

        if os.path.exists(self.filename):
            os.remove(self.filename)
        shutil.move(tmp_file, self.filename)



    def save_bitmap_data(self, _zip):
        """
        Will save all Image tools to disk as temporary files, and then removes
        them. This function is length because it will not save two idential
        images twice.
        """
        data = {}  # list of bitmap data, check if image has been pasted
        to_remove = []
        for x in range(self.gui.tab_count):
            canvas = self.gui.tabs.GetPage(x)
            for shape in canvas.shapes:
                if isinstance(shape, tools.Image):
                    img = shape.image.ConvertToImage()
                    img_data = img.GetData()

                    for k, v in data.items():
                        if v == img_data:
                            if not shape.filename:
                                shape.filename = k
                            break

                    #  the above iteration didn't find any common pastes
                    if not shape.filename:
                        tmp_name = make_filename() + u".png"
                        img.SaveFile(tmp_name, wx.BITMAP_TYPE_PNG)
                        img = wx.Image(tmp_name)

                        name = make_filename() + u".jpg"
                        img.SaveFile(name, wx.BITMAP_TYPE_JPEG)
                        shape.filename = name
                        data[shape.filename] = img_data
                        _zip.write(name, os.path.join(u"data", name))
                        to_remove.append(name)
                        to_remove.append(tmp_name)

                    else:
                        name = shape.filename

                        if not name in to_remove:
                            data[name] = img_data
                            img.SaveFile(name, get_wx_image_type(name))
                            _zip.write(name, os.path.join("data", name))
                            to_remove.append(name)

        [os.remove(x) for x in to_remove]



    def load_file(self, filename=None):
        """
        Loads in a file, passes it to convert if it is a convertable file,
        then either loads an image or unpickles a whyteboard file
        """
        if filename is None:
            filename = self.temp_file

        _file, _type = os.path.splitext(filename)  # convert to lowercase to
        _type = _type.replace(u".", u"").lower()  # save typing filename[1:] :)

        if _type in meta.types[:3]:
            self.convert()

        elif _type in meta.types:
            load_image(self.temp_file, self.gui.canvas, tools.Image)
            self.gui.canvas.redraw_all()
        else:
            wx.MessageBox(_("Whyteboard doesn't support the filetype") + u" .%s" % _type,
                          u"Whyteboard")


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

        self.is_zipped = True
        data = None
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
        sys.modules['tools'] = tools  # monkey patch for new src layout (0.4)

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
            wx.MessageBox(_('"%s" has corrupt data.\nThis file cannot be loaded.') % os.path.basename(filename),
                            u"Whyteboard")
            return
        except ImportError:  # older windows/linux incompatible type

            if not pickle_data:
                f.close()
                f = open(filename, 'r')

            try:
                temp = method(f)
            except (pickle.UnpicklingError, AttributeError, ImportError, ValueError, TypeError, EOFError):
                wx.MessageBox(_('"%s" has corrupt data.\nThis file cannot be loaded.') % os.path.basename(filename),
                              u"Whyteboard")
                return
            finally:
                if not pickle_data:
                    f.close()
        finally:
            if not pickle_data:
                f.close()

        del sys.modules['tools']
        self.recreate_save(filename, temp)


    def recreate_save(self, filename, temp):
        """
        Recreates the saved .wtbd file's state
        """
        self.filename = filename
        self.gui.show_progress_dialog(_("Loading..."))
        self.gui.remove_all_sheets()

        # change program settings and update the Preview window
        self.colour = temp[0][0]
        self.thickness = temp[0][1]
        self.tool = temp[0][2]
        self.gui.control.change_tool(_id=self.tool)  # toggle button
        self.gui.control.colour.SetColour(self.colour)
        self.gui.control.thickness.SetSelection(self.thickness - 1)

        # re-create tabs and its saved drawings
        for x in temp[1]:
            self.gui.on_new_tab(name=temp[3][x])
            self.gui.canvas.resize(temp[4][x])

            try:
                media = temp[5][x]
                for m in media:
                    m.canvas = self.gui.canvas
                    m.load()
                    self.gui.canvas.medias.append(m)
            except KeyError:
                break

            for shape in temp[1][x]:
                try:
                    shape.canvas = self.gui.canvas  # restore canvas
                    shape.load()  # restore unpickleable settings
                    self.gui.canvas.add_shape(shape)
                except Exception:
                    break
            self.gui.canvas.redraw_all(True)

        # close progress bar, handle older file versions gracefully
        wx.PostEvent(self.gui, self.gui.LoadEvent())
        self.saved = True
        self.saved_version = temp[0][4]
        pub.sendMessage('canvas.change_tool')
        self.gui.tabs.SetSelection(temp[0][3])
        self.gui.on_change_tab()
        self.gui.SetTitle(u"%s - %s" % (os.path.basename(filename), self.gui.title))

        try:
            if temp[0][5]:
                font = wx.FFont(1, 1)
                font.SetNativeFontInfoFromString(temp[0][5])
                self.font = font
        except IndexError:
            pass

        #  Don't save .wtbd file of future versions as current, older version
        if version_is_greater(self.saved_version, meta.version):
            self.update_version = False


    def save_last_path(self, path):
        self.config['last_opened_dir'] = os.path.dirname(path)
        self.config.write()


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
        #if _file is None:
        #    _file = self.temp_file
        #path = '/' + os.path.abspath(_file).replace('\\', '/')
        #self.document = poppler.document_new_from_file("file://" + path, None)
        #self.n_pages = self.document.get_n_pages()
        #self.gui.canvas.current_page = self.document.get_page(0)
        #self.gui.canvas.resize_if_large_image(self.gui.canvas.current_page.get_size())
        #self.pdf = True
        if not self.im_location:
            self.prompt_for_im()

        if not self.im_location:  # above will have changed this if IM exists
            return

        if _file is None:
            _file = self.temp_file

        quality = self.config['convert_quality']
        cached = self.library.lookup(_file, quality)
        if cached:
            self.display_converted(_file, cached)
        else:
            path = get_home_dir(u"wtbd-tmp")  # directory to store the images
            tmp_file = make_filename()
            before = os.walk(path).next()[2]  # file count before convert
            full_path = path + tmp_file + u".png"

            cmd = convert_quality(quality, self.im_location, _file, full_path)
            self.gui.convert_dialog(cmd)  # show progress bar, kick off convert

            if self.gui.convert_cancelled:
                return
            after = os.walk(path).next()[2]
            count = len(after) - len(before)
            images = []
            ignore = False

            if not count:
                wx.MessageBox(_("Failed to convert file. Ensure GhostScript is installed\nhttp://pages.cs.wisc.edu/~ghost/"), _("Conversion Failed"))
                wx.BeginBusyCursor()
                webbrowser.open_new_tab(u"http://pages.cs.wisc.edu/~ghost/")
                wx.CallAfter(wx.EndBusyCursor)
                return

            if count == 1:
                images.append(path + tmp_file + u".png")
                ignore = True
            else:
                for x in range(count):
                    # store the temp file path for this file in the dictionary
                    images.append(u"%s%s-%i.png" % (path, tmp_file, x))

            self.display_converted(_file, images, ignore)
            self.library.write(_file, images, quality)

        # Just in case it's a file with many pages
        self.gui.show_progress_dialog(_("Loading..."))
        self.gui.on_done_load()


    def display_converted(self, _file, images, ignore_close=False):
        """
        Display converted items. _file: PDF/PS name. Images: list of files
        """
        if not ignore_close and self.gui.tab_count == 1 and not self.gui.canvas.shapes:
            self.gui.remove_all_sheets()

        for x in range(len(images)):
            name = u"%s - %s" % (os.path.basename(_file)[:15], x + 1)
            self.gui.on_new_tab(name=name)
            load_image(images[x], self.gui.canvas, tools.Image)

        self.gui.canvas.redraw_all()


    def export(self, filename):
        """
        Exports the current view as a file. Select the appropriate wx constant
        depending on the filetype. gif is buggered for some reason :-/
        """
        const = get_wx_image_type(filename)
        self.gui.canvas.deselect_shape()

        context = wx.MemoryDC(self.gui.canvas.buffer)
        memory = wx.MemoryDC()
        x, y = self.gui.canvas.buffer.GetSize()
        bitmap = wx.EmptyBitmap(x, y, -1)
        memory.SelectObject(bitmap)
        memory.Blit(0, 0, x, y, context, 0, 0)
        memory.SelectObject(wx.NullBitmap)
        bitmap.SaveFile(filename, const)  # write to disk


    def prompt_for_im(self):
        """
        Prompts a Windows user for ImageMagick's directory location on
        initialisation. Save location to config file.
        """
        if os.name == "posix":
            value = os.system(u"which convert")
            if value == 256:
                wx.MessageBox(_("ImageMagick was not found. You will be unable to load PDF and PS files until it is installed."),
                              u"Whyteboard")
            else:
                self.im_location = u"convert"
        elif os.name == "nt":
            if not 'imagemagick_path' in self.config:
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
        _file = os.path.join(path, u"convert.exe")
        if not os.path.exists(_file):
            wx.MessageBox(_('Folder "%s" does not contain convert.exe') % path, u"Whyteboard")
            return False

        self.im_location = _file
        return True


    def change_tool(self, canvas, new=None):
        """
        Changes the canvas' shape that is being drawn with, or creates a new
        instance of the currently selected shape
        """
        if not new:
            new = self.tool
        else:
            self.tool = new

        colour = self.colour
        thickness = self.thickness
        params = [canvas, colour, thickness]

        if not self.transparent:
            params.append(self.background)
        canvas.shape = self.items[new - 1](*params)  # create new Tool


#----------------------------------------------------------------------

class PDFCache(object):
    """
    Represents a cache of any converted PDF files
    """
    def __init__(self, filename):
        self.path = os.path.join(get_home_dir(), filename)

        if not os.path.exists(self.path):
            self.write_dict(dict())


    def lookup(self, _file, quality):
        """Check whether a file is inside our known file library"""
        files = self.entries()

        for x, key in files.items():
            if files[x]['file'] == _file and files[x]['quality'] == quality:
                return files[x]['images']
        return False


    def write(self, location, images, quality):
        """Adds a newly converted file to the library"""
        files = self.entries()
        files[len(files)] = {'file': location, 'images': images,
                             'quality': quality, 'date': time.asctime()}
        self.write_dict(files)


    def write_dict(self, files):
        with open(self.path, "w") as f:
            pickle.dump(files, f)


    def entries(self):
        with open(self.path) as f:
            return pickle.load(f)


#----------------------------------------------------------------------


class Save(object):
    """
    Stores the data required to save a file.
    """
    def __init__(self, util, canvases, names):
        self.util = util
        self.names = names
        self.medias = []
        self.canvas_sizes = []
        self.tree_ids = []
        self.items = {}

        for x, canvas in enumerate(canvases):
            for media in canvas.medias:
                media.save()

            self.items[x] = list(canvas.shapes)
            self.canvas_sizes.append(canvas.area)
            self.medias.append(canvas.medias)


    def save_items(self):
        """
        Remove any unpickleable items from the list of shapes
        """
        for x in self.items:
            for shape in self.items[x]:
                if isinstance(shape, tools.Note):
                    self.tree_ids.append(shape.tree_id)
                    shape.tree_id = None
                try:
                    shape.save()
                except Exception:
                    break


    def create_save_list(self, tab, version):
        """
        Creates the save list. This *really* needs to be revised, using ints
        as dictionary keys! ugh.
        """
        font = None
        if self.util.font:
            font = self.util.font.GetNativeFontInfoDesc()

        return { 0: [self.util.colour, self.util.thickness, self.util.tool, tab,
                      version, font],
                  1: self.items,
                  2: None, # was self.to_convert, but wasn't used.
                  3: self.names,
                  4: self.canvas_sizes,
                  5: self.medias }


    def restore_items(self, canvases):
        """
        Fixes a bug with Windows, where the save_items() fuction unlinks each
        shape's canvas'
        """
        count = 0
        for x in self.items:
            canvas = canvases[x]
            for shape in self.items[x]:
                shape.canvas = canvas
                if isinstance(shape, tools.Note):
                    shape.load(False)
                    shape.tree_id = self.tree_ids[count]
                    count += 1
                else:
                    shape.load()
            for m in canvas.medias:
                m.canvas = canvas
                m.load()