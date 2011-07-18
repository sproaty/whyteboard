#!/usr/bin/env python

# needs:
# - http://www.crummy.com/software/BeautifulSoup/
# - http://code.google.com/p/soupselect/


from BeautifulSoup import BeautifulSoup
from soupselect import select
import urllib
import re
from pprint import pprint


print ''
results = []

class DownloadCount(object):
    def __init__(self, website, count):
        self.website = website
        self.count = int(count)
        print " {0:<25} {1:5,}".format(website, self.count)


def get_soup(site):
    try:
        f = urllib.urlopen(site)
    except IOError:
        print "error connecting to site " + site
        exit()

    html = f.read()
    f.close()
    return BeautifulSoup(html)


#----------------------------------------------------------------------


soup = get_soup("http://code.google.com/p/whyteboard/downloads/list?can=1&q=&colspec=Filename+Summary+Uploaded+Size+DownloadCount")

val = 0
for i, td in enumerate(soup.findAll("td", {"class": "vt col_4"})):
    val += int(td.findNext('a').renderContents().strip())

results.append(DownloadCount('Google Code', val))


#----------------------------------------------------------------------


soup = get_soup("https://launchpad.net/whyteboard/+download")

launchpad = 0
for i, td in enumerate(soup.findAll("td", {"style": "border: none; text-align: center;"})):
    x = int(td.string.strip().replace(",", ""))
    launchpad += x
    val += x

results.append(DownloadCount('Launchpad', launchpad))


#----------------------------------------------------------------------


soup = get_soup("http://sourceforge.net/project/stats/detail.php?group_id=259193&ugn=whyteboard&type=prdownload&mode=alltime")

table_contents = select(soup, 'div#doc4 div table td')

sourceforge = table_contents[len(table_contents) - 2].renderContents().strip().replace(",", "")

results.append(DownloadCount('SourceForge', sourceforge))


#----------------------------------------------------------------------


soup = get_soup("http://linux.softpedia.com/get/Multimedia/Graphics/Whyteboard-45071.shtml")

x = select(soup, 'table#dhead td table.margin_left25px td strong')

softpedia_linux = x[1].renderContents().replace(",", "")

results.append(DownloadCount('Softpedia Linux', softpedia_linux))


#----------------------------------------------------------------------


soup = get_soup("http://www.softpedia.com/get/Multimedia/Graphic/Graphic-Editors/Whyteboard.shtml")

x = select(soup, 'table#dhead td table.margin_left25px td strong')

softpedia_windows = x[1].renderContents().replace(",", "")

results.append(DownloadCount('Softpedia Windows', softpedia_windows))


#----------------------------------------------------------------------


soup = get_soup("http://mac.softpedia.com/get/Graphics/Whyteboard.shtml")

x = select(soup, 'table#dhead td table.margin_left25px td strong')

softpedia_mac = x[1].renderContents().replace(",", "")

results.append(DownloadCount('Softpedia Mac', softpedia_mac))


#----------------------------------------------------------------------


soup = get_soup("http://www.softpedia.com/get/PORTABLE-SOFTWARE/Multimedia/Graphics/Portable-Whyteboard.shtml")

x = select(soup, 'table#dhead td table.margin_left25px td strong')

softpedia_portable = x[1].renderContents().replace(",", "")

results.append(DownloadCount('Softpedia Portable', softpedia_portable))


#----------------------------------------------------------------------


soup = get_soup("http://www.computerbild.de/download/Whyteboard-6107832.html")

x = select(soup, 'div.contentPage div.user div.content div.clearfix table tbody tr td')

m = re.search('(\d{3})', x[6].renderContents().strip())

computerbild = m.group(0)


results.append(DownloadCount('computerbild.de', computerbild))


#----------------------------------------------------------------------



soup = get_soup("http://www.icewalkers.com/download/Whyteboard/3749/adl/")

x = select(soup, 'table.corptable2 td.corptd tr td div')

m = re.search('(\d{3})', x[1].renderContents().strip())
icewalkers = m.group(0)


results.append(DownloadCount('Icewalkers', icewalkers))


#----------------------------------------------------------------------


soup = get_soup("http://www.windows7download.com/win7-portable-whyteboard/snyghjgi.html")

x = select(soup, 'div.box_white_summary_body td')

m = re.search('(\d{2})', x[4].renderContents().strip())
windows7downloads = m.group(0)

results.append(DownloadCount('windows7downloads.com', windows7downloads))


#----------------------------------------------------------------------


soup = get_soup("http://www.downloadplex.com/tags/whyteboard/Page-1-0-0-0-0.html")

x = select(soup, 'div#ja-content div.ja-innerpad table#dl-tbl-list tbody tr.ylw td.count div.resultCount strong')

downloadplex = x[0].renderContents()

results.append(DownloadCount('downloadplex', downloadplex))


#----------------------------------------------------------------------


soup = get_soup("http://www.chip.de/downloads/Whyteboard-fuer-Linux_48294121.html")

x = select(soup, 'div.dl-faktbox div.dl-faktbox-row p.col2')

m = re.search('(\d{3})', x[2].renderContents().strip())
chip = m.group(0)

results.append(DownloadCount('chip.de Linux', chip))


#----------------------------------------------------------------------


soup = get_soup("http://www.chip.de/downloads/Whyteboard_48251314.html")

x = select(soup, 'div.dl-faktbox div.dl-faktbox-row p.col2')

m = re.search('(\d{4})', x[2].renderContents().strip().replace(".", ""))
chip = m.group(0)

results.append(DownloadCount('chip.de Windows', chip))


#----------------------------------------------------------------------


soup = get_soup("http://www.brothersoft.com/whyteboard-295735.html")

x = select(soup, 'div.sever_m div.Sever1')


m = re.search('(\d{2})', x[1].renderContents().strip())
brothersoft = m.group(0)

results.append(DownloadCount('Brothersoft', brothersoft))


#----------------------------------------------------------------------


soup = get_soup("http://download.html.it/software/vedi/11171/whyteboard/")

x = select(soup, 'table.software-info tbody tr td')

italian = x[2].renderContents()

results.append(DownloadCount('download.html.it', italian))


#----------------------------------------------------------------------


total = 0
for download in results:
    total += download.count

print '%25s ------' % " "
print '{0:<25} {1:,}'.format(" Total", total)