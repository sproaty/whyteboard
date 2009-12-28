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

#----------------------------------------------------------------------


def save_pasted_images(shapes):
    """
    When saving a Whyteboard file, any pasted Images (with path == None)
    will be saved to a directory in the user's home directory, and the image
    reference changed.
    If the same image is pasted many times, it will be only stored once and
    all images with that common image filepath will be updated.
    """
    data = {}
    for shape in shapes:
        if isinstance(shape, tools.Image):
            img1 = shape.image.ConvertToImage()

            if not shape.path:
                for path in data:
                    if path == img1.GetData():
                        shape.path = path
                        break

                #  the above iteration didn't find any common pastes
                if not shape.path:
                    path = get_home_dir("pastes")
                    tmp_file = path + make_filename() + ".jpg"
                    shape.image.SaveFile(tmp_file, wx.BITMAP_TYPE_JPEG)
                    shape.path = tmp_file

                    data[shape.path] = img1.GetData()


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
    bmp = wx.EmptyBitmap(19, 19)
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