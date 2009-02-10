#!usr/bin/python

"""
Shows a history replaying dialog, which can replay the last pen strokes
drawn by the user.
"""

import wx
from tools import Pen


#----------------------------------------------------------------------

class History(wx.Dialog):

    def __init__(self, parent, board):
        """Creates a history replaying dialogue"""
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


if __name__ == '__main__':
    from gui import WhyteboardApp
    app = WhyteboardApp(redirect=True)
    app.MainLoop()
