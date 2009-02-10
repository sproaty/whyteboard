#!/usr/bin/python

"""
This module implements the Whteboard application.  It takes a Whyteboard class
and wraps it in a GUI with a menu/toolbar/statusbar; can save and load drawings,
clear the workspace, undo, redo, a simple history "replayer", allowing you to
have a replay of what you have drawn played back to you.

Also on the GUI is a panel for setting color and line thickness, with an
indicator that shows an example of the drawing-to-be
"""

import os

import wx

from whyteboard import Whyteboard
from utility import Utility
from about import About
from history import History


#----------------------------------------------------------------------

ID_HISTORY = wx.NewId()
ID_CLEAR_ALL = wx.NewId()

class GUI(wx.Frame):
    """
    This class ontains a Whyteboard panel, a ControlPanel and manages
    their layout with a wx.BoxSizer.  A menu, toolbar and associated event
    handlers call the appropriate functions of other classes.
    """
    title = "Whyteboard"

    def __init__(self, parent):
        wx.Frame.__init__(self, parent, size=(800, 600), title="Untitled - " +
           self.title, style=wx.DEFAULT_FRAME_STYLE | wx.FULL_REPAINT_ON_RESIZE)

        self.util = Utility(self)
        self.CreateStatusBar()
        self.make_toolbar()
        self.make_menu()
        self.tab_count = 1  # instead of typing self.tabs.GetPageCount()

        self.tabs = wx.Notebook(self)
        self.board = Whyteboard(self.tabs)  # the active whiteboard tab
        self.tabs.AddPage(self.board, "Untitled 1")
        self.control = ControlPanel(self)

        self.do_bindings()

        box = wx.BoxSizer(wx.HORIZONTAL)  # position windows side-by-side
        box.Add(self.control, 0, wx.EXPAND)
        box.Add(self.tabs, 2, wx.EXPAND)
        self.SetSizer(box)


    def make_menu(self):
        """
        Creates the menu...
        """
        _file = wx.Menu()
        edit = wx.Menu()
        image = wx.Menu()
        _help = wx.Menu()
        menuBar = wx.MenuBar()

        _file.Append(wx.ID_NEW, "New &Tab\tCtrl-T", "Open a new tab")
        _file.Append(wx.ID_OPEN, "&Open\tCtrl-O", "Open an existing Whyteboard \
                                                   file")
        _file.Append(wx.ID_SAVE, "&Save\tCtrl-S", "Save the Whyteboard data")
        _file.Append(wx.ID_SAVEAS, "Save &As...\tCtrl-Shift-S", "Save the \
                                                Whyteboard data in a new file")
        _file.AppendSeparator()
        _file.Append(wx.ID_CLOSE, "&Close Tab\tCtrl-W", "Close current tab")
        _file.Append(wx.ID_EXIT, "E&xit\tAlt-F4", "Terminate Whyteboard")
        edit.Append(wx.ID_UNDO, "&Undo\tCtrl-Z", "Undo the last operation")
        edit.Append(wx.ID_REDO, "&Redo\tCtrl-Y", "Redo the last operation")
        edit.Append(ID_HISTORY, "&History Viewer\tCtrl-H", "View and replay \
                                                      your drawing history")
        image.Append(wx.ID_CLEAR, "&Clear\tCtrl-C", "Clear the current tab's \
                                                      drawing")
        image.Append(ID_CLEAR_ALL, "Clear &All\tCtrl-Shift-C", "Clear all \
                                                        drawings in all tabs" )
        _help.Append(wx.ID_ABOUT, "&About\tF1", "View information about the \
                                                Whyteboard application")

        menuBar.Append(_file, "&File")
        menuBar.Append(edit, "&Edit")
        menuBar.Append(image, "&Image")
        menuBar.Append(_help, "&Help")
        self.SetMenuBar(menuBar)


    def do_bindings(self):
        """
        Performs event binding.
        """
        self.Bind(wx.EVT_CLOSE, self.on_exit)
        self.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.on_change_tab, self.tabs)

        functs = ["new_tab", "close_tab", "open", "save", "save_as", "undo",
                  "redo", "history", "clear", "clear_all", "about", "exit"]

        IDs = [wx.ID_NEW, wx.ID_CLOSE, wx.ID_OPEN, wx.ID_SAVE, wx.ID_SAVEAS,
               wx.ID_UNDO, wx.ID_REDO, ID_HISTORY, wx.ID_CLEAR,
               ID_CLEAR_ALL, wx.ID_ABOUT, wx.ID_EXIT]

        for name, _id in zip(functs, IDs):
            method = getattr(self, 'on_%s' % name, None)  # self.on_*
            self.Bind(wx.EVT_MENU, method, id=_id )


    def make_toolbar(self):
        """
        Creates a toolbar, Pythonically :D
        """
        self.tb = self.CreateToolBar()

        ids = [wx.ID_NEW, wx.ID_OPEN, wx.ID_SAVE, wx.ID_UNDO, wx.ID_REDO]
        arts = [wx.ART_NEW, wx.ART_FILE_OPEN, wx.ART_FILE_SAVE, wx.ART_UNDO,
                wx.ART_REDO]
        tips = ["New Tab", "Open a File", "Save Drawing", "Undo Action",
                "Redo the Undone Action"]

        for _id, art_id, tip in zip(ids, arts, tips):
            art = wx.ArtProvider.GetBitmap(art_id, wx.ART_TOOLBAR)
            self.tb.AddSimpleTool(_id, art, tip)
        self.tb.Realize()

