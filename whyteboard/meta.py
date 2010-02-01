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
Contains meta data for the program, such as version, whether transparency is
supported, language mappings, translator credits
All attributes are global, but this module will always be imported, and can be
used as a class in a way. There's simply *no need* to make it a class

The function find_transparency is called from the GUI upon its creation,
instead of before the GUI is created because wx must first initialise its
App object before allowing DC operations
"""

import wx
from functions import transparent_supported

_ = wx.GetTranslation



# Creates a wxPython wildcard filter from a list of known/supported filetypes.
all = [ (_('PDF/PS/SVG'), ['ps', 'pdf', 'svg']),
        (_('Image Files'), ["jpeg", "jpg", "png", "tiff", "bmp", "pcx"]),        
        (_('Whyteboard files'), ['wtbd']) ]

wc_list, types, tmp = [], [], []

for label, exts in all:
    [types.append(x) for x in exts]
    exts = ['*.%s'%a for a in exts]
    visexts = ', '.join(exts)

    exts.extend([e.upper() for e in exts])
    tmp.extend(exts)
    [types.append(x.replace("*.", "")) for x in exts]
    wc_list.append('%s (%s)|%s'%(label, visexts, ';'.join(exts)))


wc_list.insert(0, '%s|%s'%(_('All files')+' (*.*)', '*.*'))
wc_list.insert(0, '%s|%s'%(_("All suppported files"), ';'.join(tmp)))

dialog_wildcard = '|'.join(wc_list)
transparent = True
version = "0.39.4"
languages = ( (_("English"), wx.LANGUAGE_ENGLISH),
              (_("English (United Kingdom)"), wx.LANGUAGE_ENGLISH_UK),
              (_("Japanese"), wx.LANGUAGE_JAPANESE),
              (_("Portugese"), wx.LANGUAGE_PORTUGUESE),
              (_("Dutch"), wx.LANGUAGE_DUTCH),
              (_("German"), wx.LANGUAGE_GERMAN),
              (_("Russian"), wx.LANGUAGE_RUSSIAN),
              (_("Arabic"), wx.LANGUAGE_ARABIC),
              (_("Hindi"), wx.LANGUAGE_HINDI),
              (_("Spanish"), wx.LANGUAGE_SPANISH),
              (_("French"), wx.LANGUAGE_FRENCH),
              (_("Welsh"), wx.LANGUAGE_WELSH),
              (_("Traditional Chinese"), wx.LANGUAGE_CHINESE_TRADITIONAL),
              (_("Czech"), wx.LANGUAGE_CZECH),
              (_("Italian"), wx.LANGUAGE_ITALIAN),
              (_("Galician"), wx.LANGUAGE_GALICIAN) )



config_scheme = """
bmp_select_transparent = boolean(default=False)
canvas_border = integer(min=10, max=35, default=15)
colour_grid = boolean(default=True)
colour1 = list(min=3, max=3, default=list('280', '0', '0'))
colour2 = list(min=3, max=3, default=list('255', '255', '0'))
colour3 = list(min=3, max=3, default=list('0', '255', '0'))
colour4 = list(min=3, max=3, default=list('255', '0', '0'))
colour5 = list(min=3, max=3, default=list('0', '0', '255'))
colour6 = list(min=3, max=3, default=list('160', '32', '240'))
colour7 = list(min=3, max=3, default=list('0', '255', '255'))
colour8 = list(min=3, max=3, default=list('255', '165', '0'))
colour9 = list(min=3, max=3, default=list('211', '211', '211'))
convert_quality = option('highest', 'high', 'normal', default='normal')
default_font = string
default_width = integer(min=1, max=12000, default=640)
default_height = integer(min=1, max=12000, default=480)
imagemagick_path = string
handle_size = integer(min=3, max=15, default=6)
language = option('English', 'English (United Kingdom)', 'Russian', 'Hindi', \
                  'Portugese', 'Japanese', 'French', 'Traditional Chinese',  \
                  'Dutch', 'German', 'Welsh', 'Spanish', 'Italian', 'Czech', \
                  'Galician', default='English')
print_title = boolean(default=True)
statusbar = boolean(default=True)
tool_preview = boolean(default=True)
toolbar = boolean(default=True)
toolbox = option('icon', 'text', default='icon')
toolbox_columns = option(2, 3, default=2)
undo_sheets = integer(min=5, max=50, default=10)
"""


translators = [
     'A. Emmanuel Mendoza https://launchpad.net/~a.emmanuelmendoza (Spanish)',
     'Alexey Reztsov https://launchpad.net/~ariafan (Russian)',
     '"Amy" https://launchpad.net/~anthropofobe (German)',
     '"Cheesewheel" https://launchpad.net/~wparker05 (Arabic)',
     'Cristian Asenjo https://launchpad.net/~apu2009 (Spanish)',
     'David Aller https://launchpad.net/~niclamus (Italian)',
     '"Dennis" https://launchpad.net/~dlinn83 (German)',
     'Diejo Lopez https://launchpad.net/~diegojromerolopez (Spanish)',
     'Federico Vera https://launchpad.net/~fedevera (Spanish)',
     'Fernando Muñoz https://launchpad.net/~munozferna (Spanish)',
     'Gonzalo Testa https://launchpad.net/~gonzalogtesta (Spanish)',
     'Javier Acuña Ditzel https://launchpad.net/~santoposmoderno (Spanish)',
     'James Maloy https://launchpad.net/~jamesmaloy (Spanish)',
     'John Y. Wu https://launchpad.net/~johnwuy (Traditional Chinese, Spanish)',
     '"Kuvaly" https://launchpad.net/~kuvaly (Czech)',
     '"Lauren" https://launchpad.net/~lewakefi (French)',
     'Lorenzo Baracchi https://launchpad.net/~baracchi-lorenzo (Italian)',
     'Medina https://launchpad.net/~medina-colpaca (Spanish)',
     'Miguel Anxo Bouzada https://launchpad.net/~mbouzada/ (Galician)',
     'Milan Jensen https://launchpad.net/~milanjansen (Dutch)',
     '"MixCool" https://launchpad.net/~mixcool (German)',
     'Nkolay Parukhin https://launchpad.net/~parukhin (Russian)',
     '"Pallas" https://launchpad.net/~v-launchpad-geekin-de (German)',
     '"pmkvodka" https://launchpad.net/~jazon23 (French)',
     '"Rarulis" https://launchpad.net/~rarulis (French)',
     'Roberto Bondi https://launchpad.net/~bondi (Italian)',
     '"RodriT" https://launchpad.net/~rodri316 (Spanish)',
     'Simon Junga https://launchpad.net/~simonthechipmunk (German)',
     '"SimonimNetz" https://launchpad.net/~s-marquardt (German)',
     'Steven Sproat https://launchpad.net/~sproaty (Welsh, misc.)',
     '"Tobberoth" https://launchpad.net/~tobberoth (Japanese)',
     'Tobias Baldauf https://launchpad.net/~technopagan (German)',
     '"tjalling" https://launchpad.net/~tjalling-taikie (Dutch)',
     '"ucnj" https://launchpad.net/~ucn (German)',
     '"Vonlist" https://launchpad.net/~hengartt (Spanish)',
     'Will https://launchpad.net/~willbickerstaff (UK English)',
     'Wouter van Dijke https://launchpad.net/~woutervandijke (Dutch)']


def find_transparent():
    """Has to be called by the GUI"""
    global transparent
    transparent = transparent_supported()