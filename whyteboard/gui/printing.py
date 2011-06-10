#! /usr/bin/env python
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
Print-related classes
"""

import copy
import logging
import wx

from whyteboard.tools import Highlighter


_ = wx.GetTranslation
logger = logging.getLogger("whyteboard.print")

#----------------------------------------------------------------------

class Print(object):
    def __init__(self, gui):
        self.gui = gui
        self.printData = wx.PrintData()
        self.printData.SetPaperId(wx.PAPER_LETTER)
        self.printData.SetPrintMode(wx.PRINT_MODE_PRINTER)


    def page_setup(self):
        psdd = wx.PageSetupDialogData(self.printData)
        psdd.CalculatePaperSizeFromId()
        dlg = wx.PageSetupDialog(self.gui, psdd)
        dlg.ShowModal()
        self.printData = wx.PrintData(dlg.GetPageSetupData().GetPrintData())
        dlg.Destroy()


    def print_preview(self):
        data = wx.PrintDialogData(self.printData)
        printout = PrintOut(self.gui)
        printout2 = PrintOut(self.gui)
        preview = wx.PrintPreview(printout, printout2, data)

        if not preview.Ok():
            wx.MessageBox(_("There was a problem printing.\nPerhaps your current printer is not set correctly?"),
              _("Printing Error"))
            return

        pfrm = wx.PreviewFrame(preview, self.gui, _("Print Preview"))
        pfrm.Initialize()
        pfrm.SetPosition(self.gui.GetPosition())
        pfrm.SetSize(self.gui.GetSize())
        pfrm.Show(True)


    def do_print(self):
        pdd = wx.PrintDialogData(self.printData)
        pdd.SetToPage(2)
        printer = wx.Printer(pdd)
        printout = PrintOut(self.gui)

        if not printer.Print(self.gui.canvas, printout, True):
            if printer.GetLastError() is not wx.PRINTER_CANCELLED:
                wx.MessageBox(_("There was a problem printing.\nPerhaps your current printer is not set correctly?"),
                              _("Printing Error"), wx.OK)
        else:
            self.printData = wx.PrintData(printer.GetPrintDialogData().GetPrintData())
        printout.Destroy()


#----------------------------------------------------------------------


class PrintOut(wx.Printout):
    def __init__(self, gui):
        title = _("Untitled")
        if gui.util.filename:
            title = gui.util.filename
        wx.Printout.__init__(self, title)
        self.gui = gui

    def OnBeginDocument(self, start, end):
        return super(PrintOut, self).OnBeginDocument(start, end)

    def OnEndDocument(self):
        super(PrintOut, self).OnEndDocument()

    def OnBeginPrinting(self):
        super(PrintOut, self).OnBeginPrinting()

    def OnEndPrinting(self):
        super(PrintOut, self).OnEndPrinting()

    def OnPreparePrinting(self):
        super(PrintOut, self).OnPreparePrinting()

    def HasPage(self, page):
        return page <= self.gui.tab_count

    def GetPageInfo(self):
        return (1, self.gui.tab_count, 1, self.gui.tab_count)

    def OnPrintPage(self, page):

        dc = self.GetDC()
        canvas = self.gui.tabs.GetPage(page - 1)
        canvas.deselect_shape()

        maxX = canvas.buffer.GetWidth()
        maxY = canvas.buffer.GetHeight()

        marginX = 50
        marginY = 50
        maxX = maxX + (2 * marginX)
        maxY = maxY + (2 * marginY)

        (w, h) = dc.GetSizeTuple()
        scaleX = float(w) / maxX
        scaleY = float(h) / maxY
        actualScale = min(scaleX, scaleY)
        posX = (w - (canvas.buffer.GetWidth() * actualScale)) / 2.0
        posY = (h - (canvas.buffer.GetHeight() * actualScale)) / 2.0

        dc.SetUserScale(actualScale, actualScale)
        dc.SetDeviceOrigin(int(posX), int(posY))
        dc.DrawText(_("Page:") + u" %d" % page, marginX / 2, maxY - marginY + 100)

        if self.gui.util.config['print_title']:
            filename = _("Untitled")
            if self.gui.util.filename:
                filename = self.gui.util.filename

            font = wx.SystemSettings_GetFont(wx.SYS_DEFAULT_GUI_FONT)
            dc.SetFont(font)
            dc.DrawText(_(filename), marginX / 2, -120)

        dc.SetDeviceOrigin(int(posX), int(posY))

        self.draw(canvas, dc)

        return True

    def draw(self, canvas, dc):
        """
        Due to a bug in wx 2.8, we must remove any highlighter tools
        as they cannot be printed due to the way the tool uses GraphicsContext
        http://trac.wxwidgets.org/ticket/11761
        """
        shapes = canvas.clone_shapes()

        for shape in canvas.shapes:
            if isinstance(shape, Highlighter):
                canvas.shapes.remove(shape)

        canvas.redraw_all(dc=dc)
        canvas.shapes = shapes