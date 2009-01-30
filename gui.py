#!/usr/bin/python

"""
This module implements the Superboard demo application.  It takes the
boardWindow previously presented and reuses it in a much more
intelligent Frame.  This one has a menu and a statusbar, is able to
save and reload boards, clear the workspace, and has a simple control
panel for setting color and line thickness in addition to the popup
menu that boardWindow provides.  There is also a nice About dialog
implmented using an wx.html.HtmlWindow.
"""

import os, cPickle, random, time, subprocess
import wx                  # This module uses the new wx namespace
import wx.html
from wx.lib import buttons # for generic button classes
import  wx.lib.colourselect as csel

from whiteboard import Whiteboard
from tools import Pen, Image





#----------------------------------------------------------------------

#wx.RegisterId(5000)  # Give a high starting value for the IDs, just for kicks

ID_HISTORY = wx.NewId()


class GUI(wx.Frame):
    """
    This class ontains a Whiteboard panel, a ControlPanel and manages
    their layout with a wx.BoxSizer.  A menu and associated event handlers
    provides for saving a board to a file, etc.
    """
    title = "Whyteboard"
    def __init__(self, parent):

        wx.Frame.__init__(self, parent, -1, "Untitled document - " + self.title,
        size=(800,600), style=wx.DEFAULT_FRAME_STYLE | wx.FULL_REPAINT_ON_RESIZE)

        self.CreateStatusBar()
        self.MakeMenu()
        self.filename = None
        self.board    = Whiteboard(self, -1)
        cPanel        = ControlPanel(self, -1, self.board)
        self.board.SelectTool(1)

        # Create a sizer to layout the two windows side-by-side.
        box = wx.BoxSizer(wx.HORIZONTAL)
        box.Add(cPanel, 0, wx.EXPAND)
        box.Add(self.board, 1, wx.EXPAND)

        # Tell the frame that it should layout itself in response to
        # size events using this sizer.
        self.SetSizer(box)


    def MakeMenu(self):
        """Creates the menu..."""
        file = wx.Menu()
        file.Append(wx.ID_NEW, "&New\tCtrl-N", "Create a new Whiteboard file")
        file.Append(wx.ID_OPEN, "&Open\tCtrl-O", "Open an existing Whiteboard file")
        file.Append(wx.ID_SAVE, "&Save\tCtrl-S", "Save the Whiteboard data")

        file.Append(wx.ID_SAVEAS, "Save &As\tShift-Ctrl-S", "Save the Whiteboard data in a new file")
        file.AppendSeparator()
        file.Append(wx.ID_EXIT, "E&xit\tCtrl-Q", "Terminate Whiteboard")

        edit = wx.Menu()
        edit.Append(wx.ID_UNDO, "&Undo\tCtrl-Z", "Undo the last operation")
        edit.Append(wx.ID_REDO, "&Redo\tCtrl-Y", "Redo the last operation")
        edit.Append(ID_HISTORY, "&History Viewer\tCtrl-H", "View and replay your drawing history")

        image = wx.Menu()
        image.Append(wx.ID_CLEAR, "&Clear", "Clear the current drawing")

        help = wx.Menu()
        help.Append(wx.ID_ABOUT, "&About\tF1", "View information about the Whiteboard application")

        menuBar = wx.MenuBar()
        menuBar.Append(file, "&File")
        menuBar.Append(edit, "&Edit")
        menuBar.Append(image, "&Image")
        menuBar.Append(help, "&Help")
        self.SetMenuBar(menuBar)

        self.Bind(wx.EVT_MENU, self.OnMenuOpen, id=wx.ID_OPEN)
        self.Bind(wx.EVT_MENU, self.OnMenuSave, id=wx.ID_SAVE)
        self.Bind(wx.EVT_MENU, self.OnMenuSaveAs, id=wx.ID_SAVEAS)
        self.Bind(wx.EVT_MENU, self.OnMenuUndo, id=wx.ID_UNDO)
        self.Bind(wx.EVT_MENU, self.OnMenuRedo, id=wx.ID_REDO)
        self.Bind(wx.EVT_MENU, self.OnMenuHistory, id=ID_HISTORY)
        self.Bind(wx.EVT_MENU, self.OnMenuClear, id=wx.ID_CLEAR)
        self.Bind(wx.EVT_MENU, self.OnMenuExit, id=wx.ID_EXIT)
        self.Bind(wx.EVT_MENU, self.OnMenuAbout, id=wx.ID_ABOUT)


