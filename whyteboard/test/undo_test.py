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

"""

import os

from wx import TRANSPARENT

import whyteboard.tools as tools

from whyteboard.gui import Canvas
from whyteboard.lib import Mock, pub
from whyteboard.misc import undo


#----------------------------------------------------------------------

class TestUndo(object):
    """
    Tests undoing objects
    """
    def test_undo_shape(self):
        # given
        canvas = Mock(wraps=Canvas)
        shape = tools.Rectangle(canvas, (0, 0, 0), 1, TRANSPARENT)

        # when
        shape.move(1, 2, (1, 2))
        shape.assert_called_with(1, 2, (1, 2))


        # then