#--------------------------------------------------------------


    def on_save(self, event=None):
        if not self.util.filename:  # if no wtbd file is active, prompt for one
            self.on_save_as()
        else:
            self.util.save_file()


    def on_open(self, event=None):
        """
        Opens a file, sets Utility's temp. file to the chosen one and
        """
        dlg = wx.FileDialog(self, "Open file...", os.getcwd(),
                            style=wx.OPEN, wildcard = self.util.wildcard)

        if dlg.ShowModal() == wx.ID_OK:
            name = dlg.GetPath()

            if name.endswith("wtbd"):
                self.util.filename = name

            self.util.temp_file = name
            self.util.load_file()
        dlg.Destroy()


    def on_save_as(self, event=None):
        """
        Checks if there's any drawing data to save, otherwise prompts for the
        filename and location to save.
        """
        save = False

        for board in range (0, self.tab_count):
            if self.tabs.GetPage(board).shapes:
                save = True

        if save == False:
            wx.MessageBox("No image data to save", "Save error")
        else:
            dlg = wx.FileDialog(self, "Save Whyteboard As...", os.getcwd(),
                    style=wx.SAVE | wx.OVERWRITE_PROMPT,
                    wildcard = "Whyteboard file (*.wtbd)|*.wtbd")
            if dlg.ShowModal() == wx.ID_OK:
                filename = dlg.GetPath()
                if not os.path.splitext(filename)[1]:  # no file extension
                    filename = filename + '.wtbd'

                # only store whyteboard files, not an image as the current file
                if filename.endswith(".wtbd"):
                    self.util.filename = filename
                    self.on_save()

                self.SetTitle(os.path.split(filename)[1] + ' - ' +  self.title)
            dlg.Destroy()


    def on_new_tab(self, event=None):
        """
        Opens a new tab and selects it
        """
        wb = Whyteboard(self.tabs)
        self.tabs.AddPage(wb, "Untitled "+ str(self.tab_count + 1) )
        self.tab_count += 1
        self.tabs.SetSelection(self.tab_count - 1 )  # fires on_change_tab

    def on_change_tab(self, event=None):
        """
        Sets the GUI's board attribute to be the selected Whyteboard.
        """
        self.board = self.tabs.GetCurrentPage()
        self.control.change_tool(_id=self.control.toggled)


    def on_close_tab(self, event=None):
        """
        Closes the current tab (if there are any to close).
        """
        if self.tab_count is not 0:
            self.tabs.RemovePage( self.tabs.GetSelection() )
            self.tab_count -= 1

    def on_exit(self, event=None):
        """
        Clean up any tmp files from PDF/PS conversion.
        """
        self.util.cleanup()
        self.Destroy()


    def on_undo(self, event=None):
        self.board.undo()

    def on_redo(self, event=None):
        self.board.redo()

    def on_clear(self, event=None):
        self.board.clear()

    def on_clear_all(self, event=None):
        self.board.clear()

    def on_about(self, event=None):
        dlg = About(self)
        dlg.ShowModal()
        dlg.Destroy()

    def on_history(self, event=None):
        dlg = History(self, self.board)
        dlg.ShowModal()
        dlg.Destroy()