###################################################


    def SaveFile(self):
        if self.filename:
                        #data = self.board.GetLinesData()
            temp = self.board.shapes

            if len(temp) > 0:      # don't load empty file
                for shape in temp: # iterate over the list, making each object's manager the *current* manager
                    shape.board = None

                f = open(self.filename, 'w')
                cPickle.dump(temp, f)
                f.close()


    def ReadFile(self):
        if self.filename:
            try:
                type = os.path.splitext(self.filename)[1] # access filetype

                if type[1:] in ["ps", "jpg", "jpeg", "png", "pdf"]:
                    self.Convert(type[1:])
                else:

                    temp = []
                    f = open(self.filename, 'r')
                    temp = cPickle.load(f)
                    f.close()

                    for shape in temp: # iterate over the list, making each object's manager the *current* manager
	                    shape.board = self.board

                    self.board.shapes = temp      # overwrite current shapes with loaded ones
                    self.SetTitle( os.path.split(self.filename)[1] + ' - ' +  self.title)

                self.board.reInitBuffer = True

            except cPickle.UnpicklingError:
                wx.MessageBox("%s is not a valid whiteboard file." % self.filename,
                             "oops!", style=wx.OK|wx.ICON_EXCLAMATION)

    def Convert(self, filetype):
        if filetype == "ps":
            os.system("convert " +self.filename+ " temp.jpg")
            image = wx.Bitmap("temp.jpg")
        elif filetype == "pdf":
            os.system("convert " +self.filename+ " temp.jpg")
            image = wx.Bitmap("temp-0.jpg")
        else:
            image = wx.Bitmap(self.filename)
        shape = Image(self.board, (0,0,0), 1)
        shape.button_down(50, 50, image)


    wildcard = "All files (*.*)|*.*|Whiteboard file (*.wtbd)|*.wtbd|Image Files (.jpg, .png, .gif, .ps, .pdf)|*.jpg;*.png;*.gif;*.ps;*.pdf"


    def OnMenuOpen(self, event):
        dlg = wx.FileDialog(self, "Open Whiteboard file...", os.getcwd(),
                           style=wx.OPEN, wildcard = self.wildcard)
        if dlg.ShowModal() == wx.ID_OK:
            self.filename = dlg.GetPath()
            self.ReadFile()
        dlg.Destroy()


    def OnMenuSave(self, event):
        if not self.filename:
            self.OnMenuSaveAs(event)
        else:
            self.SaveFile()


    def OnMenuSaveAs(self, event):
        if len(self.board.shapes) == 0:
            wx.MessageBox("No image data to save", "Save error", style=wx.OK)
        else:
            dlg = wx.FileDialog(self, "Save Whiteboard as...", os.getcwd(),
                               style=wx.SAVE | wx.OVERWRITE_PROMPT,
                               wildcard = "Whiteboard files (*.wtbd)|*.wtbd|All files (*.*)|*.*")
            if dlg.ShowModal() == wx.ID_OK:
                filename = dlg.GetPath()
                if not os.path.splitext(filename)[1]:
                    filename = filename + '.wtbd'
                self.filename = filename
                self.SaveFile()
                self.SetTitle( os.path.split(self.filename)[1] + ' - ' +  self.title)
            dlg.Destroy()

###################################################


    def OnMenuUndo(self, event):
        self.board.Undo()

    def OnMenuRedo(self, event):
        self.board.Redo()

    def OnMenuClear(self, event):
        self.board.Clear()
        self.SetTitle(self.title)

    def OnMenuExit(self, event):
        self.Close()

    def OnMenuAbout(self, event):
        dlg = About(self)
        dlg.ShowModal()
        dlg.Destroy()

    def OnMenuHistory(self, event):
        dlg = History(self, self.board)
        dlg.ShowModal()
        dlg.Destroy()



#----------------------------------------------------------------------


