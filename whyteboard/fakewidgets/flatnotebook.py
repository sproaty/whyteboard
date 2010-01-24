import core

# thankfully this just works...
# I'm using my own custom FlatNotebook (for the time being)
# and have to mock that.

class FlatNotebook(core.Notebook):
    pass

from ..lib import flatnotebook as flatnotebook  # phew!
flatnotebook.__dict__.update(locals())