#----------------------------------------------------------------------


class ControlPanel(wx.Panel):
    """
    This class implements a control panel for the GUI. It creates buttons for
    each tool that can be drawn upon the Whyteboard, a drop-down menu for the
    line thickness and a ColourPicker for choosing the drawing colour. A preview
    of what the tool will look like is also shown.
    """
    def __init__(self, gui):
        wx.Panel.__init__(self, gui)

        self.gui = gui
        self.toggled = 1  # Pen initallly
        self.ci = ColourIndicator(self.gui)


        self.tools  = {}
        sizer = wx.GridSizer(cols=1, hgap=1, vgap=2)

        # Get list of class names as strings for each drawable tool
        items = [str(i.__name__) for i in gui.util.items]

        for x, name in enumerate(items):
            b = wx.ToggleButton(self, x + 1, name)
            b.Bind(wx.EVT_TOGGLEBUTTON, self.change_tool, id=x + 1)
            sizer.Add(b, 0)
            self.tools[x + 1] = b

        self.tools[self.toggled].SetValue(True)
        spacing = 4

        self.colour = wx.ColourPickerCtrl(self)
        self.colour.Bind(wx.EVT_COLOURPICKER_CHANGED, self.change_colour)

        choices = ''.join(str(i) + " " for i in range(1, 26) ).split()

        self.thickness = wx.ComboBox(self, choices=choices, size=(25, 25),
                                        style=wx.CB_READONLY)
        self.thickness.SetSelection(0)
        self.thickness.Bind(wx.EVT_COMBOBOX, self.change_thickness)

        box = wx.BoxSizer(wx.VERTICAL)
        box.Add(sizer, 0, wx.ALL, spacing)
        box.Add(self.colour, 0, wx.EXPAND | wx.ALL, spacing)
        box.Add(self.thickness, 0, wx.EXPAND | wx.ALL, spacing)
        box.Add(self.ci, 0, wx.EXPAND | wx.ALL, spacing)
        self.SetSizer(box)
        self.SetAutoLayout(True)
        box.Fit(self)


    def change_tool(self, event=None, _id=None):
        """
        Toggles the tool buttons on/off and calls select_tool on the drawing
        panel.
        """
        if event:
            new = int(event.GetId() )  # get widget ID (set in method above)
        elif _id:
            new = _id

        if new != self.toggled:  # toggle old button
            self.tools[self.toggled].SetValue(False)
        else:
            self.tools[self.toggled].SetValue(True)

        self.toggled = new
        self.gui.board.select_tool(new)


    def change_colour(self, event=None):
        self.gui.util.colour = event.GetColour()
        self.gui.board.select_tool(self.gui.util.tool)
        self.ci.Refresh()

    def change_thickness(self, event=None):
        self.gui.util.thickness = event.GetSelection()
        self.gui.board.select_tool(self.gui.util.tool)
        self.ci.Refresh()

#----------------------------------------------------------------------


class ColourIndicator(wx.Window):
    """
    An instance of this class is used on the ControlPanel to show
    a sample of what the current tool will look like.
    """
    def __init__(self, gui):
        wx.Window.__init__(self, gui, style=wx.RAISED_BORDER)
        self.gui = gui
        self.SetBackgroundColour(wx.WHITE)
        self.SetSize((45, 45))
        self.Bind(wx.EVT_PAINT, self.paint)


    def paint(self, event=None):
        """
        Draws the tool inside the box when tool/colour/thickness
        is changed
        """
        dc = wx.PaintDC(self)
        pen = wx.Pen(self.gui.util.colour, self.gui.util.thickness)
        dc.SetPen(pen)
        width, height = self.GetClientSize()
        dc.DrawLine(10, height / 2, width - 10, height / 2)


#----------------------------------------------------------------------


class WhyteboardApp(wx.App):
    def OnInit(self):
        frame = GUI(None)
        frame.Show(True)
        return True

#----------------------------------------------------------------------


if __name__ == '__main__':
    app = WhyteboardApp(True)
    app.MainLoop()
