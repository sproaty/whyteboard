'''
Everything regarding the concept of topic. 

Note that name 
can be in the 'dotted' format 'topic.sub[.subsub[.subsubsub[...]]]' 
or in tuple format ('topic','sub','subsub','subsubsub',...). E.g.
'nasa.rocket.apollo13' or ('nasa', 'rocket', 'apollo13').

Copyright Oliver Schoenborn, 2008-
'''

from weakref import ref as weakref

from pubsubconf import \
    Policies
    
from listener import \
    Listener, \
    ListenerValidator

from topicutils import \
    smartDedent, \
    stringize, \
    tupleize, \
    TopicNameInvalid

from topicargspec import \
    ArgsInfo, \
    verifySubset, \
    topicArgsFromCallable, \
    InvalidArgsSpec, \
    MissingReqdArgs, \
    UnknownOptArgs
    

# just want something unlikely to clash with user's topic names
ALL_TOPICS = '!__ALL_TOPICS__!' 


class _TopicDefnProvider:
    '''
    Stores a list of topic definition providers. Gets the 
    argument specification and description for given topics, 
    as returned by one of providers added.
    '''
    
    def __init__(self):
        self.__providers = []
        
    def addProvider(self, provider):
        if provider not in self.__providers:
            self.__providers.append(provider)
    
    def clear(self):
        self.__providers = []
        
    def getSubSpec(self, topicNameTuple):
        for provider in self.__providers:
            argsDocs, required = provider.getSubSpec(topicNameTuple)
            
            if argsDocs is not None:
                verifySubset(argsDocs.keys(), required, topicNameTuple, 
                    "arg list, or _required too large")
                return argsDocs, required
            
        if Policies._raiseOnTopicUnspecified:
            raise TopicUnspecifiedError(topicNameTuple, self.__providers)
            
        return None, None
    
    def getDescription(self, topicNameTuple):
        for provider in self.__providers:
            desc = provider.getDescription(topicNameTuple)
            if desc is not None:
                return desc
            
        if Policies._raiseOnTopicUnspecified:
            raise TopicUnspecifiedError(topicNameTuple, self.__providers)
        
        return None
    

# ---------------------------------------------------------

class ListenerNotValidatable(RuntimeError):
    def __init__(self):
        RuntimeError.__init__('Topics args not set yet, cannot validate listener')
    
class TopicAlreadyDefined(RuntimeError):
    def __init__(self, msg):
        RuntimeError.__init__(self, msg)

class UndefinedTopic(RuntimeError):
    def __init__(self, topicName):
        RuntimeError.__init__(self, 'Topic "%s" doesn\'t exist' % topicName)
        
class UndefinedSubtopic(RuntimeError):
    def __init__(self, parentName, subName):
        msg = 'Topic "%s" doesn\'t have "%s" as subtopic'
        RuntimeError.__init__(self, msg % (parentName, subName))
        
class TopicUnspecifiedError(RuntimeError):
    def __init__(self, topicNameTuple, providers):
        if providers:
            msg = ("No topic specification for topic '%s' " % stringize(topicNameTuple)
                + "found from registered providers (%s)." % providers)
        else:
            msg = "No topic specification for topic '%s'."  % stringize(topicNameTuple)
        RuntimeError.__init__(self, msg + " See pub.newTopic(), pub.addTopicDefnProvider(), and/or pubsubconf.setTopicUnspecifiedFatal()")


# ---------------------------------------------------------

ARGS_SPEC_NONE    = ArgsInfo.SPEC_NONE     # specification not given
ARGS_SPEC_SUBONLY = ArgsInfo.SPEC_SUBONLY  # only subtopic args specified
ARGS_SPEC_ALL     = ArgsInfo.SPEC_ALL      # all args specified


# the root topic of all topics is different based on messaging protocol

def _getRootTopicSpecProtoKwargs():
    '''If using kwargs protocol, then root topic takes no args.'''
    argsDocs = None
    reqdArgs = ()
    return argsDocs, reqdArgs

def _getRootTopicSpecProtoDataMsg():
    '''If using dataArg protocol, then root topic has one arg; 
    if Policies._msgDataArgName is something, then use it as arg name.'''
    argName = Policies._msgDataArgName or 'data'
    argsDocs = {argName : 'data for message sent'}
    reqdArgs = (argName,)
    return argsDocs, reqdArgs

