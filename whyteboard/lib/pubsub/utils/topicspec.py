'''
Provides classes useful for specifying topics by lookup. The classes
TopicTreeDefnSimple and TopicTreeDefnRobust can be derived into 
topic trees and given to pubsub's addTopicDefnProvider() function. 
Doing so will cause pubsub to check the provided topic tree for the 
topic documentation string and topic message data specification (TMD)
whenever a new topic is created, which typically would happen in 
subscribe() and sendMessage() the first time they are called with 
a topic unknown to pubsub. 

A printout of the tree using pubsub.utils.printTreeDocs() will show you 
which topics your application has created in a particular run, which 
ones are undocumented (usually an indication of typo in topic name), 
and what message data is expected/required for each topic. 
 
Usage: derive from TopicTreeDefnSimple or TopicTreeDefnRobust and 
add class data members, nested classes and class documentation to 
represent the TMD and topic documentation. Also use the '_required'
field to specify which TMD are required arguments to any sendMessage()
for associated topic. 

Both TopicTreeDefnSimple and TopicTreeDefnRobust show example of 
defining the same topic tree, which is a two step process: 

1. Define topic hierarchy by deriving from one of the TopicTreeDefn* classes
2. Call pub.addTopicDefnProvider( TopicTreeDefnSimple() ) somewhere in your 
   application, usually in the startup script.
        
The sendMessage() calls below would be valid for the given topic 
tree definition:

sendMessage('topic1', arg1=..., arg2=..., arg3=...)
sendMessage('topic1', arg1=..., arg2=...)

sendMessage('topic1.subtopic1', arg1=..., arg2=...)
sendMessage('topic1.subtopic1', arg1=..., arg2=..., arg3=...)
sendMessage('topic1.subtopic1', arg1=..., arg2=..., arg3a=...)
sendMessage('topic1.subtopic1', arg1=..., arg2=..., arg3=..., arg3a=...)

sendMessage('topic1.subtopic2', arg1=..., arg2=..., arg3b=...)
sendMessage('topic1.subtopic2', arg1=..., arg2=..., arg3=..., arg3b=...)

would work on it too, it could be called in the 
sendMessage(arg1=..., arg2=..., arg3=...)

The following would be invalid:

sendMessage('topic1', arg1=...): required arg2 missing
sendMessage('topic1.subtopic1', arg2=..., arg3=..., arg3a=...): required arg1 missing
sendMessage('topic1.subtopic2', arg1=..., arg2=...): required arg3b missing

Note that you can easily create your own defn provider by deriving from 
ITopicTreeDefnProvider or TopicTreeDefnBase. 
'''

from inspect import isclass

__all__ = ('ITopicTreeDefnProvider', 'TopicTreeDefnSimple', 
           'TopicTreeDefnRobust', 'TopicArg', 'TopicDefn')


class ITopicTreeDefnProvider:
    '''
    Any topic tree definition provider must provide the following interface
    '''
    
    def getSubSpec(self, topicNameTuple):
        '''Get the given topic's message data specification. This 
        returns a pair (argsDocs, requiredArgs) where first item is a map
        of argument names and documentation for each arg, and second item
        is a list of the keys in argsDocs that represent topic arguments that
        are required when pubsub.sendMessage() is called. Returns (None, None)
        if no specification is available.
        
        Note that only the topic's sub-arguments are returned, i.e. if topic is 
        'a.b' and 'a' has arguments 'arg1', 'arg2' while 'a.b' adds
        sub-arguments 'arg3', then this method returns an argsDocs
        having only 'arg3' as key. '''
        raise NotImplementedError
    
    def getDescription(self, topicNameTuple):
        '''Return the description string for given topic, or None 
        if none available.'''
        raise NotImplementedError
    
        