class ControlPanel(wx.Panel):
    """
    This class implements a very simple control panel for the boardWindow.
    It creates buttons for each of the colours and thickneses supported by
    the boardWindow, and event handlers to set the selected values.  There is
    also a little window that shows an example boardLine in the selected
    values.  Nested sizers are used for layout.
    """

    BMP_SIZE = 16
    BMP_BORDER = 3

    def __init__(self, parent, ID, board):
        wx.Panel.__init__(self, parent, ID, style=wx.RAISED_BORDER, size=(20,20))

        self.board = board
        items = ["Pen", "Rectangle", "Circle", "Ellipse", "Round Rect", "Eyedropper", "Text", "Fill", "Arc"]
        self.toolBtns  = {}
        self.clrBtns   = {}
        self.thknsBtns = {}
        tools = wx.GridSizer(cols=1, hgap=1, vgap=2)
        x = 1 # assign tool widgets IDs from 1-n(tools) to be used by the tool changer function

        for i in items:
            b = buttons.GenToggleButton(self, label=i, id=x)
            b.SetBezelWidth(1)
            b.Bind(wx.EVT_BUTTON, self.ChangeTool, id=x)
            tools.Add(b, 0)
            self.toolBtns[x] = b
            x += 1

        self.toolBtns[1].SetToggle(True)

        numCols = 4
        spacing = 4

        btnSize = wx.Size(self.BMP_SIZE + 2*self.BMP_BORDER,
                          self.BMP_SIZE + 2*self.BMP_BORDER)

        foreground = wx.ColourPickerCtrl(self, size= wx.DefaultSize)
        foreground.Bind(wx.EVT_COLOURPICKER_CHANGED, self.OnSetForeground)
        background = wx.ColourPickerCtrl(self, size=wx.DefaultSize)
        background.SetColour((255,255,255))

        choice_list = ""
        for i in range(1, 40):
            choice_list = choice_list + str(i) + " "

        thickness = wx.ComboBox(self, choices=choice_list.split(), size=(25,25),
                                        style=wx.CB_READONLY)
        thickness.SetSelection(0)
        thickness.Bind(wx.EVT_COMBOBOX, self.OnSetThickness)

        # registerd as a listener to board window - be notified when settings change
        ci = ColourIndicator(self)
        board.AddListener(ci)
        board.Notify()

        # add all GUI elements
        box = wx.BoxSizer(wx.VERTICAL)
        box.Add(tools, 0, wx.ALL, spacing)
        box.Add(foreground, 0, wx.EXPAND|wx.ALL, spacing)
        box.Add(background, 0, wx.EXPAND|wx.ALL, spacing)
        box.Add(thickness, 0, wx.EXPAND|wx.ALL, spacing)
        box.Add(ci, 0, wx.EXPAND|wx.ALL, spacing)
        self.SetSizer(box)
        self.SetAutoLayout(True)

        # Resize this window so it is just large enough for the
        # minimum requirements of the sizer.
        box.Fit(self)


    def ChangeTool(self, event):
        """Toggles the tool buttons on/off and calls ChangeTool on the
        drawing panel
        """
        new = int(event.GetId() )

        if new != self.board.tool: #changing tools, toggle old one
            self.toolBtns[self.board.tool].SetToggle(False)
        else:
            self.toolBtns[self.board.tool].SetToggle(True)

        self.board.SelectTool(new)


    def OnSetForeground(self, event):
        self.board.SetColour(event.GetColour() )

    def OnSetBackground(self, event):
        self.board.foreground = event.GetValue()

    def OnSetThickness(self, event):
        self.board.SetThickness(event.GetSelection() )


#----------------------------------------------------------------------

class ColourIndicator(wx.Window):
    """
    An instance of this class is used on the ControlPanel to show
    a sample of what the current tool will look like.
    """
    def __init__(self, parent):
        wx.Window.__init__(self, parent, -1, style=wx.SUNKEN_BORDER)
        self.SetBackgroundColour(wx.WHITE)
        self.SetSize( (45, 45) )
        self.colour = self.thickness = None
        self.Bind(wx.EVT_PAINT, self.OnPaint)


    def Update(self, colour, thickness):
        """
        The board window calls this method any time the colour
        or line thickness changes.
        """
        self.colour = colour
        self.thickness = thickness
        self.Refresh()  # generate a paint event


    def OnPaint(self, event):
        """
        This method is called when all or part of the window needs to be
        redrawn. Draws the tool inside the box when tool/colour/thickness
        is changed
        """
        dc = wx.PaintDC(self)
        if self.colour:
            sz = self.GetClientSize()
            pen = wx.Pen(self.colour, self.thickness)
            dc.BeginDrawing()
            dc.SetPen(pen)
            dc.DrawLine(10, sz.height/2, sz.width-10, sz.height/2)
            dc.EndDrawing()


#----------------------------------------------------------------------

