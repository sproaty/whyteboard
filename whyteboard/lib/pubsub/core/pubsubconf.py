"""
Allows user to configure pubsub. Most important:

- setVersion(N): State which version of pubsub should be used (N=1, 2 or 3; 
  defaults to latest). E.g. to use version 1 of pubsub:
    
    # in your main script only:
    import pubsubconf
    pubsubconf.setVersion(1)
    
    # in main script and all other modules imported:
    from pubsub import pub # usual line
    
- Several functions specific to version 3:

  - setListenerExcHandler(handler): set handling of exceptions 
    raised in listeners (default: None). 
    
  - setTopicUnspecifiedFatal(val=True): state whether unspecified 
    topics should be creatable (default: False). 
    
  - setNotificationhandler(notificationhandler): what class to instantiate for 
    processing notification events (default: None).
  
  - transitionV1ToV3(commonName, stage=1): set policies that support 
    migrating an application from pubsub version 1 to version 3.
     
"""


packageImported = False


class Version:
    DEFAULT = 3
    value  = None
    output = None
        

def setVersion(val, output=None):
    '''Set the version of package to be used when imported. If 
    output is set to a file object (has write() method), a message
    will be written to that file indicating which version of pubsub 
    has been imported. E.g. setVersion(2, sys.stdout).'''
    if val < 1 or val > 3:
        raise ValueError('val = %s invalid, need 1 <= val <= 3' % val)
    Version.value  = val
    Version.output = output

def getVersion():
    '''Get version number selected for import (via setVersion, 
    or default version if setVersion not called).'''
    return Version.value or Version.DEFAULT

def isVersionChosen():
    '''Return True if setVersion() was called at least once.'''
    return Version.value is not None
    
def getDefaultVersion():
    '''Get version number imported by default.'''
    return Version.default
    
def getVersionOutput():
    '''Return the file object to be used for messaging about imported version'''
    return Version.output


class Policies:
    '''
    Define the policies used by pubsub, when several alternatives 
    exist. 
    '''
    
    _notificationHandler     = None
    _listenerExcHandler      = None
    _raiseOnTopicUnspecified = False
    _msgDataProtocol         = 'kwargs'
    _msgDataArgName          = None
    

def setTopicUnspecifiedFatal(val=True):
    '''When called with val=True (default), causes pubsub to 
    raise an UnspecifiedTopicError when attempting to create
    a topic that has no specification. This happens when 
    pub.addTopicDefnProvider() was never called, or none of 
    the given providers specify the topic (or a super topic of 
    it) that was given to pub.subscribe(). If True, the topic 
    will be created with argument specification inferred from 
    first listener subscribed. '''
    Policies._raiseOnTopicUnspecified = val
    
    
def setNotificationHandler(notificationHandler):
    '''The notifier should be a class that follows the API of  
    pubsub.utils.INotificationHandler. If no notifier is set, then 
    the default will be used. '''
    Policies._notificationHandler = notificationHandler
    

def setListenerExcHandler(handler):
    '''Set the handler to call when a listener raises an exception
    during a sendMessage(). Without a handler, the send operation
    aborts, whereas with one, the exception information is sent to 
    it (where it can be logged, printed, whatever), and 
    sendMessage() continues to send messages
    to remaining listeners. '''
    Policies._listenerExcHandler = handler


def isPackageImported():
    '''Can be used to determine if pubsub package has been imported 
    by your application (or by any modules imported by it). '''
    return packageImported


def setMsgProtocol(protocol):
    '''Messaging protocol defaults to 'kwargs'. It can be set to 
    'dataArg' to support legacy code or simple pub-sub architectures. '''
    if protocol not in ('dataArg', 'kwargs'):
        raise NotImplementedError('The protocol "%s" is not supported' % protocol)
    
    Policies._msgDataProtocol = protocol

    
def transitionV1ToV3(commonName, stage=1):
    '''Use this to help with migrating code from protocol DATA_ARG to 
    KW_ARGS. This only makes sense in an application that has been using 
    setMsgProtocol('dataArg') and wants to move to the more robust 'kwargs'. 
    This function is designed to support a three-stage process: 
    (stage 1) make all listeners use the same argument name (commonName); 
    (stage 2) make all senders use the kwargs protocol and all listeners
    use kwargs rather than Message.data. The third stage, for which you 
    don't use this function, consists in splitting up your message data
    into more kwargs and further refining your topic specification tree. 
    See the docs for more info. 
    '''
    
    Policies._msgDataArgName = commonName
    if stage <= 1:
        Policies._msgDataProtocol = 'dataArg'
