'''
Publisher-subscribe module, simple form. 

This package provides the pub and utils modules. Use for instance

    from pubsub import pub
    help(pub)
    pub.sendMessage(topic, ...)
    from pubsub import utils as pubutils
    pubutils....

Do not use Publisher in new code, it is deprecated (see below). 

DEPRECATED use: old code can still use 

    from pubsub import Publisher
    help(Publisher.__class__)
    Publisher.sendMessage(topic) # OR:
    Publisher().sendMessage(topic)
    
but should be converted to new format.
'''

__all__ = ['pub', 'utils'] 


# if user wants old pubsub, main API is a singleton Publisher instance
# ie no way to fake via module so must import here; but that's ok since
# for version 1 there are no utilities etc. 
import pubsubconf
if pubsubconf.getVersion() <= 1:
    from core.pubsub1 import Publisher as pub
    Publisher = pub
    __all__.append('Publisher')
