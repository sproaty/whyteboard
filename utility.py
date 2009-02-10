#!/usr/bin/python

"""
This module contains a utility helper class to reduce the amount of code
inside gui.py - whiyteboard-file saving/loading, pdf/ps loading/conversion
and loading a standard image.

It also defines some class variables which are set/accessed through the GUI -
supported filetypes, names of the drawing tools, a save file's associated
converted files (e.g. a PDF)

Trying to achieve a data-driven system, focusing on "don't repeat yourself"
"""

import os
import cPickle
from copy import copy
import random

from wx import MessageBox, Bitmap

from whyteboard import Whyteboard
from tools import (Pen, Rectangle, Circle, Ellipse, RoundRect, Text, Eyedropper,
                   Fill, Arc, Image)


#----------------------------------------------------------------------

class Utility(object):

    def __init__(self, gui):
        self.gui = gui
        self.to_convert = {}  # list of files
        self.filename = None  # ACTIVE .wtbd file
        self.temp_file = None  # selected file (.wtdb/png/pdf - doesn't matter)
        self.saved = False
        self.colour = "Black"
        self.thickness = 1
        self.tool = 1  # Current tool that is being drawn with
        self.items = [Pen, Rectangle, Circle, Ellipse, RoundRect, Text,
                      Eyedropper, Fill, Arc]

        #  Make wxPython wildcard filter. Add a new item - new type supported!
        self.types = ["ps", "pdf", "svg", "jpeg", "jpg", "png", "gif", "tiff",
                       "bmp", "pcx"]

        label = ["All files (*.*)", "Whyteboard file (*.wtbd)", "Image Files",
                 "Page Description Languages"]

        result1 = ';'.join('*.' + i for i in self.types[2:-2])
        result2 = ';'.join('*.' + i for i in self.types[0:2])
        wc_types = ["*.*", "*.wtbd", result1, result2]

        # format: label|*.type1,*.type2|label|*.type3,*.type4|label|*...
        wc_list = map(lambda x, y, : x + "|" + y, label, wc_types)

        self.wildcard = '|'.join(wc_list)


    def save_file(self):
        """
        Saves the file if there is any drawn data to save. Any loaded Image
        objects must be removed - they will be converted back upon loading
        a saved file.
        """
        MessageBox("broke.")
#        if self.filename:
#            temp = {}

#            for x in range(0, self.gui.tab_count ):
#                temp[x] = copy(self.gui.tabs.GetPage(x).shapes)

#            if temp:
#                #  Unlink tools' board and images' image - restored on load.
#                for x in temp:
#                    for shape in temp[x]:
#                        if isinstance(shape, Image):
#                            shape.image = None
#                        shape.board = None

#                f = open(self.filename, 'w')
#                try:
#                    cPickle.dump(temp, f)
#                except cPickle.PickleError:
#                    wx.MessageBox("Error saving file data")
#                f.close()
#            else:
#                wx.MessageBox("Error saving file data")


    def load_file(self):
        """
        Loads in a file, passes it to convert if it is a convertable file,
        then either loads an image or unpickles a whyteboard filr
        """
        _type = os.path.splitext(self.temp_file)[1]
        _type = _type.replace(".", "")

        if _type in self.types[:3]:
            self.convert()
        elif _type in self.types[3:]:
            self.load_image(self.temp_file, self.gui.board)
        elif _type.endswith("wtbd"):
#            temp = {}
#            f = open(self.filename, 'r')
#            try:
#                temp = cPickle.load(f)
#            except cPickle.UnpicklingError:
#               MessageBox("%s is not a valid Whyteboard file." % self.filename)
#            f.close()

#            # load in new tabs for every dictionary item
#            if self.gui.tabs_count > 0 and not self.gui.board.shapes:
#                self.gui.tabs.DeleteAllPages()
#            for x in temp:
#                wb = Whyteboard(self.tabs)
#                wb.select_tool(1)
#                wb.shapes = temp[x]
#                wb.AddListener(self.cPanel.ci)
#                wb.notify()
#                self.tabs.AddPage(wb, "Untitled "+str(self.tabs.tab_count + 1))

#                for shape in wb.shapes:
#                    shape.board = wb

#            self.SetTitle(os.path.split(self.filename)[1] +' - '+ self.title)
            MessageBox("currently broke.")
        else:
            MessageBox("Invalid file to load.")


    def convert(self, _file=None):
        """
        If the filetype is PDF/PS, convert to a (temporary) image and loads it.
        Find out the directory length before/after the conversion to know how
        many 'pages' were converted - used then to iterate over the temporary
        images, creating new Whyteboard tabs for each page, and storing the
        results in a dictionary, to_convert.
        """
        if _file is None:
            _file = self.temp_file

        path, filename = os.path.split(_file)
        path = os.path.join(path, "wtbd-tmp", "")  # blank element forces slash
        tmp_file = "temp-"+ str(random.randrange(0,999999))

        if not os.path.isdir(path):
            os.mkdir(path)

        index = len(self.to_convert)
        self.to_convert[index] = { 0: str(_file) }

        #cmd = "convert -density 294 "+ _file +" -resample 108 -unsharp 0x.5 \
        #-trim +repage -bordercolor white -border 7 "+ path + tmp_file +".png"

        before = os.walk(path).next()[2]  # file count before convert
        cmd = "convert "+ _file +" "+ path + tmp_file +".png"

        self.gui.convert_dialog(cmd)

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
        shape = Image(board, image=image)
        shape.button_down(0, 0)  # adds to the whyteboard
        board.redraw = True  # render self


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