_rootTopicSpecs = dict(
    kwargs  = _getRootTopicSpecProtoKwargs, 
    dataArg = _getRootTopicSpecProtoDataMsg)
_getRootTopicSpec = _rootTopicSpecs[ Policies._msgDataProtocol ]


class TopicManager:
    '''Manages the registry of all topics and creation/deletion
    of topics. All methods that start with an underscore are part 
    of the private API. Some argument names start with an 
    underscore to decrease the likelyhood that some names of 
    the **kwargs will clash with the library's argument names. '''
    
    def __init__(self):
        self._rootTopic = None # root of topic tree
        self._topicsMap = {} # registry of all topics
        self.__defnProvider = _TopicDefnProvider()

        self.__notifyOnNewTopic = False
        self.__notifyOnDelTopic = False
        self.__notifyOnDeadListener = False


        if self._rootTopic is None:
            argsDocs, reqdArgs = _getRootTopicSpec()
            self._rootTopic = \
                self.__createTopic((ALL_TOPICS,), desc='root of all topics', 
                    argsDocs=argsDocs, reqdArgs=reqdArgs, argsSpec=ARGS_SPEC_ALL)

    def addDefnProvider(self, provider):
        '''Register provider as topic specification provider. Whenever a 
        topic must be created, the first provider that has a specification
        for the created topic is used to initialize the topic. The given 
        provider must be an object that has a getDescription(topicNameTuple)
        and getArgs(topicNameTuple) that return a description string 
        and a pair (argsDocs, requiredArgs), respectively.'''
        self.__defnProvider.addProvider(provider)
    
    def clearDefnProviders(self):
        '''Remove all registered topic specification providers'''
        self.__defnProvider.clear()
        
    def _getDefnProvider_(self):
        return self.__defnProvider
    
    def newTopic(self, _name, _desc, _required=(), 
                 _argsSpec=ARGS_SPEC_SUBONLY, **args):
        '''Create a new topic of given _name, with description desc explaining 
        the topic (for documentation purposes). The **args defines the data 
        that can be given as part of messages of this topic: the keys define 
        what arguments names must be present for listeners of this topic, 
        whereas the values describe each argument (for documentation purposes).  

        Returns True only if a new topic was created, False if it already 
        existed identically (same description, same args -- in which case 
        the operation is a no-op). Otherwise raises ValueError. ''' 
        # check _name
        topicTuple = tupleize(_name)

        # create only if doesn't exist:
        nameDotted = stringize(_name)
        #print 'Checking for "%s"' % nameDotted
        if self._topicsMap.has_key(nameDotted):
            msg = 'Topic "%s" already exists' % nameDotted
            raise TopicAlreadyDefined(msg)
        
        # get parent in which to create topic
        path = topicTuple[:-1]
        if path:
            pathDotted = stringize(path)
            parent = self._topicsMap.get(pathDotted, None)
            if parent is None:
                msg = 'Parent topic "%s" does not exist, cannot create'
                raise UndefinedTopic(pathDotted)
        else:
            parent = self._rootTopic

        # ok to create!
        newTopicObj = self.__createTopic(
                          topicTuple, desc=_desc, 
                          parent=parent, argsSpec=_argsSpec,
                          argsDocs=args, reqdArgs=_required) 

        return newTopicObj

    def _newTopicFromTemplate_(self, topicName, desc, usingCallable=None):
        '''Return a new topic object created from protocol of 
        callable referenced by usingCallable. Creates missing parents.'''
        assert not self._topicsMap.has_key( stringize(topicName) )
        topicNameTuple = tupleize(topicName)
        parentObj = self.__createParentTopics(topicName)
        
        # now the final topic object, args from listener if provided
        allArgsDocs, required, argsSpec = None, None, ARGS_SPEC_NONE
        if usingCallable is not None:
            allArgsDocs, required = topicArgsFromCallable(usingCallable)
            argsSpec=ARGS_SPEC_ALL
            
        # if user description exists, use it rather than desc:
        desc = self.__defnProvider.getDescription(topicNameTuple) or desc
            
        return self.__createTopic(
            topicNameTuple, desc,
            parent=parentObj, argsSpec=argsSpec, 
            argsDocs=allArgsDocs, reqdArgs=required)

    def _newTopicNoSpec_(self, topicName, desc):
        '''Create an unspecified topic'''
        return self._newTopicFromTemplate_(topicName, desc)

    def delTopic(self, name):
        '''Undefines the named topic. Returns True if the subtopic was 
        removed, false otherwise (ie the topic doesn't exist). Also 
        unsubscribes any listeners of topic. Note that it must undefine 
        all subtopics to all depths, and unsubscribe their listeners. '''
        # find from which parent the topic object should be removed
        dottedName = stringize(name)
        try:
            obj = weakref( self._topicsMap[dottedName] )
        except KeyError:
            return False
            
        assert obj().getName() == dottedName
        # notification must be before deletion in case 
        if self.__notifyOnDelTopic:
            Policies._notificationHandler.notifyDelTopic(dottedName)
        
        obj()._undefineSelf_(self._topicsMap)
        assert obj() is None

        return True

    def getTopic(self, name):
        '''Get the Topic instance that corresponds to the given topic name 
        path. Raises an UndefinedTopic or UndefinedSubtopic error if the 
        path cannot be resolved. '''
        if not name:
            raise TopicNameInvalid(name, 'Empty topic name not allowed')
        topicNameDotted = stringize(name)
        obj = self._topicsMap.get(topicNameDotted, None)
        if obj is not None:
            return obj
        
        # NOT FOUND! Determine what problem is and raise accordingly:
        # find the closest parent up chain that does exists:
        parentObj, subtopicNames = self.__getClosestParent(topicNameDotted)
        assert subtopicNames
        
        subtopicName = subtopicNames[0]
        if parentObj is self._rootTopic:
            raise UndefinedTopic(subtopicName)

        raise UndefinedSubtopic(parentObj.getName(), subtopicName)

    def getTopicOrNone(self, name):
        '''Get the named topic, or None if doesn't exist'''
        name = stringize(name)
        obj = self._topicsMap.get(name, None)
        return obj
    
    def getTopics(self, listener):
        '''Get the list of Topic objects that given listener has 
        subscribed to. Keep in mind that the listener can get 
        messages from sub-topics of those Topics.'''
        assocTopics = []
        for topicObj in self._topicsMap.values():
            if topicObj.hasListener(listener):
                assocTopics.append(topicObj)
        return assocTopics        
        
    def setNotification(self, newTopic=None, delTopic=None, deadListener=None):
        '''See pub.setNotification() for docs. '''
        # create special topics if not already done
        if newTopic or delTopic or deadListener: # otherwise topics not needed
            if Policies._notificationHandler is None:
                raise RuntimeError('Must call pubsubconf.setNotificationHandler() first' )
        
        if newTopic is not None:
            self.__notifyOnNewTopic = newTopic
        if delTopic is not None:
            self.__notifyOnDelTopic = delTopic
        if deadListener is not None:
            self.__notifyOnDeadListener = deadListener

    def __getClosestParent(self, topicNameDotted):
        subtopicNames = []
        headTail = topicNameDotted.rsplit('.', 1)
        while len(headTail) > 1:
            parentName = headTail[0]
            subtopicNames.insert( 0, headTail[1] )
            obj = self._topicsMap.get( parentName, None )
            if obj is not None:
                return obj, subtopicNames
            
            headTail = parentName.rsplit('.', 1)
            
        subtopicNames.insert( 0, headTail[0] )
        return self._rootTopic, subtopicNames
    
    def __onDeadListener(self, topicObj, listener):
        '''This has to get called by topicObj when a listener subscribed to 
        topicObj has died in case there are other listeners who want to know
        when listeners die. Will send a message of topic 
        topics.pubsub.deadListener if that notification is on. '''
        if self.__notifyOnDeadListener:
            Policies._notificationHandler.notifyDeadListener(topicObj, listener)

    def __createParentTopics(self, topicName):
        assert self.getTopicOrNone(topicName) is None
        parentObj, subtopicNames = self.__getClosestParent(stringize(topicName))
        
        # will create subtopics of parentObj one by one from subtopicNames
        if parentObj is self._rootTopic:
            nextTopicNameList = []
        else:
            nextTopicNameList = list(parentObj.getNameTuple())
        desc = 'Defined from listener of subtopic "%s"' % stringize(topicName)
        for name in subtopicNames[:-1]:
            nextTopicNameList.append(name)
            parentObj = self.__createTopic(
                tuple(nextTopicNameList), 
                desc = desc, 
                parent = parentObj, 
                argsSpec = ARGS_SPEC_NONE)
            
        return parentObj
    
    def __createTopic(self, topicTuple, desc, parent=None, 
                      argsSpec=None, argsDocs=None, reqdArgs=()):
        '''Actual topic creation step. Adds new Topic instance
        to topic map, and sends notification message (of topic 
        'pubsub.newTopic') about new topic having been created.'''
        #print '__createTopic:', topicTuple, parent and parent.getNameTuple(), args, reqdArgs, argsSpec
        argsDocs = argsDocs or {}
        attrName = topicTuple[-1]
        if parent is not None and hasattr(parent, attrName):
            reason = '"%s" is an attribute of Topic class' % attrName
            raise TopicNameInvalid(topicTuple, reason)
        
        newTopicObj = Topic(self, topicTuple, desc, 
                            parent=parent, argsSpec=argsSpec, 
                            reqdArgs=reqdArgs, msgArgs=argsDocs, 
                            deadListenerCB=self.__onDeadListener)
        # sanity checks:
        assert not self._topicsMap.has_key(newTopicObj.getName())
        if parent is self._rootTopic:
            assert len( newTopicObj.getNameTuple() ) == 1
        else:
            assert parent.getNameTuple() == newTopicObj.getNameTuple()[:-1]
        self._topicsMap[ newTopicObj.getName() ] = newTopicObj
        assert topicTuple == newTopicObj.getNameTuple()
        
        if self.__notifyOnNewTopic:
            Policies._notificationHandler.notifyNewTopic(
                newTopicObj, desc, reqdArgs, argsDocs)
        
        return newTopicObj
    
    def __validateHierarchy(self, topicTuple):
        '''Check that names in topicTuple are valid: no spaces, not empty.
        Raise ValueError if fails check. E.g. ('',) and ('a',' ') would 
        both fail, but ('a','b') would be ok. '''
        for indx, topic in enumerate(topicTuple):
            errMsg = None
            if topic is None:
                topicName = list(topicTuple)
                topicName[indx] = 'None'
                errMsg = 'None at level #%s'
                
            elif not topic: 
                topicName = stringize(topicTuple)
                errMsg = 'empty element at level #%s'
            
            elif topic.isspace():
                topicName = stringize(topicTuple)
                errMsg = 'blank element at level #%s'
                
            if errMsg:
                raise TopicNameInvalid(topicName, errMsg % indx)


