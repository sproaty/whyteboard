###############################################################################
# Name: errdlg.py                                                             #
# Purpose: Error Reporter Dialog                                              #
# Author: Cody Precord <cprecord@editra.org>                                  #
# Copyright: (c) 2009 Cody Precord <staff@editra.org>                         #
# License: wxWindows License                                                  #
###############################################################################

"""
Editra Control Library: Error Reporter Dialog

Dialog for displaying exceptions and reporting errors to application maintainer.
This dialog is intended as a base class and should be subclassed to fit the
applications needs.

This dialog should be initiated inside of a sys.excepthook handler.

Example:

sys.excepthook = ExceptHook
...
def ExceptionHook(exctype, value, trace):
    # Format the traceback
    ftrace = ErrorDialog.FormatTrace(exctype, value, trace)

    # Ensure that error gets raised to console as well
    print ftrace

    # If abort has been set and we get here again do a more forcefull shutdown
    if ErrorDialog.ABORT:
        os._exit(1)

    # Prevent multiple reporter dialogs from opening at once
    if not ErrorDialog.REPORTER_ACTIVE and not ErrorDialog.ABORT:
        dlg = ErrorDialog(ftrace)
        dlg.ShowModal()
        dlg.Destroy()

@summary: Error Reporter Dialog

"""

__author__ = "Cody Precord <cprecord@editra.org>"
__svnid__ = "$Id: errdlg.py 61808 2009-09-02 15:57:55Z CJP $"
__revision__ = "$Revision: 61808 $"

__all__ = [# Classes
           'ErrorDialog', 'ErrorReporter']

#----------------------------------------------------------------------------#
# Dependancies
import os
import sys
import platform
import time
import traceback
import wx

#----------------------------------------------------------------------------#
# Globals

_ = wx.GetTranslation
#----------------------------------------------------------------------------#

class ErrorReporter(object):
    """Crash/Error Reporter Service
    @summary: Stores all errors caught during the current session.
    @note: singleton class

    """
    instance = None
    _first = True
    def __init__(self):
        """Initialize the reporter
        @note: The ErrorReporter is a singleton.

        """
        # Ensure init only happens once
        if self._first:
            object.__init__(self)
            self._first = False
            self._sessionerr = list()
        else:
            pass

    def __new__(cls, *args, **kargs):
        """Maintain only a single instance of this object
        @return: instance of this class

        """
        if not cls.instance:
            cls.instance = object.__new__(cls, *args, **kargs)
        return cls.instance

    def AddMessage(self, msg):
        """Adds a message to the reporters list of session errors
        @param msg: The Error Message to save

        """
        if msg not in self._sessionerr:
            self._sessionerr.append(msg)

    def GetErrorStack(self):
        """Returns all the errors caught during this session
        @return: formatted log message of errors

        """
        return (os.linesep * 2).join(self._sessionerr)

    def GetLastError(self):
        """Gets the last error from the current session
        @return: Error Message String

        """
        if len(self._sessionerr):
            return self._sessionerr[-1]

#-----------------------------------------------------------------------------#

