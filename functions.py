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

import os
import random
import wx

import tools

# the IDs for event binding, put here so they can accessed by all

ID_CHANGE_TOOL = wx.NewId()       # change tool hotkey
ID_CLEAR_ALL = wx.NewId()         # remove everything from current tab
ID_CLEAR_ALL_SHEETS = wx.NewId()  # remove everything from all tabs
ID_CLEAR_SHEETS = wx.NewId()      # remove all drawings from all tabs, keep imgs
ID_DESELECT = wx.NewId()          # deselect shape
ID_EXPORT = wx.NewId()            # export sheet to image file
ID_EXPORT_ALL = wx.NewId()        # export every sheet to numbered image files
ID_EXPORT_PDF = wx.NewId()        # export->PDF
ID_EXPORT_PREF = wx.NewId()       # export->preferences
ID_FULLSCREEN = wx.NewId()        # toggle fullscreen
ID_HISTORY = wx.NewId()           # history viewer
ID_IMPORT_IMAGE = wx.NewId()      # import->Image
ID_IMPORT_PDF = wx.NewId()        # import->PDF
ID_IMPORT_PREF = wx.NewId()       # import->Preferences
ID_IMPORT_PS = wx.NewId()         # import->PS
ID_MOVE_UP = wx.NewId()           # move shape up
ID_MOVE_DOWN = wx.NewId()         # move shape down
ID_MOVE_TO_TOP = wx.NewId()       # move shape to the top
ID_MOVE_TO_BOTTOM = wx.NewId()    # move shape to the bottom
ID_NEW = wx.NewId()               # new window
ID_NEXT = wx.NewId()              # next sheet
ID_PASTE_NEW = wx.NewId()         # paste as new selection
ID_PREV = wx.NewId()              # previous sheet
ID_RELOAD_PREF = wx.NewId()       # reload preferences
ID_RENAME = wx.NewId()            # rename sheet
ID_REPORT_BUG = wx.NewId()        # report a problem
ID_RESIZE = wx.NewId()            # resize dialog
ID_ROTATE = wx.NewId()            # rotate dialog for image 90/180/270
ID_SHAPE_VIEWER = wx.NewId()      # view/edit shapes
ID_STATUSBAR = wx.NewId()         # toggle statusbar
ID_TOOLBAR = wx.NewId()           # toggle toolbar
ID_TRANSLATE = wx.NewId()         # open translation URL
ID_UNDO_SHEET = wx.NewId()        # undo close sheet
ID_UPDATE = wx.NewId()            # update self


#----------------------------------------------------------------------


def save_pasted_images(shapes, utility):
    """
    When saving a Whyteboard file, any pasted Images (with path == None)
    will be saved to a directory in the user's home directory, and the image
    reference changed.
    If the same image is pasted many times, it will be only stored once and
    all images with that common image filepath will be updated.
    """
    data = {}
    for key, value in shapes.items():  # each tab
        for shape in value:  # each tab's shapes
            if isinstance(shape, tools.Image):
                img = shape.image.ConvertToImage()
                img_data = img.GetData()

                if not shape.path:
                    for k, v in data.items():
                        if v == img_data:
                            shape.path = k
                            break

                    #  the above iteration didn't find any common pastes
                    if not shape.path:
                        path = get_home_dir("pastes")
                        tmp_file = path + make_filename() + ".jpg"
                        shape.image.SaveFile(tmp_file, wx.BITMAP_TYPE_JPEG)
                        shape.path = tmp_file
                        utility.to_archive.append(tmp_file)
                        data[shape.path] = img_data



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


def get_time(seconds):
    """Returns an (h:)m:s time from a seconds value - hour not shown if < 0"""
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)

    if h > 0:
        h = "%d:" % h
    else:
        h = ""
    return h + "%02d:%02d" % (m, s)


def load_image(path, board):
    """
    Loads an image into the given Whyteboard tab. bitmap is the path to an
    image file to create a bitmap from.
    """
    image = wx.Bitmap(path)
    shape = tools.Image(board, image, path)
    shape.left_down(0, 0)  # renders, updates scrollbars
    board.update_thumb()
    if not path in board.gui.util.to_archive:
        board.gui.util.to_archive.append(path)


def make_bitmap(colour):
    """
    Draws a small coloured bitmap for a colour grid button. Can take a name,
    RGB tupple or RGB-packed int.
    """
    bmp = wx.EmptyBitmap(20, 20)
    dc = wx.MemoryDC()
    dc.SelectObject(bmp)
    dc.SetBackground(wx.Brush(colour))
    dc.Clear()
    dc.SelectObject(wx.NullBitmap)
    return bmp


def convert_quality(quality, im_location, _file, path):
    """Returns a string for controlling the convert quality"""
    density = 200
    resample = 88

    if quality == 'highest':
        density = 300
        resample = 120
    if quality == 'high':
        density = 250
        resample = 100
    cmd = '"%s" -density %i "%s" -resample %i -unsharp 0x.5 -trim +repage -bordercolor white -border 20 "%s"' % (im_location, density, _file, resample, path)
    return cmd


def make_filename():
    """
    Create a random filename using letters, numbers and other characters
    """
    alphabet = ("abcdefghijklmnopqrstuvwxyz1234567890-+!^&()=[]@$%_ " +
                "ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    _list = []
    for x in random.sample(alphabet, random.randint(8, 20)):
        _list.append(x)

    string = "".join(_list)
    return string +"-temp-%s" % (random.randrange(0, 999999))