class History(wx.Dialog):

    def __init__(self, parent, board):
        """Creates a history replaying dialogue"""
        wx.Dialog.__init__(self, parent, -1, "History Replayer", size=(400,200))
        self.board = board

        sizer = wx.BoxSizer(wx.VERTICAL)
        max = len(parent.board.shapes)+50
        self.slider = wx.Slider(self, minValue=1, maxValue=max, size=(200, 50), style=wx.SL_AUTOTICKS | wx.SL_HORIZONTAL | wx.SL_LABELS )
        self.slider.SetTickFreq(5, 1)
        self.slider.Bind(wx.EVT_SCROLL, self.OnScroll)
        sizer.Add(self.slider, 0, wx.ALL, 5)


        historySizer = wx.BoxSizer(wx.HORIZONTAL)
        btnPrev = wx.Button(self, label="<<", size=(40, 30) )
        btnStop = wx.Button(self, label="Stop", size=(45, 30) )
        btnPause = wx.Button(self, label="Pause", size=(50, 30) )
        btnPlay = wx.Button(self, label="Play", size=(45, 30) )
        btnNext = wx.Button(self, label=">>", size=(40, 30) )

        btnPlay.Bind(wx.EVT_BUTTON, self.OnPlay)

        historySizer.Add(btnPrev, 0,  wx.ALL, 2)
        historySizer.Add(btnStop, 0,  wx.ALL, 2)
        historySizer.Add(btnPause, 0,  wx.ALL, 2)
        historySizer.Add(btnPlay, 0,  wx.ALL, 2)
        historySizer.Add(btnNext, 0,  wx.ALL, 2)

        btnSizer = wx.StdDialogButtonSizer()
        btn = wx.Button(self, wx.ID_OK)
        btn.SetDefault()
        btnSizer.AddButton(btn)
        btnSizer.SetAffirmativeButton(btn)

        btn = wx.Button(self, wx.ID_CANCEL)
        btnSizer.AddButton(btn)
        btnSizer.SetCancelButton(btn)
        btnSizer.Realize()

        sizer.Add(historySizer, 0, wx.ALL, 5)
        sizer.Add(btnSizer, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 8)

        self.SetSizer(sizer)
        sizer.Fit(self)
        self.SetFocus()


    def OnScroll(self, event):
        print self.slider.GetValue()


    def OnPlay(self, event):

        pen = None
        dc = wx.ClientDC(self.board) #wx.BufferedDC(, self.board.buffer)
        dc.SetBackground(wx.Brush(self.board.GetBackgroundColour()) )
        dc.Clear()

        # find last drawn pen stroke
        for s in self.board.shapes:
            if isinstance(s, Pen):
                pen = s

            if pen is not None:
                self.board.reInitBuffer = False # hold off on this for a sec

                draw_pen = wx.Pen(pen.colour, pen.thickness, wx.SOLID)
                dc.SetPen(draw_pen)
                dc.BeginDrawing()

                for x, p in enumerate(pen.points):
                    try:
                        # 800 seems to make it sleep long enough
                        wx.MilliSleep( (pen.time[x+1] - pen.time[x]) * 950 )
                        wx.Yield()
                        dc.DrawLine(p[0], p[1], p[2], p[3])

                    except IndexError:
                        pass

                dc.EndDrawing()
                self.board.reInitBuffer = True

        #else:
        #    wx.MessageBox("No pen found..", "No pen drawings were found to replay!")



#----------------------------------------------------------------------


class About(wx.Dialog):
    version = "0.1"
    """ An about box that uses an HTML window """
    text = '''
<html>
<body bgcolor="#ACAA60">
<center><table bgcolor="#455481" width="100%" cellspacing="0"
cellpadding="0" border="1">
<tr>
    <td align="center"><h1>Whyteboard '''+version+'''</h1></td>
</tr>
</table>
</center>

<p><b>Whyteboard</b> is a simple image annotation program, facilitating the
annotation of PDF, PostScript and most image formats.</p>

<p>It is based on the demonstration code for wxPython, SuperDoodle by
Robin Dunn, &copy; 1997-2006.</p>
<p>Modified by Steven Sproat, &copy; 2009.</p>
</body>
</html>
'''

    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, -1, 'About Superboard',
                          size=(420, 380) )

        html = wx.html.HtmlWindow(self, -1)
        html.SetPage(self.text)
        button = wx.Button(self, wx.ID_OK, "Okay")

        # constraints for the html window
        lc = wx.LayoutConstraints()
        lc.top.SameAs(self, wx.Top, 5)
        lc.left.SameAs(self, wx.Left, 5)
        lc.bottom.SameAs(button, wx.Top, 5)
        lc.right.SameAs(self, wx.Right, 5)
        html.SetConstraints(lc)

        # constraints for the button
        lc = wx.LayoutConstraints()
        lc.bottom.SameAs(self, wx.Bottom, 5)
        lc.centreX.SameAs(self, wx.CentreX)
        lc.width.AsIs()
        lc.height.AsIs()
        button.SetConstraints(lc)

        self.SetAutoLayout(True)
        self.Layout()
        self.CentreOnParent(wx.BOTH)


#----------------------------------------------------------------------



class WhiteboardApp(wx.App):
    def OnInit(self):
        frame = GUI(None)
        frame.Show(True)
        self.SetTopWindow(frame)
        return True

#----------------------------------------------------------------------

if __name__ == '__main__':
    app = WhiteboardApp(True)
    app.MainLoop()
