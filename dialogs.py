#!usr/bin/python

"""
This module contains classes extended from wx.Dialog used by the GUI.
"""

import wx
import wx.html

from copy import copy

from tools import Pen, Image


#----------------------------------------------------------------------

class History(wx.Dialog):
    """
    Creates a history replaying dialog and methods for its functionality
    """

    def __init__(self, gui):
        wx.Dialog.__init__(self, gui, title="History Player", size=(400, 200))
        self.gui = gui
        self.looping = False
        self.paused = False
        #self.buffer = self.gui.board.buffer

        sizer = wx.BoxSizer(wx.VERTICAL)
        _max = len(gui.board.shapes)+50
        self.slider = wx.Slider(self, minValue=1, maxValue=_max, size=(200, 50),
                    style=wx.SL_AUTOTICKS | wx.SL_HORIZONTAL | wx.SL_LABELS )

        self.slider.SetTickFreq(5, 1)

        historySizer = wx.BoxSizer(wx.HORIZONTAL)
        btn_stop = wx.Button(self, label="Stop", size=(45, 30) )
        btn_pause = wx.Button(self, label="Pause", size=(50, 30) )
        btn_play = wx.Button(self, label="Play", size=(45, 30) )

        historySizer.Add(btn_play, 0,  wx.ALL, 2)
        historySizer.Add(btn_pause, 0,  wx.ALL, 2)
        historySizer.Add(btn_stop, 0,  wx.ALL, 2)

        sizer.Add(self.slider, 0, wx.ALL, 5)
        sizer.Add(historySizer, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALL, 5)

        self.SetSizer(sizer)
        sizer.Fit(self)
        self.SetFocus()

        btn_play.Bind(wx.EVT_BUTTON, self.on_play)
        btn_pause.Bind(wx.EVT_BUTTON, self.pause)
        btn_stop.Bind(wx.EVT_BUTTON, self.stop)
        self.Bind(wx.EVT_CLOSE, self.on_close)
        #self.slider.Bind(wx.EVT_SCROLL, self.scroll)


    def on_play(self, event):
        """
        Starts the replay if it's not already started, unpauses if paused
        """
        if self.looping:
            self.paused = False
            return

        if self.paused:
            self.paused = False

        tmp_shapes = copy(self.gui.board.shapes)
        shapes = []
        for shape in tmp_shapes:
            if isinstance(shape, Pen):
                shapes.append(shape)

        if shapes:
            self.looping = True
            self.start(shapes)
        else:
            wx.MessageBox("No pen found", "No drawings found to replay!")


    def start(self, shapes):
        """
        Replays the users' last-drawn pen strokes.
        The loop can be paused/unpaused by the user.
        """
        pen = None

        dc = wx.ClientDC(self.gui.board)
        dc.Clear()
        #dc.SetBrush(wx.TRANSPARENT_BRUSH)
        self.gui.board.PrepareDC(dc)

        #  paint any shapes but the pen first
        tmp_shapes = copy(self.gui.board.shapes)

        for s in tmp_shapes:
            if not isinstance(s, Pen):
                s.draw(dc)

        for pen in shapes:
            dc.SetPen(pen.pen)

            for x, p in enumerate(pen.points):
                if self.looping and not self.paused:

                    try:
                        wx.MilliSleep((pen.time[x + 1] - pen.time[x]) * 950)
                        wx.Yield()
                    except IndexError:
                        pass

                    dc.DrawLine(p[0], p[1], p[2], p[3])

                else:  # loop is paused, wait for unpause/close/stop
                    while self.paused:
                        wx.MicroSleep(100)
                        wx.Yield()

        self.stop()  # restore other drawn items


    def pause(self, event):
        """
        Pauses/unpauses the replay.
        """
        if self.looping:
            self.paused = not self.paused


    def stop(self, event=None):
        """
        Stops the replay.
        """
        if self.looping or self.paused:
            self.looping = False
            self.paused = False
            self.gui.board.Refresh()  # restore


    def on_close(self, event=None):
        """
        Called when the dialog is closed; stops the replay and ends the modal
        view, allowing the GUI to Destroy() the dialog.
        """
        self.stop()
        self.EndModal(1)

    def scroll(self, event):
        pass

#----------------------------------------------------------------------

class ConvertProgress(wx.Dialog):
    """
    Shows a Progres Gauge while file conversion is taking place.
    """

    def __init__(self, gui):
        """
        Defines a gauge and a timer which updates the gauge.
        """
        wx.Dialog.__init__(self, gui, title="Converting...",  size=(250, 100))
        self.gui = gui
        self.count = 0

        self.timer = wx.Timer(self)
        self.gauge = wx.Gauge(self, range=100, size=(180, 30))

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.gauge, 0, wx.ALL, 5)
        self.SetSizer(sizer)
        sizer.Fit(self)
        self.SetFocus()

        self.Bind(wx.EVT_TIMER, self.on_timer, self.timer)
        self.timer.Start(20)


    def on_timer(self, event):
        """
        Increases the gauge's progress.
        """
        self.count += 1
        self.gauge.SetValue(self.count)
        if self.count == 100:
            self.count = 0
            self.timer.Start(20)


#----------------------------------------------------------------------

class About(wx.Dialog):
    """
    Shows an HTML 'about' box for the program.
    """

    version = "0.30"
    text = '''
<html><body bgcolor="#6699CC">
 <table bgcolor="#F0F0F0" width="100%" border="1">
  <tr><td align="center"><h1>Whyteboard '''+version+'''</h1></td></tr>
 </table>

<p>Whyteboard is a simple image annotation program, facilitating the
annotation of PDF and PostScript files, and most image formats.</p>

<p>It is based on a demonstration application for wxPython; SuperDoodle, by
Robin Dunn, &copy; 1997-2006.</p>
<p>Modified by Steven Sproat, &copy; 2009.<br />
Many thanks to the helpful users in #python on FreeNode!</p>
</body></html>'''

    def __init__(self, parent):
        """
        Displays the HTML box with various constraints.
        """
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