class PublisherMixinKwargs:
    def publish(self, msgKwargs):
        '''Send the message for given topic with data in msgKwargs.
        This sends message to listeners of of parent topics as well. 
        Note that at each level, msgKwargs is filtered so only those 
        args that are defined for the topic are sent to listeners. '''
        # check valid args; only possible if topic spec complete, otherwise
        # will check first complete parent (assumes we are
        # traversing topic tree up from children to parents):
        argsChecked = False
        if self.argsSpecComplete():
            self.argsSpec.check(msgKwargs)
            argsChecked = True
            
        fullTopic = self
        filteredArgs = msgKwargs
        topicObj = self
        while topicObj is not None:
            if topicObj.hasListeners():
                # need to filter the args since not all args accepted
                filteredArgs = topicObj.argsSpec.filterArgs(filteredArgs)

                # if no check of args yet, do it now:
                if not argsChecked:
                    topicObj.argsSpec.check(filteredArgs)
                    argsChecked = True
                    
                # now send message data to each listener for current topic:
                for listener in topicObj.getListeners():
                    try:
                        if listener.acceptsAllKwargs:
                            listener(fullTopic, msgKwargs)
                        else:
                            listener(fullTopic, filteredArgs)
                            
                    except Exception, exc: 
                        # if exception handling is on, handle, otherwise re-raise
                        handler = Policies._listenerExcHandler
                        if handler:
                            handler( listener.name(instance=True) )
                        else:
                            raise
                    
            # done for this topic, continue up branch to parent towards root
            topicObj = topicObj.getParent()


