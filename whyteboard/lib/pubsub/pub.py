"""
Pubsub package initialization. This module loads the pubsub API
selected via pubsubconf. The default is to load latest pubsub 
API. The Publisher variable is deprecated but is made
available for backward compatibility. 

This module assumes one of two imports::

  from pubsub import pub
  from pubsub import Publisher
  
(do not use "import pubsub" or "from pubsub import *").
"""

import pubsubconf

# indicate that package has been loaded:
pubsubconf.packageLoaded = True

__all__ = []

def _notify(output, version):
    if output is not None:
        output.write('Importing version %s of pubsub\n' % version)
    
_output  = pubsubconf.getVersionOutput()
_version = pubsubconf.getVersion()

if _version <= 1:
    msg = 'BUG: Should not be loaded for version (%s) <= 1' % _version
    raise NotImplementedError(msg)
    
if _version <= 2:
    _notify(_output, 2)
    from core.pubsub2 import *
    from core import pubsub2 as _pubsubMod

elif _version <= 3:
    _notify(_output, 3)
    from core.pubsub3 import *
    from core import pubsub3 as _pubsubMod
    
else:
    _output.write('Warning: pubsub version %s doesn\'t exist')
    raise NotImplementedError('pubsub version %s doesn\'t exist' % _version)

assert PUBSUB_VERSION == _version
__doc__ = _pubsubMod.__doc__
__all__.extend(_pubsubMod.__all__)

