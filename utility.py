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
inside gui.py - whiyteboard-file saving/loading, pdf/ps loading/conversion and
loading a standard image.

The saved file structure is:

  dictionary { 0: [colour, thickness, tool, tab, version],   - program settings
               1: shapes { 0: [shape1, shape2, .. shapeN],  1 / shapes
                           1: [shape1, shape2, .. shapeN],  2 / shapes
                           ..
                           N: [shape1, shape2, .. shapeN]
                         }
               2: files  { 0: { 0: filename,                  - converted files
                                1: temp-file-1.png,           - linked tmp file
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
             }

Image Tools have the assosicated image removed from their class upon saving,
but are restored with it upon loading the file.
"""

import wx
import os
import cPickle
import random
from copy import copy
from platform import system

from whyteboard import Whyteboard
from dialogs import ProgressDialog, FindIM
import tools


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
        self.to_convert = {}   # list of files
        self.filename = None   # ACTIVE .wtbd file
        self.temp_file = None  # selected file (.wtdb/png/pdf - doesn't matter)
        #self.saved_shapes = {}  # used for undo/redo checking save state
        self.saved = True
        self.colour = "Black"
        self.thickness = 1
        self.tool = 1  # Current tool that is being drawn with
        self.make_wildcard()
        self.items = tools.items

        self.im_location = None  # location of ImageMagick on windows


    def make_wildcard(self):
        """
        Make wxPython wildcard filter. Add a new item - new type supported!
        """
        self.types = ["ps", "pdf", "svg", "jpeg", "jpg", "png", "gif", "tiff",
                       "bmp", "pcx"]
        label = ["All files (*.*)", "Whyteboard file (*.wtbd)", "Image Files",
                 "Page Description Languages"]

        result1 = ';'.join('*.' + i for i in self.types[2:-2])
        result2 = ';'.join('*.' + i for i in self.types[0:2])
        wc_types = ["*.*", "*.wtbd", result1, result2]

        # format: label|*.type1;*.type2|label|*.type3;*.type4|label|*...
        wc_list = map(lambda x, y, : x + "|" + y, label, wc_types)
        self.wildcard = '|'.join(wc_list)



    def save_file(self):
        """
        Saves the file if there is any drawn data to save. Any loaded Image
        objects must be removed - they will be converted to an Image loading
        a saved file.
        """
        if self.filename:
            temp = {}
            names =  []

            # load in every shape from every tab
            for x in range(0, self.gui.tab_count):
                self.save_pasted_images(self.gui.tabs.GetPage(x).shapes)
                temp[x] = copy(self.gui.tabs.GetPage(x).shapes)
                names.append(self.gui.tabs.GetPageText(x))

            if temp:
                self.saved_shapes = self.save_pasted_images(temp)
                for x in temp:
                    for shape in temp[x]:
                        shape.save()  # need to unlink unpickleable items;

                # Now the unpickleable objects are gone, build the save file
                tab = self.gui.tabs.GetSelection()
                _file = { 0: [self.colour, self.thickness, self.tool, tab,
                              self.gui.version],
                          1: temp,
                          2: self.to_convert,
                          3: names }

                f = open(self.filename, 'w')
                try:
                    cPickle.dump(_file, f)
                    t = os.path.split(self.filename)[1] + ' - ' + self.gui.title
                    self.gui.SetTitle(t)
                except cPickle.PickleError:
                    wx.MessageBox("Error saving file data")
                    self.saved = False
                    self.filename = None
                finally:
                    f.close()

                for x in temp:
                    for shape in temp[x]:
                        shape.board = self.gui.tabs.GetPage(x)
                        shape.load()
            else:
                wx.MessageBox("Error saving file data - no data to save")
                self.saved = False
                self.filename = None


    def save_pasted_images(self, shapes):
        """
        When saving a Whyteboard file, any pasted Images (with path == None)
        will be saved to a directory in the user's home directory, and the image
        reference changed.
        If the same image is pasted many times, it will be only stored once and
        all images with that common image filepath will be updated.
        """
        data = {}
        for x, shape in enumerate(shapes):
            if isinstance(shape, tools.Image):
                img1 = shape.image.ConvertToImage()

                if not shape.path:
                    for path in data:
                        if data[path] == img1.GetData():
                            shape.path = path
                            break

                    #  the above iteration didn't find any common pastes
                    if not shape.path:
                        path = get_home_dir("pastes")
                        tmp_file = path + make_filename() + ".jpg"
                        shape.image.SaveFile(tmp_file, wx.BITMAP_TYPE_JPEG)
                        shape.path = tmp_file

                        data[shape.path] = img1.GetData()


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

        elif _type.endswith("wtbd"):
            self.load_wtbd(filename)
        else:
            wx.MessageBox("Whyteboard doesn't support the filetype .%s" % _type)


    def load_wtbd(self, filename):
        """
        Closes all tabs, loads in a Whyteboard save file into their proper
        tab
        """
        temp = {}
        f = open(self.filename, 'r')
        try:
            temp = cPickle.load(f)
        except (cPickle.UnpicklingError, ValueError, ImportError):
            wx.MessageBox("%s has corrupt Whyteboard data. No action taken."
                        % self.filename)
            return
        finally:
            f.close()

        self.gui.dialog = ProgressDialog(self.gui, "Loading...", 30)
        self.gui.dialog.Show()

        #  Remove all tabs, thumbnails and tree note items
        self.gui.board = None
        for x in range(self.gui.tab_count -1, -1, -1):
            self.gui.tabs.RemovePage(x)
        self.gui.thumbs.remove_all()
        self.gui.notes.remove_all()
        self.gui.tab_count = 0

        # change program settings and update the Preview window
        self.saved = True
        self.colour = temp[0][0]
        self.thickness = temp[0][1]
        self.tool = temp[0][2]
        self.to_convert = temp[2]
        #self.saved_shapes = temp[1]
        self.gui.control.change_tool(_id = self.tool)
        self.gui.control.colour.SetColour(self.colour)
        self.gui.control.thickness.SetSelection(self.thickness - 1)
        self.gui.control.preview.Refresh()
        self.gui.SetTitle(os.path.split(filename)[1] +' - '+ self.gui.title)

        # re-create tabs and its saved drawings
        for x, board in enumerate(temp[1]):
            wb = Whyteboard(self.gui.tabs)
            wb.select_tool()
            try:
                name = temp[3][x]
            except KeyError:
                name = "Sheet " + str(x + 1)

            self.gui.tabs.AddPage(wb, name)
            self.gui.tab_count += 1
            self.gui.thumbs.new_thumb()
            self.gui.notes.add_tab()

            for shape in temp[1][x]:
                shape.board = wb  # restore board
                shape.load()  # restore unpickleable settings
                wb.add_shape(shape)

            wb.redraw_all()
            wb.Refresh()

        # close progress bar, handle older file versions gracefully
        wx.PostEvent(self.gui, self.gui.LoadEvent())
        self.gui.board.select_tool(temp[0][2])

        try:
            version = temp[0][4]
        except IndexError:
            version = "< 0.33"

        try:
            self.gui.tabs.SetSelection(temp[0][3])
        except IndexError:
            wx.MessageBox("Warning: This save file was created in an older "
            + "version of Whyteboard ("+version+"). Saving the file will " +
            "update it to the latest version, " + self.gui.version)
            self.gui.tabs.SetSelection(0)


    def convert(self, _file=None):
        """
        If the filetype is PDF/PS, convert to a (temporary) image and loads it.
        Find out the directory length before/after the conversion to know how
        many 'pages' were converted - used then to iterate over the temporary
        images, creating new Whyteboard tabs for each page, and storing the
        results in a dictionary, to_convert.

        An attempt at randomising the temp. file name is made using alphanumeric
        characters to help minimise conflict.
        """
        if not self.im_location:
            self.prompt_for_im()

        # above will have changed this value if the user selected IM's dir.
        if not self.im_location:
            return
        if _file is None:
            _file = self.temp_file

        path = get_home_dir("wtbd-tmp")
        tmp_file = make_filename()  #

        index = len(self.to_convert)
        self.to_convert[index] = { 0: str(_file) }
        before = os.walk(path).next()[2]  # file count before convert

        #cmd = "convert -density 294 "+ _file +" -resample 108 -unsharp 0x.5 \
        #-trim +repage -bordercolor white -border 7 "+ path + tmp_file +".png"
        # ------------------------------------------------
        # better PDF quality, takes longer to convert
        # ------------------------------------------------
        # convert "[file path]" "[destination-folder]" -- quotes for Windows

        cmd = ("\""+self.im_location + "\" \"" + _file + "\" \""
                + path + tmp_file + ".png\"")

        self.gui.convert_dialog(cmd)  # show progress bar
        after = os.walk(path).next()[2]
        count = len(after) - len(before)

        if count == 1:
            temp_path = path + tmp_file + ".png"
            load_image(temp_path, self.gui.board)
            self.to_convert[index][1] = temp_path
        else:
            # remove single tab with no drawings
            if self.gui.tab_count == 1 and not self.gui.board.shapes:
                self.gui.tabs.DeletePage(0)
                self.gui.thumbs.remove_all()
                self.gui.notes.remove_all()
                self.gui.tab_count = 0

            for x in range(0, count):
                wb = Whyteboard(self.gui.tabs)

                # store the temp file path for this file in the dictionary
                temp_file = path + tmp_file + "-" + str(x) + ".png"
                load_image(temp_file, wb)
                self.to_convert[index][x + 1] = temp_file
                self.gui.tab_count += 1
                name = os.path.split(_file)[1] + " p" + str(x + 1)
                self.gui.tabs.AddPage(wb, name)

                self.gui.thumbs.new_thumb()
                self.gui.notes.add_tab()

        # Just in case it's a file with many pages
        self.gui.dialog = ProgressDialog(self.gui, "Loading...", 30)
        self.gui.dialog.Show()
        self.gui.on_done_load()


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

        context = wx.MemoryDC(self.gui.board.buffer)
        memory = wx.MemoryDC()
        x, y = self.gui.board.buffer.GetSize()
        bitmap = wx.EmptyBitmap(x, y, -1)
        memory.SelectObject(bitmap)
        memory.Blit(0, 0, x, y, context, 0, 0)
        memory.SelectObject(wx.NullBitmap)
        bitmap.SaveFile(filename, const)  # write to disk


    def cleanup(self):
        """
        Cleans up any temporarily png files from conversions.
        Element 0 in y is the filename, so we don't want to remove that :)
        """
        if self.to_convert:
            for x in self.to_convert.keys():
                for y in self.to_convert[x].keys():
                    if y is not 0:
                        os.remove(self.to_convert[x][y])


    def prompt_for_im(self):
        """
        Prompts a Windows user for ImageMagick's directory location on
        initialisation
        """
        if system() == "Linux":
            value = os.system("which convert")
            if value == 256:
                wx.MessageBox("ImageMagick was not found. You will be unable " +
                              "to load PDF and PS files until it is installed.")
            else:
                self.im_location = "convert"
        elif system() == "Windows":
            path = get_home_dir()
            path = os.path.join(path, "user.pref")

            if not os.path.exists(path):
                dlg = FindIM(self, self.gui)
                dlg.ShowModal()
                if self.im_location:
                    # save the ImageMagick directory location
                    loc = self.im_location.replace("convert.exe", "")
                    _file = open(path, "w")
                    _file.write("imagemagick_location=" + loc)
            else:
                # verify loaded file's IM directory is valid
                for pref in open(path, "r"):
                    self.check_im_path(pref.split("=")[1])


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


    def get_clipboard(self):
        """
        Checks the clipboard for any valid image data to paste
        """
        bmp = wx.BitmapDataObject()
        wx.TheClipboard.Open()
        success = wx.TheClipboard.GetData(bmp)
        wx.TheClipboard.Close()
        if success:
            return bmp
        return False

    def set_clipboard(self, rect):
        """
        Sets the clipboard with a bitmap image data of a selection
        rectangle = (x, y, width, height)
        """
        temp = self.gui.board.buffer.GetSubBitmap(rect)
        bmp = wx.BitmapDataObject()
        bmp.SetBitmap(temp)

        wx.TheClipboard.Open()
        success = wx.TheClipboard.SetData(bmp)
        wx.TheClipboard.Close()


#----------------------------------------------------------------------

class FileDropTarget(wx.FileDropTarget):
    """
    Implements drop target functionality to receive files
    """
    def __init__(self, gui):
        wx.FileDropTarget.__init__(self)
        self.gui = gui


    def OnDropFiles(self, x, y, filenames):
        """
        Passes the first file to the load file method to handle
        """
        self.gui.do_open(filenames[0])

#----------------------------------------------------------------------

def load_image(path, board):
    """
    Loads an image into the given Whyteboard tab. bitmap is the path to an
    image file to create a bitmap from.
    """
    image = wx.Bitmap(path)
    shape = tools.Image(board, image, path)
    shape.button_down(0, 0)  # renders, updates scrollbars


def make_filename():
    """
    Create a random filename using letters, numbers and other characters
    """
    alphabet = ("abcdefghijklmnopqrstuvwxyz1234567890-+!^&()=[]@$% " +
                "ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    _list = []
    for x in random.sample(alphabet, random.randint(8, 20)):
        _list.append(x)

    string = "".join(_list)
    return string +"-temp-"+ str(random.randrange(0, 999999))


def get_home_dir(extra_path=None):
    """
    Returns the home directory for Whyteboard cross-platformally
    If the extra path is supplied, it is appended to the home directory.
    The directory is verified to see if it exists: if doesn't, it is created.
    """
    std_paths = wx.StandardPaths.Get()
    path = wx.StandardPaths.GetUserLocalDataDir(std_paths)
    if extra_path:
        path = os.path.join(path, extra_path, "")   # "" forces slash at end

    if not os.path.isdir(path):
        os.makedirs(path)
    return path

#----------------------------------------------------------------------

if __name__ == '__main__':
    from gui import WhyteboardApp
    app = WhyteboardApp()
    app.MainLoop()
