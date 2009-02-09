#!/usr/bin/python

"""
This module contains a utility helper class to reduce the amount of code
inside gui.py - whiyteboard-file saving/loading, pdf/ps loading/conversion
and loading a standard image.

It also defines some class variables which are set/accessed through the GUI -
supported filetypes, names of the drawing tools, a save file's associated
converted files (e.g. a PDF)
"""

import os
import cPickle
from copy import copy

from wx import Bitmap

from whyteboard import Whyteboard
from tools import (Pen, Rectangle, Circle, Ellipse, RoundRect,
                  Text, Eyedropper, Fill, Arc, Image)


class Utility(object):

    def __init__(self, gui, filename=None, to_convert=None):
        if to_convert is None:
            to_convert =  {}

        self.gui = gui
        self.filename = filename  # ACTIVE .wtbd file
        self.to_convert = to_convert  # list of files
        self.temp_file = None  # selected file (.wtdb/png/pdf - doesn't matter)
        self.saved = False

        self.items = [Pen, Rectangle, Circle, Ellipse, RoundRect,
                      Text, Eyedropper, Fill, Arc]

        #  Make wxPython wildcard filter. Add a new item - new type supported!
        self.types = ["ps", "pdf", "svg", "jpeg", "jpg", "png", "gif", "tiff",
                       "bmp", "pcx"]

        label = ["All files (*.*)", "Whyteboard file (*.wtbd)", "Image Files",
                 "Page Description Languages"]

        result1 = ';'.join('*.' + i for i in self.types[:-2])
        result2 = ';'.join('*.' + i for i in self.types[0:2])
        wc_types = ["*.*", "*.wtbd", result1, result2]

        wc_list = map(lambda x, y, : x + "|" + y, label, wc_types)
        self.wildcard = '|'.join(wc_list)


    def save_file(self):
        """
        Saves the file if there is any drawn data to save. Any loaded Image
        objects must be removed - they will be converted back upon loading
        a saved file.
        - Returns: True/False
        """
        if self.filename:
            temp = {}

            for x in range(0, self.gui.tab_count ):
                temp[x] = copy(self.gui.tabs.GetPage(x).shapes)

            if temp:
                #  Unlink tools' board and images' image - restored on load.
                for x in temp:
                    for shape in temp[x]:
                        if isinstance(shape, Image):
                            shape.image = None
                        shape.board = None

                f = open(self.filename, 'w')
                try:
                    cPickle.dump(temp, f)
                except cPickle.PickleError:
                    wx.MessageBox("Error saving file data")
                f.close()
            else:
                wx.MessageBox("Error saving file data")


    def load_file(self):
        """
        Loads in a file, passes it to convert if it is not a .wtbd file,
        otherwise the file attempts to get unpickled
        - Returns: True/False
        ."""
        type = os.path.splitext(self.temp_file)[1]
        type = type.replace(".", "")

        if type in self.types[:3]:
            self.convert()
        elif type in self.types[3:]:
            image = Bitmap(self.temp_file)  # load image into current tab
            shape = Image(self.gui.board, image=image)
            shape.button_down(0, 0)
        elif type.endswith("wtbd"):

            temp = {}
            f = open(self.filename, 'r')
            try:
                temp = cPickle.load(f)
            except cPickle.UnpicklingError:
                MessageBox("%s is not a valid Whyteboard file." % self.filename)
            f.close()

            # load in new tabs for every dictionary item
            if self.tabs.tab_count() > 0 and not self.board.shapes:
                self.tabs.DeleteAllPages()
            for x in temp:
                wb = Whyteboard(self.tabs)
                wb.select_tool(1)
                wb.shapes = temp[x]
                wb.AddListener(self.cPanel.ci)
                wb.notify()
                self.tabs.AddPage(wb, "Untitled "+str(self.tabs.tab_count + 1))

                for shape in wb.shapes:
                    shape.board = wb

            self.SetTitle(os.path.split(self.filename)[1] +' - '+ self.title)
        else:
            MessageBox("Invalid file to load.")


    def convert(self, file=None):
        """
        If the filetype is PDF/PS, convert to a (temporary) image and loads it.
        Find out the directory length before/after the conversion to know how
        many 'pages' were converted - used then to
        """
        if file is None:
            file = self.temp_file

        path, filename = os.path.split(file)
        path += "/wtbd-tmp/"
        tmp_file = "temp-0"

        if not os.path.isdir(path):
            os.mkdir(path)

        before = os.walk(path).next()[2]  # file count before convert
        os.system("convert "+ file +" "+ path + tmp_file +".png")
        after = os.walk(path).next()[2]
        count = len(after) - len(before)

        if count == 1:
            image = Bitmap(path + tmp_file +".png")
            shape = Image(self.gui.board, image=image)
            shape.button_down(0, 0)
        else:
            for x in range(0, count):
                wb = Whyteboard(self.gui.tabs)

                image = Bitmap(path + tmp_file +"-"+ str(x) +".png")
                shape = Image(wb, image=image)
                shape.button_down(0, 0)

                name = filename +" - pg."+ str(x+1)
                self.gui.tabs.AddPage(wb, name)
                self.gui.tab_count += 1


    def add_to_convert(self, filename):
        pass

    def cleanup(self):
        """
        Cleans up any temporarily png files from conversions.
        """
#        if self.converted is not False:
#            if self.count == 1:
#                os.remove( os.path.split(self.converted)[0] +"/temp-0.png")
#            else:
#                for x in range(0, self.count):
#                    os.remove( os.path.split(self.converted)[0] +"/temp-0-"+ str(x) +".png")




#----------------------------------------------------------------------

if __name__ == '__main__':
    from gui import WhyteboardApp
    app = WhyteboardApp()
    app.MainLoop()