class ErrorDialog(wx.Dialog):
    """Dialog for showing errors and and notifying Editra.org should the
    user choose so.

    """
    ID_SEND = wx.NewId()
    ABORT = False
    REPORTER_ACTIVE = False
    def __init__(self, parent, id=wx.ID_ANY, title=u'',
                 pos=wx.DefaultPosition, size=wx.DefaultSize,
                 style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
                 name="ErrorReporterDlg", message=u''):
        """Initialize the dialog
        @param message: Error message to display

        """
        ErrorDialog.REPORTER_ACTIVE = True
        wx.Dialog.__init__(self, parent, id, title, pos, size, style, name)

        # Give message to ErrorReporter
        ErrorReporter().AddMessage(message)

        # Attributes
        self.err_msg = os.linesep.join((self.GetEnvironmentInfo(), 
                                        unicode(ErrorReporter().GetErrorStack(), "utf-8")))
        # Layout
        self._panel = ErrorPanel(self, self.err_msg)
        self._DoLayout()
        self.SetMinSize(wx.Size(450, 300))
        self.parent = parent

        # Event Handlers
        self.Bind(wx.EVT_BUTTON, self.OnButton)
        self.Bind(wx.EVT_CLOSE, self.OnClose)

        # Auto show at end of init
        self.CenterOnParent()

    def _DoLayout(self):
        """Layout the dialog and prepare it to be shown
        @note: Do not call this method in your code

        """
        msizer = wx.BoxSizer(wx.VERTICAL)
        msizer.Add(self._panel, 1, wx.EXPAND)
        self.SetSizer(msizer)
        self.SetInitialSize()

    #---- Override in Subclass ----#

    def Abort(self):
        """Called to abort the application
        @note: needs to be overidden in sublcasses

        """
        raise NotImplementedError("Abort must be implemented!")

    def GetEnvironmentInfo(self):
        """Get the enviromental info / Header of error report
        @return: string

        """
        system_language = wx.Locale.GetLanguageName(wx.Locale.GetSystemLanguage())
        running_language = wx.Locale.GetLanguageName(wx.GetLocale().GetLanguage())
        res = wx.Display().GetGeometry()
        info = list()
        info.append(self.GetProgramName())
        info.append(u"Operating System: %s" % wx.GetOsDescription())
        if sys.platform == 'darwin':
            info.append(u"Mac OSX: %s" % platform.mac_ver()[0])
        info.append(u"System Lanauge: %s" % system_language)
        info.append(u"Running Lanauge: %s" % running_language)
        info.append(u"Screen Resolution: %ix%i" % (res[2], res[3]))
        info.append(u"Python Version: %s" % sys.version)
        info.append(u"wxPython Version: %s" % wx.version())
        info.append(u"wxPython Info: (%s)" % ", ".join(wx.PlatformInfo))
        info.append(u"Python Encoding: Default=%s  File=%s" % \
                    (sys.getdefaultencoding(), sys.getfilesystemencoding()))
        info.append(u"wxPython Encoding: %s" % wx.GetDefaultPyEncoding())
        info.append(u"System Architecture: %s %s" % (platform.architecture()[0], \
                                                    platform.machine()))
        info.append(u"Frozen: %s" % str(getattr(sys, 'frozen', 'False')))
        info.append(u"")
        info.append(u"")

        return info#os.linesep.join(info)

    def GetProgramName(self):
        """Get the program name/version info to include in error report
        @return: string

        """
        return wx.GetApp().GetAppName()

    def Send(self):
        """Called to send error report
        @note: needs to be overridden in subclasses

        """
        raise NotImplementedError("Send must be implemented!")

    #---- End Required overrides ----#

    @staticmethod
    def FormatTrace(exctype, value, trace):
        """Format the traceback
        @return: string

        """
        exc = traceback.format_exception(exctype, value, trace)
        ftrace = "".join(exc)
        return ftrace

    def SetDescriptionLabel(self, label):
        """Set the dialogs main description text
        @param label: string

        """
        self._panel.SetDescriptionText(label)

    def ShowAbortButton(self, show=True):
        """Show/Hide the Abort button
        @keyword show: bool

        """
        btn = self._panel.FindWindowById(wx.ID_ABORT)
        if btn is not None:
            btn.Show(show)
            self._panel.Layout()

    def ShowSendButton(self, show=True):
        """Show/Hide the Send button
        @keyword show: bool

        """
        btn = self._panel.FindWindowById(ErrorDialog.ID_SEND)
        if btn is not None:
            btn.Show(show)
            self._panel.Layout()

    #---- Event Handlers ----#

    def OnButton(self, evt):
        """Handles button events
        @param evt: event that called this handler
        @postcondition: Dialog is closed
        @postcondition: If Report Event then email program is opened

        """
        e_id = evt.GetId()
        if e_id == wx.ID_CLOSE:
            self.Close()
        elif e_id == ErrorDialog.ID_SEND:
            self.Send()
            self.Close()
        elif e_id == wx.ID_ABORT:
            ErrorDialog.ABORT = True
            self.Abort()
            self.Close()
        else:
            evt.Skip()

    def OnClose(self, evt):
        """Cleans up the dialog when it is closed
        @param evt: Event that called this handler

        """
        ErrorDialog.REPORTER_ACTIVE = False
        evt.Skip()

