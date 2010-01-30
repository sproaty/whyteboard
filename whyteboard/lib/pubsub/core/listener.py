'''
Topic listeners are callables that satisfy the minimum requirements 
for the topic of interest. The Listener class aggregates 
the callable with other useful info, such as whether the 
listener accepts **kwargs, a more 'human friendly' 
name for the listener. 

Notes:
- A Listener instance
  holds its callable only by weak reference so it doesn't prevent the 
  callable from being garbage collected when no longer in use by the 
  application.  
- Listeners subscribing to a Topic are validated for compliance 
  with the topic's TMAS (topic message argument specification). 
  Compliance can be configured via pubsubconf.setListenerValidator(). 
'''

from weakref import ref as weakref
from types   import InstanceType
from inspect import getargspec, ismethod, isfunction, getmro

from pubsubconf import Policies

import weakmethod
from callables import \
    getID, getRawFunction, getArgs,\
    ListenerInadequate, \
    ArgsInfo, \
    KWARG_TOPIC as _KWARG_TOPIC, \
    AUTO_ARG as _AUTO_ARG


class Message:
    """
    A simple container object for the two components of a message: the 
    topic and the user data. An instance of Message is given to your 
    listener when called by sendMessage(topic). The data is accessed
    via the 'data' attribute, and can be type of object. 
    """
    def __init__(self, topicNameTuple, data):
        self.topic = topicNameTuple
        self.data  = data

    def __str__(self):
        return '[Topic: '+`self.topic`+',  Data: '+`self.data`+']'


class Listener:
    '''
    Represent a listener of messages of a given Topic. Each 
    Listener has a name and module, determined via introspection. 
    
    Note that listeners that have 'msgTopic=AUTO_ARG' as a kwarg will 
    be given the topic object for the message when called by 
    a sendMessage(). 
    '''
    
    KWARG_TOPIC = _KWARG_TOPIC
    AUTO_ARG = _AUTO_ARG
    Validator = None
    
    def __init__(self, callable_, argsInfo, onDead=None):
        '''Use callable_ as a listener of topicName. The argsInfo is the 
        return value from a Validator, ie an instance of callables.ArgsInfo.
        If given, the onDead will be called if/when callable_ gets
        garbage collected (callable_ is held only by weak reference). '''
        # set call policies
        self.acceptsAllKwargs = argsInfo.acceptsAllKwargs
        
        self.__wantsTopic = argsInfo.wantsTopic
        if onDead is None:
            self._callable = weakmethod.getWeakRef(callable_)
        else:
            self._callable = weakmethod.getWeakRef(callable_, self.__notifyOnDead)
        self.__onDead = onDead
        
        # save identity now in case callable dies:
        name, mod = getID(callable_)   #
        self.__nameID = name
        self.__module = mod 
        self.__id     = str(id(callable_))[-4:] # only last four digits of id
    
    def __call__(self, *args, **kwargs):
        raise NotImplementedError
    
    def name(self, instance=True):
        '''Return a human readable name for listener. If instance is True, 
        then append part of the id(callable_) given at construction (for 
        uniqueness). Note that the id() was saved at construction time so 
        return value is not necessarily unique if the callable has 
        died (because id's can be re-used after garbage collection).'''
        if instance:
            return '%s_%s'  % (self.__nameID, self.__id)
        else:
            return self.__nameID
    
    def module(self):
        '''Get the module in which callable type/class was defined.'''
        return self.__module

    def getCallable(self):
        '''Get the listener that was given at construction. Note that 
        this could be None if it has been garbage collected (e.g. if it was 
        created as a wrapper of some other callable, and not stored 
        locally).'''
        if self._callable is None:
            return None
        else:
            return self._callable()

    def isDead(self):
        '''Return True if this listener died (has been garbage collected)'''
        return self._callable is None
    
    def _unlinkFromTopic_(self):
        '''Tell self that it is no longer used by a Topic. This allows 
        to break some cyclical references.'''
        self.__onDead = None
        

    def __callWhenDead(self, actualTopic, *args, **kwargs):
        raise RuntimeError('BUG: Dead Listener called, still subscribed!')
    
    def __notifyOnDead(self, ref):
        '''This gets called when listener weak ref has died. Propagate 
        info to Topic).'''
        notifyDeath = self.__onDead
        self._unlinkFromTopic_()
        self._callable = None
        self.__call__ = self.__callWhenDead
        if notifyDeath is not None:
            notifyDeath(self)

    def __eq__(self, rhs):
        '''Compare for equality to rhs. This returns true if id(rhs) is 
        same as id(self) or id(callable in self). '''
        if hasattr(rhs,'_Listener__nameID'): 
            return self is rhs
        else:
            if self._callable is None:
                raise RuntimeError('BUG: Comparing a dead Listener!')
                
            return self._callable() == rhs
            
    def __str__(self):
        '''String rep is the callable'''
        return self.__nameID


