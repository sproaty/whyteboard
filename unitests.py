"""
Unit tests for the functionality parts of Whyteboard. Simulates wxPython
with mock classes. Doesn't test the GUI.
"""
import unittest
from copy import copy

import fakewidgets
import whyteboard
import tools

def setup_wb():
    """
    Creates a Whyteboard instance and sets up appropriate mock parent hierarchy
    returns the instance of the Whyteboard
    """
    gui = fakewidgets.core.Window(None)  # mocking the GUI

    bk = fakewidgets.core.Notebook(gui)
    wb = whyteboard.Whyteboard(bk)
    return wb

#----------------------------------------------------------------------

class SimpleApp(fakewidgets.core.PySimpleApp):

    def OnInit(self):
        wb = setup_wb()
        wb.Show()
        return 1

#----------------------------------------------------------------------

class TestWhyteboard(unittest.TestCase):
    """
    Tests the Whyteboard frame and its functionality.
    """

    def setUp(self):
        """
        Adds a few shapes to the list
        """
        app = SimpleApp(True)
        self.board = setup_wb()
        pen = tools.Pen(self.board, (0, 0, 0), 1, 1)
        self.board.add_shape(pen)
        self.board.add_shape(copy(pen))

    def testAddShape(self):
        """Test adding shapes"""
        self.board.add_shape(tools.Image(self.board, (0, 0, 0), 1))
        self.assertEqual(len(self.board.shapes), 3)

    def testUndo(self):
        pass#self.board.undo()  # pop image
        #print self.board.shapes
        #self.assertEqual(len(self.board.redo_list), 1)
        #self.assertEqual(len(self.board.shapes), 2)

    def testRedo(self):
        """
        Redo last action
        """
        pass#self.board.redo()
        #self.assertEqual(len(self.board.shapes), 2)
        #self.assertEqual(len(self.board.redo_list), 0)
        #self.assertEqual(len(self.board.undo_list), 1)

    def testClear(self):
        """
        Clear all items
        """
        pass#self.board.clear()
        #self.assertEqual(len(self.board.shapes), 0)
        #print self.board.undo_list
        #self.assertEqual(len(self.board.undo_list), 2)

    def testUndoClear(self):
        pass

    def testRedoClear(self):
        pass

#----------------------------------------------------------------------

class TestApp(unittest.TestCase):

    def setUp(self):
        self.app = SimpleApp(True)

    def test_create(self):
        pass

    def test_on_init(self):
        retval = self.app.OnInit()
        assert retval == 1, retval

#----------------------------------------------------------------------

if __name__ == '__main__':
    unittest.main()