class PublisherMixinDataMsg:
    def publish(self, data):
        '''Send the message for given topic with data.
        This sends message to listeners of parent topics as well. 
        If an exception is raised in a listener, the publish is 
        aborted, except if there is a handler (see 
        pubsubconf.setListenerExcHandler).'''
        fullTopic = self
        topicObj = self
        while topicObj is not None:
            if topicObj.hasListeners():
                # now send message data to each listener for current topic:
                for listener in topicObj.getListeners():
                    try:
                        listener(fullTopic, data)
                            
                    except Exception, exc: 
                        # if exception handling is on, handle, otherwise re-raise
                        handler = Policies._listenerExcHandler
                        if handler:
                            handler( listener.name(instance=True) )
                        else:
                            raise
                    
            # done for this topic, continue up branch to parent towards root
            topicObj = topicObj.getParent()


_publisherMixins = dict(
    kwargs  = PublisherMixinKwargs, 
    dataArg = PublisherMixinDataMsg)
PublisherMixin = _publisherMixins[ Policies._msgDataProtocol ]


class Topic(PublisherMixin):
    '''
    Represent a message topic. This keeps track of which  
    call arguments (msgArgs) can be given as message data to subscribed
    listeners, it supports documentation of msgArgs and topic itself,
    and allows Python-like access to subtopics (e.g. A.B is subtopic
    B of topic A) and keeps track of listeners of topic. 
    '''
    
    UNDERSCORE = '_' # topic name can't start with this
    
    class InvalidName(ValueError):
        '''
        Raised when attempt to create a topic with name that is 
        not allowed (contains reserved characters etc).
        '''
        def __init__(self, name, reason):
            msg = 'Invalid topic name "%s": %s' % (name or '', reason)
            ValueError.__init__(self, )

    def __init__(self, topicMgr, nameTuple, description, parent=None,
                 argsSpec=None, reqdArgs=(), msgArgs=None, deadListenerCB=None):
        '''Specify the name, description, and parent of this Topic. Any remaining 
        keyword arguments (which will be put in msgArgs) describe the arguments that 
        a listener of this topic must support (i.e., the key is the argument name and
        the value is a documentation string explaining what the argument is for). 
        The reqdArgs is an optional list of names identifying which variables in 
        msgArgs keys are required arguments. E.g. 
        
            Topic(('a','b'), 'what is topic for', parentTopic, _reqdArgs=('c','d'), 
                c='what is c for', d='what is d for', e='what is e for')
            
        would create a Topic whose listeners would have to be of the form
        
            callable(c, d, e=...)
            
        ie 
            callable(c, d, e=...)
            callable(self, c, d, e=..., **kwargs) (method)
            
        would all be valid listeners but 
        
            callable(c, e=...) # error: required d is missing
            callable(c, d, e)  # error: e is optional
        
        would not be valid listeners of this topic. 
        
        The _useKwa is only used by the package to indicate whether the arguments are
        specified as part of __init__ (there is no other way since msgArgs cannot be None). 
        '''
        self.__validateName(nameTuple, parent is None)
        self.__tupleName = nameTuple

        self.__validator    = None
        self.__listeners    = []
        self.__deadListenerCB = deadListenerCB
        
        # specification: 
        self.__description  = None
        self.setDescription(description)
        getArgsSpec = topicMgr._getDefnProvider_().getSubSpec
        self.__msgArgs      = ArgsInfo(getArgsSpec, nameTuple, 
                                       parent, msgArgs, reqdArgs, argsSpec) 
        if self.__msgArgs.isComplete():
            self.__finalize()
        self.argsSpec = self.__msgArgs
        
        # now that we know the args are fine, we can link to parent
        self.__parentTopic = None
        if parent is None:
            assert self.isSendable()
        else:
            self.__parentTopic = weakref(parent)
            parent.__setSubtopic( self.getTailName(), self )
        
    def setDescription(self, desc):
        '''Set the 'docstring' of topic'''
        self.__description = desc or 'UNDOCUMENTED'
        
    def getDescription(self):
        '''Return the 'docstring' of topic'''
        return smartDedent(self.__description)
        
    def argsSpecComplete(self):
        '''Return true only if topic's spec is complete'''
        return self.__msgArgs.isComplete()
    
    def getArgs(self):
        '''Returns a triplet (reqdArgs, optArgs, isComplete) where reqdArgs
        is the names of required message arguments, optArgs same for optional
        arguments, and isComplete is same as would be returned from 
        self.argsSpecComplete().'''
        return (self.__msgArgs.allRequired, 
                self.__msgArgs.allOptional,
                self.__msgArgs.isComplete())
    
    def getArgDescriptions(self):
        '''Get a **copy** of the topic's kwargs given at construction time. 
        Returns None if args not described yet. '''
        if self.__parentTopic is None:
            return self.__msgArgs.subArgsDocs.copy()
        parentDescs = self.__parentTopic().getArgDescriptions()
        parentDescs.update( self.__msgArgs.subArgsDocs or {})
        return parentDescs
    
    def isSendable(self):
        '''Return true if messages can be sent for this topic'''
        return self.__validator is not None
    
    def getName(self):
        '''Return dotted form of full topic name'''
        return stringize(self.__tupleName)
        
    def getNameTuple(self):
        '''Return tuple form of full topic name'''
        return self.__tupleName
    
    def getTailName(self):
        '''Return the last part of the topic name (has no dots)'''
        name = self.__tupleName[-1]
        if name is ALL_TOPICS:
            return 'ALL_TOPICS'
        assert name.find('.') < 0
        return name
    
    def getParent(self):
        '''Get Topic object that is parent of self 
        (i.e. self is a subtopic of parent).'''
        if self.__parentTopic is None:
            return None
        return self.__parentTopic()

    def hasSubtopic(self, name=None):
        '''Return true only if name is a subtopic of self. If name not
        specified, return true only if self has at least one subtopic.'''
        if name is None:
            for attr in self.__dict__.values():
                if isinstance(attr, Topic):
                    return True
            return False
        
        elif hasattr(self, name):
            return isinstance(getattr(self, name), Topic)
        
        return False
        
    def getSubtopics(self):
        '''Get a list of Topic instances that are subtopics of self.'''
        st = []
        for attr in self.__dict__.values():
            if isinstance(attr, Topic):
                st.append(attr)
        return st
    
    def getNumListeners(self):
        '''Return number of listeners currently subscribed to topic. This is
        different from number of listeners that will get notified since more
        general topics up the topic tree may have listeners.'''
        return len(self.__listeners)

    def hasListener(self, listener):
        '''Return true if listener is subscribed to this topic.'''
        return listener in self.__listeners

    def hasListeners(self):
        '''Return true if there are any listeners subscribed to 
        this topic, false otherwise.'''
        return self.__listeners != []
    
    def getListeners(self):
        '''Get a **copy** of Listener objects for listeners 
        subscribed to this topic.'''
        return self.__listeners[:]
        
    def validate(self, listener):
        '''Same as self.isValid(listener) but raises ListenerInadequate
        instead of returning False. Returns nothing. '''
        if not self.isSendable():
            raise ListenerNotValidatable()
        return self.__validator.validate(listener)
    
    def isValid(self, listener):
        '''Return True only if listener can subscribe to messages of 
        this topic, otherwise returns False. Raises ListenerNotValidatable 
        if not self.isSendable().'''
        if not self.isSendable():
            raise ListenerNotValidatable()
        return self.__validator.isValid(listener)
        
    def __call__(self, subtopicName):
        '''Return the Topic object that represents the subtopic of given name'''
        return getattr(self, subtopicName)
    
    # Impementation API:
    
    def _updateArgsSpec_(self, usingCallable, topicMgr):
        '''Update the argument spec of topic using given callable. '''
        assert self.__parentTopic is not None
        assert not self.argsSpecComplete()
        
        argsDocs, required = topicArgsFromCallable(usingCallable)
        getArgsSpec = topicMgr._getDefnProvider_().getSubSpec
        self.__msgArgs = ArgsInfo(getArgsSpec, self.getName(), self.__parentTopic(), 
                                  argsDocs, required, ARGS_SPEC_ALL)
        self.argsSpec = self.__msgArgs
        # validate that our new spec agrees with complete children
        for child in self.getSubtopics():
            # get difference between child and our parent
            # this must contain our difference from our parent
            pass
        
        if self.__msgArgs.isComplete():
            self.__finalize()
            
    def _subscribe_(self, listener):
        '''This method must only be called from within pubsub, as 
        indicated by the surrounding underscores.'''
        # add to list if not already there:
        if listener in self.__listeners:
            assert self.isSendable()
            idx = self.__listeners.index(listener)
            return self.__listeners[idx], False
            
        else:
            if not self.isSendable():
                raise RuntimeError('Incomplete topic, can\'t register listeners')
            else:
                argsInfo = self.__validator.validate(listener)
                weakListener = Listener(
                    listener, argsInfo, onDead=self.__onDeadListener)
            self.__listeners.append(weakListener)
            return weakListener, True
            
    def _unsubscribe_(self, listener):
        try:
            idx = self.__listeners.index(listener)
        except ValueError:
            return None

        tmp = self.__listeners.pop(idx)
        tmp._unlinkFromTopic_()
        return tmp
        
    def _unsubscribeAllListeners_(self, filter=None):
        '''Clears list of subscribed listeners. If filter is given, it must 
        be a function that takes a listener and returns true if the listener
        should be unsubscribed. Returns the list of listeners that were 
        unsubscribed.'''
        index = 0
        unsubd = []
        for listener in self.__listeners[:] :
            if filter is None or filter(listener):
                listener._unlinkFromTopic_()
                assert listener is self.__listeners[index]
                del self.__listeners[index] 
                unsubd.append(listener)
            else:
                index += 1
            
        return unsubd
        
    def _undefineSelf_(self, topicsMap):
        if self.__parentTopic is not None:
            delattr(self.__parentTopic(), self.__tupleName[-1])
        self.__undefineSelf(topicsMap)

    def __finalize(self):
        '''Change the arguments of topic. They can be different from those set (if any) 
        at construction time, however any subscribed listeners must remain valid with 
        new args/required otherwise a ValueError exception is raised. '''            
        assert not self.isSendable()
        #assert self.__msgArgs.isFinal()

        # must make sure can adopt a validator
        required = self.__msgArgs.allRequired
        optional = self.__msgArgs.allOptional
        self.__validator = ListenerValidator(required, list(optional) )
        assert not self.__listeners 
    
    def __undefineSelf(self, topicsMap):
        '''Unsubscribe all our listeners, remove all subtopics from self,
        then detach from parent. '''
        #print 'Remove %s listeners (%s)' % (self.getName(), self.getNumListeners())
        self._unsubscribeAllListeners_()
        self.__parentTopic = None
        
        for subName, subObj in self.__dict__.items(): # COPY since modify!!
            if isinstance(subObj, Topic) and not subName.startswith('_'):
                #print 'Unlinking %s from parent' % subObj.getName()
                delattr(self, subName)
                subObj.__undefineSelf(topicsMap)
            
        del topicsMap[self.getName()]

    def __validateName(self, nameTuple, isRootTopic):
        '''Raise TopicNameInvalid if nameTuple not valid as topic name.'''
        if not nameTuple: 
            reason = 'name tuple must have at least one item!'
            raise TopicNameInvalid(None, reason)
        
        tailName = nameTuple[-1]
        if not tailName:
            reason = 'can\'t contain empty string or None'
            raise TopicNameInvalid(None, reason)
        if tailName.startswith(self.UNDERSCORE):
            reason = 'must not start with "%s"' % self.UNDERSCORE
            raise TopicNameInvalid(tailName, reason)
        if tailName == ALL_TOPICS and not isRootTopic:
            reason = 'only root topic can contain "%s"' % ALL_TOPICS
            raise TopicNameInvalid(tailName, reason)
        assert tailName != ALL_TOPICS or isRootTopic

    def __setSubtopic(self, attrName, topicObj):
        '''Link self to a Topic instance via self.attrName. Always succeeds.'''
        assert topicObj.__parentTopic() is self
        setattr(self, attrName, topicObj)
        
    def __onDeadListener(self, weakListener):
        '''One of our subscribed listeners has died, so remove it and notify others'''
        ll = self.__listeners.index(weakListener)
        listener = self.__listeners[ll]
        llID = str(listener)
        del self.__listeners[ll]
        self.__deadListenerCB(self, listener)

    def __str__(self):
        return "%s, %s" % (self.getName(), self.getNumListeners())
        

