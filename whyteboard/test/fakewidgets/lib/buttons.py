from .. import core

class GenBitmapToggleButton(core.ToggleButton):
    pass

from wx.lib import buttons
buttons.__dict__.update(locals())