import wx


class TBI(wx.TaskBarIcon):
    def __init__(self):
        wx.TaskBarIcon.__init__(self)
        icon = wx.ArtProvider.GetIcon(wx.ART_FILE_OPEN, wx.ART_TOOLBAR)
        self.SetIcon(icon, "Icon")
        self.Bind(wx.EVT_TASKBAR_RIGHT_UP, self.on_right_up)
        
    def on_right_up(self, event):
         if wx.GetKeyState(wx.WXK_CONTROL):
             print 'ctrl was pressed!'

                                                                                                                      
app = wx.App(redirect=False)
icon = TBI()
app.MainLoop()