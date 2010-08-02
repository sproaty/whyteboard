#!/usr/bin/env python
# -*- coding: utf-8 -*-

import core

# thankfully this just works...
# I'm using my own custom FlatNotebook (for the time being)
# and have to mock that.

class FlatNotebook(core.Notebook):
    pass

from whyteboard.lib import flatnotebook  # phew!
flatnotebook.__dict__.update(locals())