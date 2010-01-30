'''
Low level functions and classes related to callables. 
'''

from inspect import getargspec, ismethod, isfunction, getmro


KWARG_TOPIC = 'msgTopic' # must NOT be changed
AUTO_ARG    = 'your listener wants topic name'


def getModule(obj):
    '''Get the module in which an object was defined. Returns '__main__' 
    if no module defined (which usually indicates either a builtin, or
    a definition within main script). '''
    if hasattr(obj, '__module__'):
        module = obj.__module__
    else:
        module = '__main__'
    return module


def getID(callable_):
    '''Get name and module name for a callable, ie function, bound 
    method or callable instance, by inspecting the callable. E.g. 
    getID(Foo.bar) returns ('Foo.bar', 'a.b') if Foo.bar was
    defined in module a.b. '''
    sc = callable_
    if ismethod(sc):
        module = getModule(sc.im_self)
        id = '%s.%s' % (sc.im_self.__class__.__name__, sc.im_func.func_name)
    elif isfunction(sc):
        module = getModule(sc)
        id = sc.__name__
    else: # must be a functor (instance of a class that has __call__ method)
        module = getModule(sc)
        id = sc.__class__.__name__
        
    return id, module


def getRawFunction(callable_):
    '''Given a callable, return (offset, func) where func is the
    function corresponding to callable, and offset is 0 or 1 to 
    indicate whether the function's first argument is 'self' (1)
    or not (0).'''
    firstArg = 0
    if isfunction(callable_):
        #print 'Function', getID(callable_)
        func = callable_
    elif ismethod(callable_):
        func = callable_
        #print 'Method', getID(callable_)
        firstArg = 1  # don't care about the self arg
    elif hasattr(callable_, '__call__'):
        #print 'Functor', getID(callable_)
        func = callable_.__call__
        firstArg = 1  # don't care about the self arg
    else:
        msg = 'type %s not recognized' % type(callable_)
        raise ValueError(msg)
    
    return firstArg, func

    
class ListenerInadequate(TypeError):
    '''
    Raised when an attempt is made to subscribe a listener to 
    a topic without satisfying the topic requirements.
    '''
    
    def __init__(self, msg, listener, *args):
        idStr, module = getID(listener)
        msg = 'Listener %s (module %s) inadequate: %s' % (idStr, module, msg)
        TypeError.__init__(self, msg)
        self.msg    = msg
        self.args   = args
        self.module = module
        self.idStr  = idStr
        
    def __str__(self):
        return self.msg


class ArgsInfo:
    '''
    Represent the "signature" or protocol of a listener in the context of 
    topics. 
    '''
    
    def __init__(self, args, firstArgIdx, defaultVals, acceptsAllKwargs=False):
        '''Args is the complete set of arguments as obtained form inspect.getargspec().
        The firstArgIdx points to the first item in args that is of use, so it is typically
        0 if listener is a function, and 1 if listener is a method. After initialization,
        the self.args will contain subset of args without first firstArgIdx items, 
        the self.numRequired will indicate number of required arguments, and 
        self.wantsTopic will be True only if listener indicated it wanted the topic 
        object to be auto-passed to it in a pubsub.sendMessage().
         
        Note that args may be different upon return.'''
        self.allArgs = args
        self.numRequired = None
        self.wantsTopic = None
        self.acceptsAllKwargs = acceptsAllKwargs
        defaultVals = list(defaultVals or ())
        self.__cleanup(firstArgIdx, defaultVals)

    def getRequiredArgs(self):
        return tuple( self.allArgs[:self.numRequired] )
    
    def __cleanup(self, firstArgIdx, defaultVals):
        '''Removes unnecessary items from args and defaultVals. 
        Returns a pair (num, wantTopic) where num is how many
        items in args represent the required arguments, and 
        wantTopic is True if args/defaultVals satisfied the 
        "wantTopic" condition. '''
        args = self.allArgs
        del args[0:firstArgIdx] # does nothing if firstArgIdx == 0
        
        self.numRequired = len(args) - len(defaultVals)
        assert self.numRequired >= 0
        
        # if listener wants topic, remove that arg from args/defaultVals
        self.wantsTopic = False
        if defaultVals is not None:
            wantTopicIdx = self.__isTopicWanted(defaultVals)
            if wantTopicIdx >= self.numRequired:
                del args[wantTopicIdx]
                del defaultVals[wantTopicIdx - self.numRequired]
                self.wantsTopic = True        
    
    def __isTopicWanted(self, defaults):
        '''Does the listener want topic of message? Returns < 0 if not, 
        otherwise return index of topic kwarg within args.'''
        args = self.allArgs
        firstKwargIdx = len(args) - len(defaults)
        try:
            findTopicArg = args.index(KWARG_TOPIC, firstKwargIdx)
                
        except ValueError:
            return -1
        
        topicKwargIdx = findTopicArg - firstKwargIdx
        if defaults[topicKwargIdx] != AUTO_ARG:
            return -1
        
        return findTopicArg
        

def getArgs(listener):
    '''Returns an instance of ArgsInfo for the given listener. '''
    # figure out what is the actual function object to inspect:
    try:
        firstArgIdx, func = getRawFunction(listener)
    except ValueError, exc:
        raise ListenerInadequate(str(exc), listener)

    (args, va, vkwa, defaultVals) = getargspec(func)
    return ArgsInfo(args, firstArgIdx, defaultVals, vkwa)


