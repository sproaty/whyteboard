from .. import core

class ScrolledPanel(core.ScrolledWindow):
        
    def Scroll(self, width, height):
        pass
        
    def __getattr__(self, attr):
        """Just fake any other methods"""
        pass

import wx.lib.scrolledpanel
wx.lib.scrolledpanel.__dict__.update(locals())