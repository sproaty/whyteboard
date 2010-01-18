from .. import core

class ColourSelect(core.BitmapButton):
        
    def GetColour(self, width, height):
        pass
        
    def SetValue(self, attr):
        pass

import wx.lib.colourselect
wx.lib.colourselect.__dict__.update(locals())