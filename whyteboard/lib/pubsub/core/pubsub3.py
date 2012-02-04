'''
This is the top-level API to pubsub version 3. 

This package can be configured via the pubsubconf module (available 
outside of the pubsub package, but installed alongside it).


:Author:      Oliver Schoenborn
:Since:       Oct 2007
:Version:     1.0
:Copyright:   \(c) 2007 Oliver Schoenborn
:License:     Python Software Foundation
'''

PUBSUB_VERSION = 3 # DO NOT CHANGE

import pubsubconf
pubsubconf.packageImported = True
Policies = pubsubconf.Policies

from listener import \
    Listener, \
    getID as getListenerID, \
    ListenerInadequate, \
    isValid as _isValid
    
from topics import \
    ALL_TOPICS, \
    TopicUnspecifiedError, \
    MissingReqdArgs, \
    UnknownOptArgs, \
    Topic, \
    TopicManager as _TopicManager

from publisher import Publisher



__all__ = [
    # listener stuff:
    'Listener', 'ListenerInadequate', 
    'isValid', 'validate',
    
    # topic stuff:
    'ALL_TOPICS', 'Topic', 
    'topics', 'topicsMap', 'AUTO_ARG',
    'newTopic', 'delTopic', 'getTopic', 
    'getAssociatedTopics', 'getDefaultTopicMgr', 'getDefaultRootTopic',
    'TopicUnspecifiedError', 'addTopicDefnProvider',
    
    # publisher stuff:
    'Publisher', 
    'subscribe', 'unsubscribe', 'isSubscribed', 'unsubAll', 
    'sendMessage', 'setNotification', 
    'MissingReqdArgs', 'UnknownOptArgs',
    
    # misc:
    'PUBSUB_VERSION',
    ]


# ---------------------------------------------
_topicMgr = _TopicManager()

topics    = _topicMgr._rootTopic
topicsMap = _topicMgr._topicsMap
AUTO_ARG  = Listener.AUTO_ARG


def isValid(listener, topicName):
    '''Return true only if listener can subscribe to messages of 
    type topicName.'''
    return _topicMgr.getTopic(topicName).isValid(listener)


def validate(listener, topicName):
    '''Checks if listener can subscribe to topicName. Raises 
    ListenerInadequate if not. Otherwise, returns whether listener
    accepts topicName as one of its arguments. '''
    return _topicMgr.getTopic(topicName).validate(listener)

    
def isSubscribed(listener, topicName):
    '''Returns true if listener has subscribed to topicName, false otherwise.
    Note that a false return is not a guarantee that listener won't get 
    messages of topicName: it could get messages of a subtopic of topic 
    if some are sent. '''
    return _topicMgr.getTopic(topicName).hasListener(listener)
    

def getDefaultTopicMgr():
    '''Get the topic manager that is created by default when you 
    import package.'''
    return _topicMgr

def getDefaultRootTopic():
    '''Get the root topic that is created by default when you 
    import package. All top-level topics are children of that 
    topic. '''
    return _topicMgr._rootTopic

newTopic            = _topicMgr.newTopic
delTopic            = _topicMgr.delTopic
getTopic            = _topicMgr.getTopic
getAssociatedTopics = _topicMgr.getTopics
addTopicDefnProvider = _topicMgr.addDefnProvider
    
# ---------------------------------------------

from pubsubconf import Policies
_publisher = Publisher( _topicMgr )

subscribe   = _publisher.subscribe    
unsubscribe = _publisher.unsubscribe
unsubAll    = _publisher.unsubAll
sendMessage = _publisher.sendMessage
    
Publisher  = _publisher # for backward compat with pubsub1
    
def setNotification(subscribe=None, unsubscribe=None, 
    deadListener=None, sendMessage=None, newTopic=None, 
    delTopic=None, all=None):
    '''Set the notification on/off for various aspects of pubsub:
    
    - subscribe:    send a 'pubsub.subscribe' message whenever a 
                    listener subscribes to a topic;
    - unsubscribe:  send a 'pubsub.unsubscribe' message whenever a 
                    listener unsubscribes from a topic;
    - deadListener: send a 'pubsub.deadListener' message whenever 
                    pubsub finds out that a listener has died;
    - send:         send a 'pubsub.sendMessage' message whenever the 
                    user calls sendMessage();
    - newTopic:     send a 'pubsub.newTopic' message whenever the 
                    user defines a new topic;
    - delTopic:     send a 'pubsub.delTopic' message whenever the 
                    user undefines a topic.
    - all:          set all of the above to the given value.
    
    The kwargs that are None are left at their current value. The 'all'
    is set first, then the others. E.g. 
    
        pubsub.setNotification(all=True, delTopic=False)
    
    will toggle all notifications on, but will turn off the 'delTopic'
    notification. 
    
    Note that setNotification() merely sets what notifications are given, 
    not how they take place. The how is defined by setting the notifier 
    class to use, via a call to pubsubconf.setNotificationHandler() once 
    when the application starts.
    '''
    if all is not None: 
        _publisher.setNotification(all, all, all)
        _topicMgr.setNotification(all, all, all)
        
    _publisher.setNotification(
        subscribe=subscribe, 
        unsubscribe=unsubscribe, 
        sendMessage=sendMessage)
    _topicMgr.setNotification(
        newTopic=newTopic, 
        delTopic=delTopic, 
        deadListener=deadListener)


