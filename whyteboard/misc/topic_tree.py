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
Specifices a "PyPubSub" topic tree which is a list of all pub/sub events that
the system is listening to.
Helps give an overview of the program as well as prevent any invalid parameters
being passed into the message broadcasts.
"""


from whyteboard.lib import pub
from pub.utils import TopicTreeDefnSimple

_ = wx.GetTranslation

#----------------------------------------------------------------------

class WhyteboardTopicTree(TopicTreeDefnSimple):
    class sheet:
        '''Operations performed on the sheets (tabs)'''
        class move:
            '''When a sheet has been dragged/dropped'''
            event = 'the wx.Event that the listener can use as needed'
            tab_count = 'total number of tabs to iterate over for updating'
            _required = ('event', 'tab_count')

#        class rename:
#            '''sheet being renamed'''
#            _id = 'ID (tab number) of the sheet being renamed'
#            text = 'new sheet name'
#            _required = ('_id', 'text')


    class canvas:
        '''Operations performed on the canvas'''
        class set_border:
            '''Updates the "grabbable" border size the canvas has'''
            border_size = 'size in pixels to set the border to'
            _required = 'border_size'

        class capture_mouse:
            pass

        class release_mouse:
            pass


    class note:
        '''The Note Tool'''
        class add:
            '''when a note is added'''
            note = 'the Note instance'
            _id = 'wx.TreeId'
            _required = 'note'

        class edit:
            '''when a note is edited'''
            tree_id = 'wx.TreeId'
            text = "new Note's text"
            _required = ('tree_id', 'text')


    class thumbs:
        '''Thumbnails'''
        class text:
            '''static text labels'''

            class highlight:
                '''to turn a thumbnail label bold or not'''
                tab = 'which label to update'
                select = 'Whether to highlight the text or not'
                _required = ('tab', 'select')


    class shape:
        '''Operations performed on shapes'''
        class selected:
            '''shape has been select'''
            shape = 'selected shape'
            _required = 'shape'

        class add:
            '''shape has been drawn'''
            shape = 'drawn shape'
            _required = 'shape'


    class shape_viewer:
        '''actions for the Shape Viewer dialog'''
        class update:
            '''an action has been performed to update the dialog'''
            pass


    class tools:
        '''update a Tool'''
        class set_handle_size:
            '''change tools' selection handle size'''
            handle_size = 'size in pixels'
            _required = 'handle_size'


pub.addTopicDefnProvider(WhyteboardTopicTree())