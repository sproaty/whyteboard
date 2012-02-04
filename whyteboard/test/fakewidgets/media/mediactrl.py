from .. import core

class MediaCtrl(core.Control):
    def GetState(self):
        return 0

    def Load(self, path):
        pass

    def Pause(self):
        pass

    def Play(self):
        pass

    def Stop(self):
        pass

    def Seek(self, position):
        pass

    def SetVolume(self, volume):
        pass

import wx.media
wx.media.__dict__.update(locals())