class ListenerKwargs(Listener):
    def __call__(self, actualTopic, kwargs):
        '''Call the listener with **kwargs. Note that it raises RuntimeError 
        if listener is dead. Should always return True (False would require
        the callable_ be dead but self hasn't yet been notified of it...).'''
        cb = self._callable()
        if cb:
            if self._Listener__wantsTopic:
                cb(msgTopic=actualTopic, **kwargs)
            else:
                cb(**kwargs)
            return True
        else:
            return False


class ListenerDataMsg(Listener):
    def __call__(self, actualTopic, data):
        '''Call the listener with data. Note that it raises RuntimeError 
        if listener is dead. Should always return True (False would require
        the callable_ be dead but self hasn't yet been notified of it...).'''
        cb = self._callable()
        if cb:
            msg = Message(actualTopic.getNameTuple(), data)
            if self._Listener__wantsTopic:
                cb(msg, msgTopic=actualTopic)
            else:
                cb(msg)
            return True
        else:
            return False


def isValid(listener, topicReqdArgs, topicOptArgs):
    '''Return true only if listener can subscribe to messages where
    topic has kwargs keys topicKwargKeys and required args names topicArgs. 
    Just calls validate() in a try-except clause.'''
    validator = listener.Validator(topicReqdArgs, topicOptArgs)
    try:
        validator.validate(listener)
        return True
    except ListenerInadequate:
        return False


class Validator:
    '''
    Validates listeners. It checks whether the listener given to 
    validate() method complies with required and optional arguments
    specified for topic. 
    '''
    
    def __init__(self, topicArgs, topicKwargs):
        '''topicArgs is a list of argument names that will be required when sending 
        a message to listener. Hence order of items in topicArgs matters. The topicKwargs
        is a list of argument names that will be optional, ie given as keyword arguments
        when sending a message to listener. The list is unordered. '''
        self.topicArgs   = topicArgs
        self.topicKwargs = topicKwargs
        
    def validate(self, listener):
        '''Validate that listener satisfies the requirements of 
        being a topic listener, if topic's kwargs keys are topicKwargKeys
        (so only the list of keyword arg names for topic are necessary). 
        Raises ListenerInadequate if listener not usable for topic. 
        
        Otherwise, returns whether listener wants topic name (signified 
        by a kwarg key,value = KWARG_TOPIC,AUTO_ARG in listener protocol)
        when sent messages. E.g. def fn1(msgTopic=Listener.AUTO_ARG) would 
        cause validate(fn1) to return True, whereas any other kwarg name or value 
        would cause a False to be returned. 
        '''
        # figure out what is the actual function object to inspect:
        try:
            firstArg, func = getRawFunction(listener)
        except ValueError, exc:
            raise ListenerInadequate(str(exc), listener)

        (args, va, vkwa, defaultVals) = getargspec(func)
        if defaultVals is None:
            defaultVals = []
        else:
            defaultVals = list(defaultVals)
        return self.__validateArgs(listener, firstArg, args, va, vkwa, defaultVals)
        
    def isValid(self, listener):
        '''Return true only if listener can subscribe to messages where
        topic has kwargs keys topicKwargKeys. Just calls validate() in 
        a try-except clause.'''
        try:
            self.validate(listener)
            return True
        except ListenerInadequate:
            return False
    
    def __validateArgs(self, listener, firstArg, args, va, vkwa, defaultVals):
        # get the listener's signature (protocol), remove 'self' and
        # auto-pass topic kwarg and etc
        acceptsAllKwargs = (vkwa is not None)
        argsInfo = ArgsInfo(args, firstArg, defaultVals, acceptsAllKwargs)        
        
        # now validate:
        self._validateVarArg_(listener, va)
        self._validateVarKwarg_(listener, vkwa)
        self._validateArgs_(listener, argsInfo.allArgs, argsInfo.numRequired, va)
        self._validateKwargs_(listener, argsInfo.allArgs, argsInfo.numRequired, defaultVals, vkwa)
        
        return argsInfo
    
    def _validateVarArg_(self, listener, va):
        raise NotImplementedError
    def _validateVarKwarg_(self, listener, vkwa):
        raise NotImplementedError
    def _validateArgs_(self, listener, args, numReqdArgs, va):
        raise NotImplementedError
    def _validateKwargs_(self, listener, args, firstKwargIdx, defaultVals, vkwa):
        raise NotImplementedError        
        
    def acceptVarArg(self, listener, vaName):
        '''Accept listener even if a vararg is used.'''
        pass
    
    def rejectVarArg(self, listener, vaName):
        '''Reject if listener uses a vararg (*arg).'''
        if vaName is not None: 
            msg = 'can\'t have a *arg'
            raise ListenerInadequate(msg, listener, (vaName,))
    
    def rejectArgsReqdAny(self, listener, args, numReqdArgs, vaName):
        '''Reject if ANY required arguments are present (ie numReqdArgs>0),
        regardless of whether the vararg name vaName is None. '''
        if numReqdArgs > 0: # some args are required: only kwargs allowed
            msg = 'can\'t have required args (has %s too many)' % numReqdArgs
            raise ListenerInadequate(msg, listener, args[:numReqdArgs])

    def rejectArgsReqdNotSame(self, listener, args, numReqdArgs, vaName):
        listenerArgs = args[:numReqdArgs]
        self.__rejectArgsNotSame(listener, listenerArgs, self.topicArgs, 
            vaName, ordered=True)
        
    def rejectKwargsNotSame  (self, listener, args, firstKwargIdx, vkwa):
        listenerKwargs = args[firstKwargIdx:]
        self.__rejectArgsNotSame(listener, listenerKwargs, self.topicKwargs, vkwa)
    
    def rejectKwargsMissing  (self, listener, args, firstKwargIdx, vkwa):
        if vkwa is None:
            listenerKwargs = args[firstKwargIdx:]
            self.__rejectArgsMissing(listener, listenerKwargs, self.topicKwargs)
    
    def _rejectArgsExtra(  self, listener, listenerArgs, topicArgs):
        '''Verify that listener doesn't have more kwargs than Topic'''
        extraArgs = set(listenerArgs) - set(topicArgs)
        if extraArgs:
            if topicArgs:
                msg = 'args (%s) not allowed, should be (%s)' \
                    % (','.join(extraArgs), ','.join(topicArgs))
            else:
                msg = 'no args allowed, has (%s)' % ','.join(extraArgs)
            raise ListenerInadequate(msg, listener, extraArgs)


    def __rejectArgsNotSame(self, listener, listenerArgs, topicArgs, 
        vaName, ordered=False):
        '''If ordered=True, the listenerArgs will be compared to topicArgs 
        taking order into consideration, otherwise just the sets of values
        are compared.'''
        self._rejectArgsExtra(listener, listenerArgs, topicArgs)
        if vaName is None:
            self.__rejectArgsMissing(listener, listenerArgs, topicArgs)
        if ordered: 
            wrong = [a for a,b in zip(listenerArgs, topicArgs) if a!=b]
            if wrong:
                msg = 'has some args %s in wrong order' % wrong
                raise ListenerInadequate(msg, listener, wrong)
                
        
    def __rejectArgsMissing(self, listener, listenerArgs, topicArgs):
        '''Verify that listener has at least all the kwargs defined for topic'''
        missingArgs = set(topicArgs) - set(listenerArgs)
        if missingArgs:
            msg = 'needs to accept %s more args (%s)' \
                % (len(missingArgs), ''.join(missingArgs))
            raise ListenerInadequate(msg, listener, missingArgs)
    

