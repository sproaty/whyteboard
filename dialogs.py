#!usr/bin/python

"""
This module contains classes extended from wx.Dialog used by the GUI.
"""

import wx
import wx.html
from tools import Pen


#----------------------------------------------------------------------

class History(wx.Dialog):
    """
    Creates a history replaying dialog and methods for its functionality
    """

    def __init__(self, parent, board):
        wx.Dialog.__init__(self, parent, title="History Player",
                           size=(400, 200))
        self.board = board

        sizer = wx.BoxSizer(wx.VERTICAL)
        max = len(parent.board.shapes)+50
        self.slider = wx.Slider(self, minValue=1, maxValue=max, size=(200, 50),
                    style=wx.SL_AUTOTICKS | wx.SL_HORIZONTAL | wx.SL_LABELS )
        self.slider.SetTickFreq(5, 1)
        self.slider.Bind(wx.EVT_SCROLL, self.scroll)
        sizer.Add(self.slider, 0, wx.ALL, 5)

        historySizer = wx.BoxSizer(wx.HORIZONTAL)
        btnPrev = wx.Button(self, label="<<", size=(40, 30) )
        btnStop = wx.Button(self, label="Stop", size=(45, 30) )
        btnPause = wx.Button(self, label="Pause", size=(50, 30) )
        btnPlay = wx.Button(self, label="Play", size=(45, 30) )
        btnNext = wx.Button(self, label=">>", size=(40, 30) )

        btnPlay.Bind(wx.EVT_BUTTON, self.play)

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


    def scroll(self, event):
        pass


    def play(self, event):
        """Replays the users' last-drawn pen(s)"""
        pen = None
        dc = wx.ClientDC(self.board) #wx.BufferedDC(, self.board.buffer)
        dc.SetBackground(wx.Brush(self.board.GetBackgroundColour()) )
        dc.Clear()

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
                        wx.MilliSleep( (pen.time[x + 1] - pen.time[x]) * 950 )
                        wx.Yield()
                        dc.DrawLine(p[0], p[1], p[2], p[3])

                    except IndexError:
                        pass

                dc.EndDrawing()
                self.board.reInitBuffer = True
        else:
            wx.MessageBox("No pen found", "No drawings found to replay!")

#----------------------------------------------------------------------

class ConvertProgress(wx.Dialog):
    """
    Shows a Progres Gauge while file conversion is taking place.
    """

    def __init__(self, gui):
        wx.Dialog.__init__(self, gui, title="Converting...",  size=(250, 100))
        self.gui = gui
        sizer = wx.BoxSizer(wx.VERTICAL)

        self.gauge = wx.Gauge(self, range=50, pos=(110, 50), size=(180, 30))
        self.Bind(wx.EVT_IDLE, self.pump_gauge)
        self.count = 0

        sizer.Add(self.gauge, 0, wx.ALL, 5)
        self.SetSizer(sizer)
        sizer.Fit(self)
        self.SetFocus()


    def pump_gauge(self, event):
        """
        Pumps the gauge to indicate conversion progress
        """
        self.count += 0.15

        if self.count >= 999:
            self.count = 0
        self.gauge.SetValue(self.count)

#----------------------------------------------------------------------

class About(wx.Dialog):
    """
    Shows an HTML 'about' box for the program.
    """

    version = "0.27"
    text = '''
<html><body bgcolor="#6699CC">
 <table bgcolor="#F0F0F0" width="100%" border="1">
  <tr><td align="center"><h1>Whyteboard '''+version+'''</h1></td></tr>
 </table>

<p>Whyteboard is a simple image annotation program, facilitating the
annotation of PDF and PostScript files, and most image formats.</p>

<p>It is based on a demonstration application wxPython; SuperDoodle, by
Robin Dunn, &copy; 1997-2006.</p>
<p>Modified by Steven Sproat, &copy; 2009.<br />
Many thanks to the helpful users in #python on FreeNode!</p>
</body></html>'''

    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, title='About Whyteboard',
                           size=(420, 380))

        html = wx.html.HtmlWindow(self, -1)
        html.SetPage(self.text)
        button = wx.Button(self, wx.ID_OK, "Okay")

        lc = wx.LayoutConstraints()
        lc.top.SameAs(self, wx.Top, 5)
        lc.left.SameAs(self, wx.Left, 5)
        lc.bottom.SameAs(button, wx.Top, 5)
        lc.right.SameAs(self, wx.Right, 5)
        html.SetConstraints(lc)

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

if __name__ == '__main__':
    from gui import WhyteboardApp
    app = WhyteboardApp(redirect=True)
    app.MainLoop()
