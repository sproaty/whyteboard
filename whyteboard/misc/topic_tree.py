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
    class change_background:
        '''Changes the background colour panel'''
        colour = 'the wx.Colour object'
        _required = 'colour'

    class change_colour:
        '''Changes the colour panel'''
        colour = 'the wx.Colour object'
        _required = 'colour'        
        
    class update_shape_viewer:
        '''Forces the shape viewer to update itself'''
        pass
        
    class sheet:
        '''Operations performed on the sheets (tabs)'''
        class move:
            '''When a sheet has been dragged/dropped'''
            event = 'the wx.Event that the listener can use as needed'
            tab_count = 'total number of tabs to iterate over for updating'
            _required = ('event', 'tab_count')

        class rename:
            '''sheet being renamed'''
            _id = 'ID (tab number) of the sheet being renamed'
            text = 'new sheet name'
            _required = ('_id', 'text')


    class canvas:
        '''Operations performed on the canvas'''
        class change_tool:
            '''Changes the currently drawing tool to a new one'''
            new = 'optional new tool to change to'

        class paste_image:
            '''Pastes a bitmap onto the canvas'''
            bitmap = 'wx.Bitmap to use'
            x = 'x position on canvas'
            y = 'y position on canvas'
            ignore = 'whether to resize canvas or not'
            _required = ('bitmap', 'x', 'y')
            
        class paste_text:
            '''Pastes a string as a text object'''
            text = 'string to use'
            x = 'x position on canvas'
            y = 'y position on canvas'
            _required = ('text', 'x', 'y')
                                          
        class set_border:
            '''Updates the "grabbable" border size the canvas has'''
            border_size = 'size in pixels to set the border to'
            _required = 'border_size'

        class capture_mouse:
            '''Captures mouse focus'''
            pass

        class release_mouse:
            '''Releases mouse focus'''
            pass


    class gui:
        '''Operations performed on the gui'''
        class mark_unsaved:
            '''Notifies that the canvas has unsaved changes'''
            pass
        
        class open_file:
            '''Opens a file'''
            filename = 'file to open'
            _required = 'filename'
                
        class preview:
            class refresh:
                '''Refreshes the drawing preview.'''
                pass
        
            
    class media:
        '''For the media tool'''
        class create_panel:
            '''creates the media panel''' 
            size = "size to make the media panel"
            media = 'the media tool instance'
            _required = ('size', 'media')
            

        
    class note:
        '''The Note Panel, containing a GUI tree of all notes'''
        class delete_sheet_items:
            '''removes all note tools from the current sheet''' 
            pass
            
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
        class update_current:
            '''redraws the current thumbnail'''
            pass
        
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
            
        class popup:
            '''shows a pop-up menu for a given shape'''
            shape = 'shape to use for pop up menu'
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

    class text:
        '''update a Tool'''
        class show_dialog:
            '''popup the text edit/create dialog'''
            text = 'text/note object'
            _required = 'text'

pub.addTopicDefnProvider(WhyteboardTopicTree())