class TopicTreeDefnBase (ITopicTreeDefnProvider):
    REQUIRED_ATTR = '_required'
    HAS_ARGSSPEC_ATTR = '_hasSpecification'
    argsSpecified = []
    
    def getSubSpec(self, topicNameTuple):
        obj = self.__findTopicDefn(topicNameTuple)
        if not self.__hasSpecification(topicNameTuple, obj):
            return None, None
        
        # set description and args
        argsDocs = dict( [(arg, str(desc))
                      for (arg, desc) in obj.__dict__.iteritems() 
                      if (not arg.startswith('_')) and self._isTopicArg(desc)] )
        
        # set required
        required = getattr(obj, self.REQUIRED_ATTR, ())
        if isinstance(required, str):
            required = (required,)
        else: # make sure we have a tuple not a list 
            required = tuple(required) 
        
        # ok: 
        return argsDocs, required
        
    def getDescription(self, topicNameTuple):
        obj = self.__findTopicDefn(topicNameTuple)
        if obj is None:
            return None
        return obj.__doc__
    
    def _isTopicDefn(self, attr):
        '''This can be overridden to change how the tree should determine 
        if an attribute is a topic definition. Should return True if 
        attr qualifies as a topic definition (ie it has a documentation 
        string, class attributes that define its message arguments, and 
        nested classes that define subtopics), False otherwise. Called
        by getDescription() and getSubSpec().'''
        raise NotImplementedError

    def _isTopicArg(self, attr):
        '''This can be overridden to change how the tree should determine 
        if an attribute is a topic argument. Should return True if 
        attr qualifies as a topic argument (ie it represents an argument
        name and it documentation), False otherwise. Called
        by getSubSpec().'''
        raise NotImplementedError

    def __hasSpecification(self, topicName, topicObj):
        '''Returns true only if topicObj is not None and has an 
        argument specification.'''
        if topicObj is None:
            return False
        if topicObj.__doc__ is None:
            return False
        if hasattr(topicObj, self.HAS_ARGSSPEC_ATTR):
            hasSpec = getattr(topicObj, self.HAS_ARGSSPEC_ATTR)
            print 'topic def for %s has %s=%s' % (topicName, self.HAS_ARGSSPEC_ATTR, hasSpec)
            return hasSpec
        if topicName in self.argsSpecified:
            print 'topic in argsSpecified list', topicName
            return True
        #print 'all ok, so defaults to has spec', topicName
        return True
            
    def __findTopicDefn(self, topicNameTuple):
        '''Find the topic definition object for given topic name.
        Returns the object, or None if not found.'''
        if not topicNameTuple:
            return None
        
        obj = self
        exists = True
        for name in topicNameTuple:
            obj = getattr(obj, name, None)
            exists = (obj is not None) and self._isTopicDefn(obj)
            if not exists:
                return None
            
        return obj


class TopicTreeDefnSimple(TopicTreeDefnBase):
    '''
    Subtopics are nested classes, TMD are class data members. 
    For instance: 
    
        class MyTopicTree(TopicTreeDefnSimple):
        
            class topic1:
                """Docs for topic1, several lines of it, 
                many many lines of it"""
                
                arg1 = "explain what arg1 is for"
                arg2 = "explain what arg2 is for"
                arg3 = "explain what arg3 is for"
                _required = ('arg1', 'arg2')
                
                class subtopic1:
                    """Docs for subtopic1, several lines of it, 
                    many many lines of it"""
                    
                    arg3a = "explain what arg3a is for"
        
                class subtopic2:
                    """Docs for subtopic2, several lines of it, 
                    many many lines of it"""
                    
                    arg3b = "explain what arg3b is for"
                    _required = 'arg3b'
                    
    The above example defines topics 'topic1', 'topic1.subtopic1' and 
    'topic1.subtopic2'. The module documentation describes how the
    above tree affects the validity of calls to sendMessage(). 
    '''

    def _isTopicDefn(self, attr):
        return isclass(attr)
    def _isTopicArg(self, attr):
        return isinstance(attr, str)


class TopicTreeDefnRobust(TopicTreeDefnBase):
    '''
    Subtopics are nested classes, TMD are class data members. 
    For instance: 
    
    class MyTopicTree(TopicTreeDefnRobust):
    
        class topic1(TopicDefn):
            """Docs for topic1, several lines of it, 
            many many lines of it"""
            
            arg1 = TopicArg("explain what arg1 is for")
            arg2 = TopicArg("explain what arg2 is for")
            arg3 = TopicArg("explain what arg3 is for")
            _required = ('arg1', 'arg2')
            
            class subtopic1(TopicDefn):
                """Docs for subtopic1, several lines of it, 
                many many lines of it"""
                
                arg3a = TopicArg("explain what arg3a is for")
    
            class subtopic2(TopicDefn):
                """Docs for subtopic2, several lines of it, 
                many many lines of it"""
                
                arg3b = TopicArg("explain what arg3b is for")
                _required = 'arg3b'
    '''
    
    def _isTopicDefn(self, attr):
        return isinstance(attr, TopicDefn)
    def _isTopicArg(self, attr):
        return isinstance(attr, TopicArg)


class TopicArg:
    '''Used to 'tag' a class attribute as a TMD, when using 
    TopicTreeDefnRobust as the base for topic tree definition. '''
    def __init__(self, desc):
        self.value = desc
    def __str__(self):
        return self.value
        

class TopicDefn: 
    '''Used to 'tag' a nested class a subtopic, when using 
    TopicTreeDefnRobust as the base for topic tree definition. '''
    pass

