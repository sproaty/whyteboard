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
Contains meta data for the program, such as version, whether transparency is
supported, language mappings, translator credits
All attributes are global, but this module will always be imported, and can be
used as a class in a way. There's simply *no need* to make it a class

The function find_transparency is called from the GUI upon its creation,
instead of before the GUI is created because wx must first initialise its
App object before allowing DC operations
"""

import wx
from whyteboard.misc import transparent_supported

_ = wx.GetTranslation

#----------------------------------------------------------------------

version = u"0.42"
transparent = True


def find_transparent():
    """Has to be called by the GUI"""
    global transparent
    transparent = transparent_supported()
    
    
def define_languages():
    return (
            (u"Arabic", _("Arabic"), wx.LANGUAGE_ARABIC),
            (u"Catalan", _("Catalan"), wx.LANGUAGE_CATALAN),
            (u"Chinese (Traditional)", _("Chinese (Traditional)"), wx.LANGUAGE_CHINESE_TRADITIONAL),
            (u"Czech", _("Czech"), wx.LANGUAGE_CZECH),
            (u"Dutch", _("Dutch"), wx.LANGUAGE_DUTCH),
            (u"English", _("English"), wx.LANGUAGE_ENGLISH),
            (u"English (U.K.)", _("English (U.K.)"), wx.LANGUAGE_ENGLISH_UK),
            (u"French", _("French"), wx.LANGUAGE_FRENCH),
            (u"Galician", _("Galician"), wx.LANGUAGE_GALICIAN),
            (u"German", _("German"), wx.LANGUAGE_GERMAN),
            (u"Hindi", _("Hindi"), wx.LANGUAGE_HINDI),
            (u"Italian", _("Italian"), wx.LANGUAGE_ITALIAN),
            (u"Japanese", _("Japanese"), wx.LANGUAGE_JAPANESE),
            (u"Korean", _("Korean"), wx.LANGUAGE_KOREAN),
            (u"Occitan (post 1500)", _("Occitan (post 1500)"), wx.LANGUAGE_OCCITAN),
            (u"Portuguese", _("Portuguese"), wx.LANGUAGE_PORTUGUESE),
            (u"Russian", _("Russian"), wx.LANGUAGE_RUSSIAN),
            (u"Slovak", _("Slovak"), wx.LANGUAGE_SLOVAK),
            (u"Spanish", _("Spanish"), wx.LANGUAGE_SPANISH),
            (u"Swedish", _("Swedish"), wx.LANGUAGE_SWEDISH),
            (u"Turkish", _("Turkish"), wx.LANGUAGE_TURKISH),
            (u"Welsh", _("Welsh"), wx.LANGUAGE_WELSH),
           )

def define_filetypes():
    # Creates a wxPython wildcard filter from a list of known/supported filetypes.
    _all = [ (_('PDF/PS/SVG'), [u'ps', u'pdf', u'svg']),
            (_('Image Files'), [u"jpeg", u"jpg", u"png", u"tiff", u"bmp", u"pcx"]),
            (_('Whyteboard files'), [u'wtbd']) ]

    wc_list, types, tmp = [], [], []

    for label, exts in _all:
        [types.append(x) for x in exts]
        exts = [u'*.%s' % a for a in exts]
        visexts = u', '.join(exts)

        exts.extend([e.upper() for e in exts])
        tmp.extend(exts)
        [types.append(x.replace(u"*.", u"")) for x in exts]
        wc_list.append(u'%s (%s)|%s' % (label, visexts, u';'.join(exts)))

    wc_list.insert(0, u'%s|%s' % (_('All files') + u' (*.*)', u'*.*'))
    wc_list.insert(0, u'%s|%s' % (_("All suppported files"), u';'.join(tmp)))

    return (types, u'|'.join(wc_list))


languages = define_languages()
types, dialog_wildcard = define_filetypes()

_langs = "'%s'" % "', '".join(str(x[0]) for x in languages)

config_scheme = """
bmp_select_transparent = boolean(default=False)
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
language = option(""" + _langs + """, default='English')
last_opened_dir = string
print_title = boolean(default=True)
statusbar = boolean(default=True)
tool_preview = boolean(default=True)
toolbar = boolean(default=True)
"""
config_scheme = config_scheme.split("\n")

translators = [
     u'A. Emmanuel Mendoza https://launchpad.net/~a.emmanuelmendoza (Spanish)',
     u'Alexander \'FONTER\' Zinin https://launchpad.net/~spore-09 (Russian)',
     u'Alexey Reztsov https://launchpad.net/~ariafan (Russian)',
     u'Aljosha Papsch https://launchpad.net/~joschi-papsch (German)',
     u'Almufadado https://launchpad.net/~almufadado (Portuguese)',
     u'Amy https://launchpad.net/~anthropofobe (German)',
     u'Antoine Jouve https://launchpad.net/~aj94tj (French)',
     u'Ash https://launchpad.net/~barzogh (French)',
     u'Auduf https://launchpad.net/~5097-mail (Russian)',
     u'Billy Robshaw https://launchpad.net/~billyrobshaw (Spanish)',
     u'Brian Hahn https://launchpad.net/~thetriggerer (Korean)',
     u'Cédric VALMARY (Tot en òc) https://launchpad.net/~cvalmary (Occitan)',
     u'Cheesewheel https://launchpad.net/~wparker05 (Arabic)',
     u'cmdrhenner https://launchpad.net/~cmdrhenner (German)',
     u'Cristian Asenjo https://launchpad.net/~apu2009 (Spanish)',
     u'David https://launchpad.net/~3-admin-dav1d-de (German)',
     u'David Aller https://launchpad.net/~niclamus (Italian)',
     u'Dennis https://launchpad.net/~dlinn83 (German)',
     u'Diejo Lopez https://launchpad.net/~diegojromerolopez (Spanish)',
     u'Donkade https://launchpad.net/~donkade (Dutch)',
     u'Fabian Riechsteiner https://launchpad.net/~ruffy91-gmail (German)',
     u'Federico Vera https://launchpad.net/~fedevera (Spanish)',
     u'Fernando Muñoz https://launchpad.net/~munozferna (Spanish)',
     u'Fido https://launchpad.net/~fedevera (Spanish)',
     u'Fitoschido https://launchpad.net/~fitoschido (Spanish)',
     u'fgp https://launchpad.net/~komakino (Spanish)',
     u'Gonzalo Testa https://launchpad.net/~gonzalogtesta (Spanish)',
     u'Hugh Man https://launchpad.net/~marsalien (Dutch)',
     u'Hiroshi Tagawa https://launchpad.net/~kuponuga (Japanese)',
     u'Javier Acuña Ditzel https://launchpad.net/~santoposmoderno (Spanish)',
     u'James Maloy https://launchpad.net/~jamesmaloy (Spanish)',
     u'Jean-Philippe Fleury https://launchpad.net/~jpfle (French)',
     u'John https://launchpad.net/~gobbler85 (Swedish)',
     u'John Y. Wu https://launchpad.net/~johnwuy (Traditional Chinese, Spanish)',
     u'kentxchang https://launchpad.net/~kentxchang (Traditional Chinese)',
     u'Kuvaly https://launchpad.net/~kuvaly (Czech)',
     u'Lauren https://launchpad.net/~lewakefi (French)',
     u'LoReNicolò https://launchpad.net/~god121-p-l (Italian)',
     u'Lorenzo Baracchi https://launchpad.net/~baracchi-lorenzo (Italian)',
     u'Lukáš Machyán https://launchpad.net/~phobulos (Czech)',
     u'Marcel Schmücker https://launchpad.net/~versus666 (German)',
     u'Martino Barbon https://launchpad.net/~martins999 (Italian)',
     u'melvinor https://launchpad.net/~aka-melv (Russian)',
     u'Medina https://launchpad.net/~medina-colpaca (Spanish)',
     u'Miguel Anxo Bouzada https://launchpad.net/~mbouzada/ (Galician)',
     u'Miquel Escarrà https://launchpad.net/~quelet (Catalan)',
     u'Milan Jensen https://launchpad.net/~milanjansen (Dutch)',
     u'MixCool https://launchpad.net/~mixcool (German)',
     u'nafergo https://launchpad.net/~nafergo (Portuguese)',
     u'Nicolas Delvaux https://launchpad.net/~malaria (French)',
     u'Nkolay Parukhin https://launchpad.net/~parukhin (Russian)',
     u'Pallas https://launchpad.net/~v-launchpad-geekin-de (German)',
     u'Papazu https://launchpad.net/~pavel-z (Russian)',
     u'pmkvodka https://launchpad.net/~jazon23 (French)',
     u'pygmee https://launchpad.net/~pygmee (French)',
     u'Rarulis https://launchpad.net/~rarulis (French)',
     u'Quentin Pagès https://launchpad.net/~kwentin (Spanish)',
     u'Roberto Bondi https://launchpad.net/~bondi (Italian)',
     u'RodriT https://launchpad.net/~rodri316 (Spanish)',
     u'Sergey Sedov https://launchpad.net/~serg-sedov (Russian)',
     u'Sérgio Marques https://launchpad.net/~sergio+marques (Portuguese)',
     u'simone.sandri https://launchpad.net/~lexluxsox (Italian)',
     u'Simon Junga https://launchpad.net/~simonthechipmunk (German)',
     u'SimonimNetz https://launchpad.net/~s-marquardt (German)',
     u'SpaceCafé https://launchpad.net/~spacecafe (German)',
     u'Stanislas Michalak https://launchpad.net/~stanislas-michalak-live (French)',
     u'Steven Sproat https://launchpad.net/~sproaty (Welsh, misc.)',
     u'Thibault Févry https://launchpad.net/~thibaultfevry (French)',
     u'tjalling https://launchpad.net/~tjalling-taikie (Dutch)',
     u'Tobberoth https://launchpad.net/~tobberoth (Japanese)',
     u'Tobias Baldauf https://launchpad.net/~technopagan (German)',
     u'Tubuntu https://launchpad.net/~t-ubuntu (French)',
     u'ucnj https://launchpad.net/~ucn (German)',
     u'VonlisT https://launchpad.net/~hengartt (Spanish)',
     u'Will https://launchpad.net/~willbickerstaff (UK English)',
     u'Wouter van Dijke https://launchpad.net/~woutervandijke (Dutch)',
     u'xemard.nicolas https://launchpad.net/~xemard.nicolas (French)']