class ValidatorSameKwargsOnly(Validator):
    '''
    Do not accept any required args or *args; accept any **kwarg, 
    and require that the Listener have at least all the kwargs (can 
    have extra) of Topic.
    '''
    
    def _validateVarArg_(self, listener, va):
        pass
    def _validateVarKwarg_(self, listener, vkwa):
        pass
    def _validateArgs_(self, listener, args, numReqdArgs, va):
        self.rejectArgsReqdNotSame(listener, args, numReqdArgs, va)
    def _validateKwargs_(self, listener, args, firstKwargIdx, defaultVals, vkwa):
        self.rejectKwargsNotSame(listener, args, firstKwargIdx, vkwa)
    

class ValidatorOneArgAnyKwargs(Validator):
    '''
    Accept one arg or *args; accept any **kwarg, 
    and require that the Listener have at least all the kwargs (can 
    have extra) of Topic.
    '''
    
    def _validateVarArg_(self, listener, va):
        '''accept *arg'''
        pass
    def _validateVarKwarg_(self, listener, vkwa):
        '''accept **kwarg'''
        pass
    
    def _validateArgs_(self, listener, args, numReqdArgs, va):
        '''accept if exactly one arg, regardless of name'''
        if numReqdArgs > 1:
            msg = 'cannot require more than one arg'
            effTopicArgs = ['msg']
            raise ListenerInadequate(msg, listener, effTopicArgs)

        if numReqdArgs == 1:
            # if no policy set, any name ok; otherwise validate name:
            needArgName = Policies._msgDataArgName
            if needArgName is None or args[0] == needArgName:
                return
            
            msg = 'listener arg name must be %s (is %s)' % (needArgName, args[0])
            effTopicArgs = [needArgName]
            raise ListenerInadequate(msg, listener, effTopicArgs)
        
        # numReqdArgs < 1:
        assert numReqdArgs == 0
        if va is not None:
            # then user specified *args, so ok:
            return
        
        if args:
            # then there are no required arg, but the first 
            # kwarg will be able to take the arg, so ok: 
            return
        
        # nothing goes, so raise:
        msg = 'Must take one arg (any name) or *arg'
        effTopicArgs = ['msg']
        raise ListenerInadequate(msg, listener, effTopicArgs)

    def _validateKwargs_(self, listener, args, firstKwargIdx, defaultVals, vkwa):
        '''accept any keyword args'''
        pass
    


_ListenerClasses = dict(
    kwargs  = ListenerKwargs, 
    dataArg = ListenerDataMsg)

_ListenerValidatorClasses = dict(
    kwargs  = ValidatorSameKwargsOnly, 
    dataArg = ValidatorOneArgAnyKwargs)
    
ListenerValidator = _ListenerValidatorClasses[Policies._msgDataProtocol]
Listener = _ListenerClasses[Policies._msgDataProtocol]


