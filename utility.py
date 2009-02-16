#!/usr/bin/python

"""
This module contains a utility helper class to reduce the amount of code
inside gui.py - whiyteboard-file saving/loading, pdf/ps loading/conversion and
loading a standard image.


The saved file structure is:

  dictionary { 0: [colour, thickness, tool, selected_tab],    - program settings
               1: shapes { 0: [shape1, shape2, .. shapeN],   - tab / shapes
                           1: [shape1, shape2, .. shapeN],   - tab / shapes
                           ..
                           N: [shape1, shape2, .. shapeN]
                         }
               2: files  { 0: { 0: filename,                 - converted files
                                1: temp-file-1.png,          - linked tmp file
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
             }

Image Tools have the assosicated image removed from their class upon saving,
but are restored with it upon loading the file.
"""

import os
import cPickle
import random
import platform
from copy import copy

from wx import MessageBox, Bitmap, StandardPaths, BufferedDC

from whyteboard import Whyteboard
from tools import (Pen, Rectangle, Circle, Ellipse, RoundRect, Text, Eyedropper,
                   Line, Fill, Arc, Image)


#----------------------------------------------------------------------

class Utility(object):
    """
    The class defines some class variables which are set/accessed through the GUI -
    supported filetypes, names of the drawing tools, a save file's associated
    converted files (e.g. a PDF)

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
        self.saved_shapes = {}  # used for undo/redo checking save state
        self.saved = True
        self.colour = "Black"
        self.thickness = 1
        self.tool = 1  # Current tool that is being drawn with
        self.make_wildcard()
        self.items = [Pen, Rectangle, Circle, Ellipse, RoundRect, Text, Fill,
                      Line, Eyedropper]

        # test to see if ImageMagick is installed
        #if platform.system() == "Linux":
        #    value = os.system("which convert")
        #    if value == 256:
        #        MessageBox("ImageMagick was not found on your system. ")


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

            # load in every shape from every tab
            for x in range(0, self.gui.tab_count):
                temp[x] = copy(self.gui.tabs.GetPage(x).shapes)

            if temp:
                self.saved_shapes = temp
                for x in temp:
                    for shape in temp[x]:
                        # need to unlink unpickleable items; be restored on load
                        if isinstance(shape, Image):
                            shape.image = None
                        if isinstance(shape, Text):
                            shape.text = shape.txt_ctrl.GetValue()
                            shape.txt_ctrl = None

                        shape.board = None
                        shape.pen = None
                        shape.brush = None

                # Now the unpickleable objects are gone, build the save file
                tab = self.gui.tabs.GetSelection()
                _file = { 0: [self.colour, self.thickness, self.tool, tab],
                          1: temp,
                          2: self.to_convert }

                f = open(self.filename, 'w')
                try:
                    cPickle.dump(_file, f)

                    # restore saved text shapes, the actual objects get set
                    # to None, somehow, this rebuilds them from its saved text
                    for x in range(0, self.gui.tab_count):
                        for s in self.gui.tabs.GetPage(x).shapes:
                            if isinstance(s, Text):
                                s.board = self.gui.tabs.GetPage(x)
                                s.make_control()

                            s.make_pen()  # restore wx.Pen from colour/thickness

                except cPickle.PickleError:
                    MessageBox("Error saving file data")
                f.close()
            else:
                MessageBox("Error saving file data")


    def load_file(self, filename=None):
        """
        Loads in a file, passes it to convert if it is a convertable file,
        then either loads an image or unpickles a whyteboard file

        Loading in a whyteboard file recursively calls this method.
        """
        if filename is None:
            filename = self.temp_file

        _type = os.path.splitext(filename)[1]  # convert to lowercase
        _type = _type.replace(".", "").lower()  # otherwise type filename[1:]

        if _type in self.types[:3]:
            self.convert()

        elif _type in self.types[3:]:
            self.load_image(self.temp_file, self.gui.board)

        elif _type.endswith("wtbd"):
            temp = {}
            f = open(self.filename, 'r')
            try:
                temp = cPickle.load(f)
            except cPickle.UnpicklingError:
                MessageBox("%s is not a valid Whyteboard file." % self.filename)
            f.close()

            # change program settings and update the Preview window
            self.saved = True
            self.colour = temp[0][0]
            self.thickness = temp[0][1]
            self.tool = temp[0][2]
            self.to_convert = temp[2]
            self.saved_shapes = temp[1]
            self.gui.control.change_tool()
            self.gui.control.colour.SetColour(self.colour)
            self.gui.control.thickness.SetSelection(self.thickness - 1)
            self.gui.control.preview.Refresh()

            for x in range(0, self.gui.tab_count):
                self.gui.tabs.RemovePage(x)
            self.gui.tab_count = 0

            for x, shape in enumerate(temp[1]):
                wb = Whyteboard(self.gui.tabs)
                wb.shapes = temp[1][shape]
                name = "Untitled "+ str(x + 1)
                self.gui.tabs.AddPage(wb, name)
                self.gui.tab_count += 1

                dc = BufferedDC(None, wb.buffer)

                for s in temp[1][shape]:
                    # restore unpickleable settings
                    s.board = wb

                    if isinstance(s, Image):
                        image = Bitmap(s.path)
                        s.image = image
                        size = (image.GetWidth(), image.GetHeight())

                        self.gui.board.update_scrollbars(size)
                        dc = BufferedDC(None, wb.buffer)  # get updated buffer
                    if isinstance(s, Text):
                        s.make_control()  # restore text

                    s.make_pen()  # restore colour/thickness
                    s.draw(dc)  # draw each shape

            try:
                self.gui.tabs.SetSelection(temp[0][3])
            except IndexError:
                MessageBox("Warning: This save file was created in an older " +
                "version of Whyteboard. Saving the file will update it to the "+
                "latest version.")
        else:
            MessageBox("Invalid file to load.")


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
        if _file is None:
            _file = self.temp_file

        filename = os.path.split(_file)[1]

        std_paths = StandardPaths.Get()
        path = StandardPaths.GetUserLocalDataDir(std_paths)  # $HOME/.appName
        path = os.path.join(path, "wtbd-tmp", "")  # "" forces slash at end

        # Create a random filename using letters and numbers
        alphabet = 'abcdefghijklmnopqrstuvwxyz1234567890-'
        _list = []

        for x in random.sample(alphabet, random.randint(3, 12)):
            _list.append(x)

        string = "".join(_list)
        tmp_file = string +"-temp-"+ str(random.randrange(0, 999999))

        if not os.path.isdir(path):
            os.makedirs(path)

        index = len(self.to_convert)
        self.to_convert[index] = { 0: str(_file) }
        before = os.walk(path).next()[2]  # file count before convert

        #cmd = "convert -density 294 "+ _file +" -resample 108 -unsharp 0x.5 \
        #-trim +repage -bordercolor white -border 7 "+ path + tmp_file +".png"
        # ------------------------------------------------
        # better PDF quality, takes longer to convert
        cmd = "convert "+ _file +" "+ path + tmp_file +".png"
        self.gui.convert_dialog(cmd)  # show progress bar
        after = os.walk(path).next()[2]
        count = len(after) - len(before)

        if count == 1:
            temp_path = path + tmp_file +".png"
            self.load_image(temp_path, self.gui.board)
            self.to_convert[index][1] = temp_path
        else:
            # remove single tab with no drawings
            if self.gui.tab_count == 1 and not self.gui.board.shapes:
                self.gui.tabs.RemovePage(0)
                self.gui.tab_count = 0

            for x in range(0, count):
                wb = Whyteboard(self.gui.tabs)

                # the tmp. file path, store it in the dict. for this file
                temp_file = path + tmp_file +"-"+ str(x) +".png"
                self.load_image(temp_file, wb)
                self.to_convert[index][x + 1] = temp_file

                name = filename +" - pg."+ str(x+1)
                self.gui.tabs.AddPage(wb, name)
                self.gui.tab_count += 1


    def load_image(self, path, board):
        """
        Loads an image into the given Whyteboard tab. bitmap is the path to an
        image file to create a bitmap from.
        """
        image = Bitmap(path)
        shape = Image(board, image, path)
        shape.button_down(0, 0)  # renders, updates scrollbars


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


#----------------------------------------------------------------------
if __name__ == '__main__':
    from gui import WhyteboardApp
    app = WhyteboardApp()
    app.MainLoop()
