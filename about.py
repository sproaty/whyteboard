#!/usr/bin/python

"""
Shows an HTML 'about' box for the program.
"""

import wx
import wx.html

#----------------------------------------------------------------------

class About(wx.Dialog):
    version = "0.26"
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
