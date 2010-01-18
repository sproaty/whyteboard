from .. import core

class GenBitmapToggleButton(core.ToggleButton):
    pass

import wx.lib.buttons
wx.lib.buttons.__dict__.update(locals())