#-----------------------------------------------------------------------------#

class ErrorPanel(wx.Panel):
    """Error Reporter panel"""
    def __init__(self, parent, msg):
        """Create the panel
        @param parent: wx.Window
        @param msg: Error message to display

        """
        wx.Panel.__init__(self, parent)

        # Attributes
        self.err_msg = msg
        self.desc = wx.StaticText(self, label=u'')

        # Layout
        self.__DoLayout()

    def __DoLayout(self):
        """Layout the control"""
        icon = wx.StaticBitmap(self,
                               bitmap=wx.ArtProvider.GetBitmap(wx.ART_ERROR))
        d = _("Description of what you was doing before this error appeared")

        t_lbl = wx.StaticText(self, label=_("Error Traceback:"))
        email_label = wx.StaticText(self, label=_("E-mail Address (Optional)"))
        self.action = wx.TextCtrl(self, value=d, style=wx.TE_MULTILINE)
        tctrl = wx.TextCtrl(self, value=self.err_msg, style=wx.TE_MULTILINE |
                                                            wx.TE_READONLY)

        abort_b = wx.Button(self, wx.ID_ABORT, _("Abort"))
        abort_b.SetToolTipString(_("Exit the application"))
        send_b = wx.Button(self, ErrorDialog.ID_SEND, _("Report Error"))
        send_b.SetDefault()
        close_b = wx.Button(self, wx.ID_CLOSE)
        self.email = wx.TextCtrl(self)

        font = t_lbl.GetClassDefaultAttributes().font
        font.SetWeight(wx.FONTWEIGHT_BOLD)
        font.SetPointSize(font.GetPointSize() + 1)
        self.desc.SetFont(font)

        order = (self.action, self.email, send_b, close_b, abort_b)  # tab order
        for i in xrange(len(order) - 1):
            order[i+1].MoveAfterInTabOrder(order[i])

        # Layout
        vsizer = wx.BoxSizer(wx.VERTICAL)
        hsizer1 = wx.BoxSizer(wx.HORIZONTAL)
        hsizer1.AddMany([((5, 40), 0), (icon, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 10),
                         ((12, 10), 0), (self.desc, 0, wx.ALIGN_CENTER_VERTICAL), ((5, 20), 0)])

        hsizer2 = wx.BoxSizer(wx.HORIZONTAL)
        hsizer2.AddMany([((5, 150), 0), (tctrl, 1, wx.EXPAND | wx.BOTTOM, 10)])

        hsizer3 = wx.BoxSizer(wx.HORIZONTAL)
        hsizer3.AddMany([((5, 80), 0), (self.action, 1, wx.EXPAND), ((5, 20), 0)])

        hsizer4 = wx.BoxSizer(wx.VERTICAL)
        hsizer4.AddMany([((5, 5), 0), (email_label, 0,wx.BOTTOM | wx.LEFT, 10),
                         (self.email, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 5), ((5, 20), 0)])

        bsizer = wx.BoxSizer(wx.HORIZONTAL)
        bsizer.AddMany([((5, 5), 0), (abort_b, 0), ((-1, -1), 1, wx.EXPAND),
                        (send_b, 0), ((5, 5), 0), (close_b, 0), ((5, 5), 0)])

        vsizer.AddMany([((5, 5), 0),
                        (hsizer1, 0),
                        ((10, 10), 0),
                        (t_lbl, 0, wx.ALIGN_LEFT | wx.LEFT | wx.BOTTOM, 5),
                        ((3, 3), 0),
                        (hsizer2, 1, wx.EXPAND),
                        ((8, 8), 0),
                        (hsizer3, 0, wx.EXPAND),
                        ((8, 8), 0),
                        (hsizer4, 0, wx.EXPAND),
                        ((8, 4), 0),
                        (bsizer, 0, wx.EXPAND),
                        ((8, 8), 0)])

        self.SetSizer(vsizer)
        self.SetAutoLayout(True)

    def SetDescriptionText(self, text):
        """Set the description label text
        @param text: string

        """
        self.desc.SetLabel(text)
        self.Layout()
