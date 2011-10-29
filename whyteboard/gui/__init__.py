#!/usr/bin/env python
# -*- coding: utf-8 -*-

from event_ids import (ID_HISTORY, ID_REPORT_BUG, ID_FEEDBACK, ID_CLEAR_SHEETS,
                       ID_UPDATE, ID_PREV, ID_RECENTLY_CLOSED, ID_PASTE_NEW,
                       ID_MOVE_TO_TOP, ID_RENAME, ID_FULLSCREEN, ID_PDF_CACHE,
                       ID_EXPORT_PREF, ID_EXPORT_PDF, ID_RESIZE, ID_MOVE_TO_BOTTOM,
                       ID_CLEAR_ALL, ID_CLOSE_ALL,  ID_EXPORT, ID_COLOUR_GRID,
                       ID_UNDO_SHEET, ID_SWAP_COLOURS, ID_NEW, ID_BACKGROUND,
                       ID_IMPORT_IMAGE, ID_RELOAD_PREF, ID_DESELECT, ID_STATUSBAR,
                       ID_TRANSLATE, ID_MOVE_UP, ID_TOOL_PREVIEW, ID_IMPORT_PDF,
                       ID_MOVE_DOWN, ID_TOOLBAR, ID_CLEAR_ALL_SHEETS, ID_IMPORT_PREF,
                       ID_TRANSPARENT, ID_IMPORT_PS, ID_FOREGROUND, ID_EXPORT_ALL,
                       ID_NEXT, ID_SHAPE_VIEWER, ID_CLOSE_OTHERS)

from menu import Menu, Toolbar
from sheets import UndoSheetManager

from canvas import Canvas, CanvasDropTarget
from dialogs import (ExceptionHook, AboutDialog, Feedback, FindIM, History,
                     PDFCacheDialog, ProgressDialog, PromptForSave, Resize,
                     ShapeViewer, TextInput, UpdateDialog)

from popups import NotesPopup, ThumbsPopup, ShapePopup, SheetsPopup
from panels import ControlPanel, MediaPanel, SidePanel
from preferences import Preferences
from printing import Print

from frame import GUI
from app import WhyteboardApp