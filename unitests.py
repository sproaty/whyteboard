"""
Unit tests for the functionality parts of Whyteboard. Simulates wxPython
with mock classes. Doesn't test the GUI.
"""

import fakewidgets
import whyteboard
import unittest

class SimpleApp(fakewidgets.core.PySimpleApp):

    def OnInit(self):
        frame = fakewidgets.core.Window(None)
        ctrl = fakewidgets.core.Frame(frame)
        prev = fakewidgets.core.Panel(frame)
        ctrl.preview = prev
        frame.control = ctrl
        bk = fakewidgets.core.Notebook(frame)
        frame = whyteboard.Whyteboard(bk)
        frame.Show()
        return 1

#class TestWhyteboard(unittest.TestCase):
#    """
#    Tests the Whyteboard frame and its functionality.
#    """

#    def setUp(self):
#        self.board = whyteboard.Whyteboard(None)

#    def test_add_shape(self):
#        # make sure the shuffled sequence does not lose any elements
#        self.board.add(2)
#        self.assertEqual(len(self.seq), 1)

class TestApp(unittest.TestCase):

    def setUp(self):
        self.app = SimpleApp(True)

    def test_create(self):
        pass

    def test_on_init(self):
        retval = self.app.OnInit()
        assert retval == 1, retval

if __name__ == '__main__':
    unittest.main()
