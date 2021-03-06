#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2009-2011 by Steven Sproat
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
import logging
import shutil
import time
import zipfile
import wx

try:
    import cPickle as pickle
except ImportError:
    import pickle

from whyteboard.core import Config
from whyteboard.lib import pub
from whyteboard.misc import (meta, get_home_dir, load_image, convert_quality, make_filename,
                       get_wx_image_type, version_is_greater, open_url)

import whyteboard.tools as tools

_ = wx.GetTranslation
logger = logging.getLogger("whyteboard.utility")

#----------------------------------------------------------------------

class Utility(object):
    """
    The class defines some class variables which are set/accessed through the
    GUI - supported filetypes, names of the drawng tools, a save file's
    associated converted files (e.g. a PDF)

    Trying to achieve a data-driven system, focusing on "don't repeat yourself"
    """
    def __init__(self, gui):
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
        self.im_location = None  # location of ImageMagick on windows
        self.path = None
        self.library = PDFCache(u"library.known")
        pub.subscribe(self.set_colour, 'change_colour')
        pub.subscribe(self.set_background, 'change_background')

        if Config().default_font():
            self.font = wx.FFont(1, wx.FONTFAMILY_DEFAULT)
            self.font.SetNativeFontInfoFromString(Config().default_font())



    def save_file(self):
        """
        Saves the file by wrapping a pickled dictionary into a .data file and
        added any images into a zip archive along with the .data file.
        """
        if not self.filename:
            logger.debug("No filename set; cannot save")
            return

        version = meta.version
        if not self.update_version:
            version = self.saved_version

        self.is_zipped = True
        self.mark_saved()
        self.save_last_path(self.filename)
        self.gui.show_progress_dialog(_("Saving..."))

        canvases = self.gui.get_canvases()
        save = Save(self, canvases, self.gui.get_tab_names())

        if not self.write_save_file(save, version):
            save.restore_items(canvases)
            self.gui.dialog.Destroy()
            return

        self.zip = zipfile.ZipFile(self.filename, "r")
        save.restore_items(canvases)
        self.zip.close()

        self.gui.dialog.Destroy()
        self.gui.SetTitle(u"%s - %s" % (os.path.basename(self.filename), self.gui.title))


    def write_save_file(self, save, version):
        """
        An existing .wtbd zip must be re-created by copying all files except
        the pickled file, otherwise it gets added twice
        """
        path = os.path.join(os.path.dirname(self.filename), u'whyteboard_temp_new.wtbd')
        tmp_file = os.path.abspath(path)
        errored = False
        logger.debug("Creating temporary zip file [%s].", tmp_file)
        
        _zip = zipfile.ZipFile(tmp_file, 'w')
        self.save_bitmap_data(_zip)
        save.save_items()
        data = save.create_save_list(self.gui.current_tab, version)
        data_file = os.path.join(get_home_dir(), "save.data")
        logger.debug("Writing save data to [%s]", data_file)
        
        with open(data_file, 'wb') as f:
            try:
                pickle.dump(data, f)
            except pickle.PickleError:
                wx.MessageBox(_("Error saving file data"), u"Whyteboard")
                logger.exception("Error pickling file data")
                self.saved = False
                self.filename = None
                errored = True
        
        if not errored:
            logger.debug("Writing data file to zip and cleaning up")
            _zip.write(data_file, "save.data")
        _zip.close()
        os.remove(data_file)
        if errored:
            os.remove(tmp_file)
            return False
        
        logger.debug("Removing old file and renaming temporary file")
        if os.path.exists(self.filename):
            os.remove(self.filename)
        shutil.move(tmp_file, self.filename)


    def save_bitmap_data(self, _zip):
        """
        Will save all Image tools to disk as temporary files, and then removes
        them. This function is lengthy because it will not save two idential
        images twice.
        """
        logger.debug("Writing bitmap files to zip")
        data = {}  # list of bitmap data, check if image has been pasted
        to_remove = []
        for canvas in self.gui.get_canvases():
            for shape in canvas.shapes:
                if isinstance(shape, tools.Image):
                    img = shape.image.ConvertToImage()
                    img_data = img.GetData()

                    for key, value in data.items():
                        if value == img_data:
                            if not shape.filename:
                                shape.filename = key
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

        [os.remove(x) for x in to_remove]



    def load_file(self, filename=None):
        """
        Loads in a file, passes it to convert if it is a convertable file,
        then either loads an image or unpickles a whyteboard file
        """
        if filename is None:
            filename = self.temp_file
        logger.debug("Attempting to load file [%s]", filename)

        _file, _type = os.path.splitext(filename)  # convert to lowercase to
        _type = _type.replace(u".", u"").lower()  # save typing filename[1:] :)
        
        if _type in meta.types[:3]:
            self.convert()

        elif _type in meta.types:
            load_image(self.temp_file, self.gui.canvas, tools.Image)
            self.gui.canvas.redraw_all()
        else:
            logger.warning("Filetype [%s] is not supported", _type)
            wx.MessageBox(_("Whyteboard doesn't support the filetype") + u" .%s" % _type,
                          u"Whyteboard")


    def load_wtbd(self, filename):
        """
        Closes all tabs, loads in a Whyteboard save, which can be a zipped file
        or a single pickled file.
        """
        logger.debug("Loading .wtbd file")
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
            logger.exception("File save.data is missing")
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

        save_data = {}
        if not pickle_data:
            logger.warning("Loading in older .wtbd save format.")
            method = pickle.load
            f = open(filename, 'rb')
        else:
            method = pickle.loads
            f = pickle_data

        try:
            save_data = method(f)
        except (pickle.UnpicklingError, AttributeError, ValueError, TypeError, EOFError):
            logger.exception("Save file has corrupt data")
            wx.MessageBox(_('"%s" has corrupt data.\nThis file cannot be loaded.') % os.path.basename(filename),
                            u"Whyteboard")
            return
        except ImportError:  
            logger.warning("Even older, incompatible save format being used.")
            if not pickle_data:
                f.close()
                f = open(filename, 'r')

            try:
                save_data = method(f)
            except (pickle.UnpicklingError, AttributeError, ImportError, ValueError, TypeError, EOFError):
                logger.exception("Save file has corrupt data")
                wx.MessageBox(_('"%s" has corrupt data.\nThis file cannot be loaded.') % os.path.basename(filename),
                              u"Whyteboard")
                return
            finally:
                if not pickle_data:
                    f.close()
        finally:
            if not pickle_data:
                f.close()

        logger.debug("Removing tools namespace")
        del sys.modules['tools']
        self.recreate_save(filename, save_data)


    def recreate_save(self, filename, save_data):
        """
        Recreates the saved .wtbd file's state
        """
        logger.debug("Recreating save file")
        self.filename = filename
        self.gui.show_progress_dialog(_("Loading..."))
        self.gui.remove_all_sheets()

        # change program settings and update the Preview window
        self.colour = save_data[0][0]
        self.thickness = save_data[0][1]
        self.tool = save_data[0][2]
        self.gui.control.change_tool(_id=self.tool)  # toggle button
        self.gui.control.colour.SetColour(self.colour)
        self.gui.control.thickness.SetSelection(self.thickness - 1)

        # re-create tabs and its saved drawings
        for x in save_data[1]:
            self.gui.on_new_tab(name=save_data[3][x])
            size = (Config().default_width(), Config().default_height())
            try:
                size = save_data[4][x]
            except KeyError:
                pass
            self.gui.canvas.resize(size)

            try:
                media = save_data[5][x]
                for m in media:
                    m.canvas = self.gui.canvas
                    m.load()
                    self.gui.canvas.medias.append(m)
            except KeyError:
                break

            for shape in save_data[1][x]:
                try:
                    shape.canvas = self.gui.canvas  # restore canvas
                    shape.load()  # restore unpickleable settings
                    self.gui.canvas.add_shape(shape)
                except Exception:
                    break
            self.gui.canvas.redraw_all(True)

        # close progress bar, handle older file versions gracefully
        wx.PostEvent(self.gui, self.gui.LoadEvent())
        self.mark_saved()
        self.saved_version = save_data[0][4]
        pub.sendMessage('canvas.change_tool')
        self.gui.tabs.SetSelection(save_data[0][3])
        self.gui.on_change_tab()
        self.gui.SetTitle(u"%s - %s" % (os.path.basename(filename), self.gui.title))
        self.gui.closed_tabs = list()

        try:
            if save_data[0][5]:
                logger.debug("Setting default font from save file: [%s]", save_data[0][5])
                font = wx.FFont(1, wx.FONTFAMILY_DEFAULT)
                font.SetNativeFontInfoFromString(save_data[0][5])
                self.font = font
        except IndexError:
            pass

        #  Don't save .wtbd file of future versions as current, older version
        if version_is_greater(self.saved_version, meta.version):
            self.update_version = False


    def save_last_path(self, path):
        logger.debug("Writing last opened directory [%s] to config", path)
        Config().last_opened_dir(os.path.dirname(path))
        Config().write()

    def mark_saved(self):
        self.saved = True
        self.save_time = time.time()

    def convert(self):
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

        _file = self.temp_file
        logger.info("Converting [%s]", os.path.basename(_file))

        quality = Config().convert_quality()
        cached = self.library.lookup(_file, quality)
        if cached:
            logger.debug("PDF is cached")
            self.display_converted(_file, cached)
        else:
            path = get_home_dir(u"wtbd-tmp")  # directory to store the images
            tmp_file = make_filename()
            before = os.walk(path).next()[2]  # file count before convert
            full_path = path + tmp_file + u".png"
            logger.debug("Writing PDF images as [%s]", full_path)

            cmd = convert_quality(quality, self.im_location, _file, full_path)
            logger.info("Starting to convert PDF")
            self.gui.convert_dialog(cmd)  # show progress bar, kick off convert

            if self.gui.convert_cancelled:
                logger.info("Convert process cancelled by user")
                return
            after = os.walk(path).next()[2]
            count = len(after) - len(before)
            images = []
            ignore = False
            logger.info("Convert process complete. %i images were created", count)

            if not count:
                logger.warning("Failed to convert.")
                wx.MessageBox(_("Failed to convert file. Ensure GhostScript is installed\nhttp://pages.cs.wisc.edu/~ghost/"), _("Conversion Failed"))
                open_url(u"http://pages.cs.wisc.edu/~ghost/")
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
        logger.debug("Displaying PDF images")
        if not ignore_close and self.gui.tab_count == 1 and not self.gui.canvas.shapes:
            logger.info("Closing all sheets")
            self.gui.remove_all_sheets()

        for x in range(len(images)):
            name = u"%s - %s" % (os.path.basename(_file)[:15], x + 1)
            self.gui.on_new_tab(name=name)
            load_image(images[x], self.gui.canvas, tools.Image)
        
        logger.debug("Files loaded - redrawing canvas")
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
                logger.warning("Could not find ImageMagick")
                wx.MessageBox(_("ImageMagick was not found. You will be unable to load PDF and PS files until it is installed."),
                              u"Whyteboard")
            else:
                self.im_location = u"convert"
        elif os.name == "nt":
            if not Config().imagemagick_path():
                self.gui.prompt_for_im()
                if self.im_location:
                    Config().imagemagick_path(os.path.dirname(self.im_location))
                    Config().write()
            else:
                self.check_im_path(Config().imagemagick_path())


    def check_im_path(self, path):
        """
        Checks the ImageMagick path before getting/setting the string to ensure
        convert.exe exists
        """
        _file = os.path.join(path, u"convert.exe")
        if not os.path.exists(_file):
            logger.warning("Could not find ImageMagick's convert.exe in [%s]", path)
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

    def set_colour(self, colour):
        self.colour = colour

    def set_background(self, colour):
        self.background = colour

#----------------------------------------------------------------------

class PDFCache(object):
    """
    Represents a cache of any converted PDF files
    """
    def __init__(self, filename):
        self.path = os.path.join(get_home_dir(), filename)
        logger.debug("Using PDF cache at [%s]", self.path)
        if not os.path.exists(self.path):
            logger.debug("Cache file does not exist - creating it")
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
        logger.debug("Adding [%s] at [%s] quality to cache", os.path.basename(location), quality)
        files = self.entries()
        files[len(files)] = {'file': location, 'images': images,
                             'quality': quality, 'date': time.asctime()}
        self.write_dict(files)


    def write_dict(self, files):
        logger.debug("Writing to PDF cache")
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
