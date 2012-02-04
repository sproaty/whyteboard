from .. import core

class ColourSelect(core.BitmapButton):

    def GetColour(self, width=None, height=None):
        pass

    def SetValue(self, attr):
        pass

from wx.lib import colourselect
colourselect.__dict__.update(locals())