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


from lib.BeautifulSoup import BeautifulSoup
from lib.soupselect import select
import urllib
import re
from pprint import pprint


print ''
results = []

class DownloadCount(object):
    def __init__(self, website, count):
        self.website = website
        if isinstance(count, str):
            count = count.replace(",", "")
        self.count = int(count)
        print " {0:<25} {1:5,}".format(website, self.count)

def add_download(name, count):
    global results
    results.append(DownloadCount(name, count))

def get_soup(site, cssSelector=None):
    try:
        f = urllib.urlopen(site)
    except IOError:
        print "error connecting to site " + site
        exit()

    html = f.read()
    f.close()
    soup = BeautifulSoup(html)
    if not cssSelector:
        return soup
    return select(soup, cssSelector)


#---------------------------------------------------------------


soup = get_soup("http://code.google.com/p/whyteboard/downloads/list?can=1&q=&colspec=Filename+Summary+Uploaded+Size+DownloadCount")

val = 0
for i, td in enumerate(soup.findAll("td", {"class": "vt col_4"})):
    val += int(td.findNext('a').renderContents().strip().replace(",", ""))

add_download('Google Code', val)


#----------------------------------------------------------------------


soup = get_soup("https://launchpad.net/whyteboard/+download")

launchpad = 0
for i, td in enumerate(soup.findAll("td", {"style": "border: none; text-align: center;"})):
    x = int(td.string.strip().replace(",", ""))
    launchpad += x
    val += x

add_download('Launchpad', launchpad)


#----------------------------------------------------------------------


soup = get_soup("http://sourceforge.net/project/stats/detail.php?group_id=259193&ugn=whyteboard&type=prdownload&mode=alltime",
                'div#doc4 div table td')

sourceforge = soup[len(soup) - 2].renderContents().strip()

add_download('SourceForge', sourceforge)


#----------------------------------------------------------------------


soup = get_soup("http://linux.softpedia.com/get/Multimedia/Graphics/Whyteboard-45071.shtml",
                'table#dhead td table.margin_left25px td strong')

softpedia_linux = soup[1].renderContents()

add_download('Softpedia Linux', softpedia_linux)


#----------------------------------------------------------------------


soup = get_soup("http://www.softpedia.com/get/Multimedia/Graphic/Graphic-Editors/Whyteboard.shtml",
                'table#dhead td table.margin_left25px td strong')

softpedia_windows = soup[1].renderContents()

add_download('Softpedia Windows', softpedia_windows)


#----------------------------------------------------------------------


soup = get_soup("http://mac.softpedia.com/get/Graphics/Whyteboard.shtml",
                'table#dhead td table.margin_left25px td strong')

softpedia_mac = soup[1].renderContents()

add_download('Softpedia Mac', softpedia_mac)


#----------------------------------------------------------------------


soup = get_soup("http://www.softpedia.com/get/PORTABLE-SOFTWARE/Multimedia/Graphics/Portable-Whyteboard.shtml",
                'table#dhead td table.margin_left25px td strong')

softpedia_portable = soup[1].renderContents()

add_download('Softpedia Portable', softpedia_portable)


#----------------------------------------------------------------------


soup = get_soup("http://www.computerbild.de/download/Whyteboard-6107832.html",
                'div.contentPage div.user div.content div.clearfix table tbody tr td')

m = re.search('(\d{3})', soup[6].renderContents().strip())

computerbild = m.group(0)


add_download('computerbild.de', computerbild)


#----------------------------------------------------------------------



soup = get_soup("http://www.icewalkers.com/download/Whyteboard/3749/adl/",
                'table.corptable2 td.corptd tr td div')

m = re.search('(\d{3})', soup[1].renderContents().strip())
icewalkers = m.group(0)


add_download('Icewalkers', icewalkers)


#----------------------------------------------------------------------


soup = get_soup("http://www.windows7download.com/win7-portable-whyteboard/snyghjgi.html",
                'div.box_white_summary_body td')

m = re.search('(\d{2})', soup[4].renderContents().strip())
windows7downloads = m.group(0)

add_download('windows7downloads.com', windows7downloads)


#----------------------------------------------------------------------


soup = get_soup("http://www.downloadplex.com/tags/whyteboard/Page-1-0-0-0-0.html",
                'div#ja-content div.ja-innerpad table#dl-tbl-list tbody tr.ylw td.count div.resultCount strong')

downloadplex = soup[0].renderContents()

add_download('downloadplex', downloadplex)


#----------------------------------------------------------------------


soup = get_soup("http://www.chip.de/downloads/Whyteboard-fuer-Linux_48294121.html",
                'div.dl-faktbox div.dl-faktbox-row p.col2')

m = re.search('(\d{3})', soup[2].renderContents().strip())
chip = m.group(0)

add_download('chip.de Linux', chip)


#----------------------------------------------------------------------


soup = get_soup("http://www.chip.de/downloads/Whyteboard_48251314.html",
                'div.dl-faktbox div.dl-faktbox-row p.col2')

m = re.search('(\d{4})', soup[2].renderContents().strip().replace(".", ""))
chip = m.group(0)

add_download('chip.de Windows', chip)


#----------------------------------------------------------------------


soup = get_soup("http://www.brothersoft.com/whyteboard-295735.html",
                'div.sever_m div.Sever1')


m = re.search('(\d{2})', soup[1].renderContents().strip())
brothersoft = m.group(0)

add_download('Brothersoft', brothersoft)


#----------------------------------------------------------------------


soup = get_soup("http://download.html.it/software/vedi/11171/whyteboard/",
                'table.software-info tbody tr td')

italian = soup[2].renderContents()

add_download('download.html.it', italian)


#----------------------------------------------------------------------


total = 0
for download in results:
    total += download.count

print '%25s ------' % " "
print '{0:<25} {1:,}'.format(" Total", total)

raw_input() # so window doesn't close when run from file explorer