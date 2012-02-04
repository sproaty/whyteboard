'''
Definitions related to topic message argument specification.
'''

from pubsubconf import Policies
from topicutils import stringize
from listener import getArgs as getListenerArgs


def topicArgsFromCallable(_callable):
    '''Get the topic arguments and list of those that are required, 
    by introspecting given listener. Returns a pair, (args, required)
    where args is a dictionary of allowed arguments, and required
    states which args are required rather than optional.'''
    argsInfo = getListenerArgs(_callable)
    required = argsInfo.getRequiredArgs()
    defaultDoc = 'NEEDS TO BE DOCUMENTED!!!'
    args = dict.fromkeys(argsInfo.allArgs, defaultDoc)
    return args, required


class InvalidArgsSpec(RuntimeError):
    def __init__(self, msg, args):
        argsMsg = msg % ','.join(args)
        RuntimeError.__init__(self, 'Invalid arguments: ' + argsMsg)
    

class MissingReqdArgs(RuntimeError):
    def __init__(self, argNames, missing):
        argsStr = ','.join(argNames)
        missStr = ','.join(missing)
        msg = "Some required args missing in call to sendMessage(%s): %s" % (argsStr, missStr)
        RuntimeError.__init__(self, msg)
        

class UnknownOptArgs(RuntimeError):
    def __init__(self, argNames, extra):
        argsStr = ','.join(argNames)
        extraStr = ','.join(extra)
        msg = "Some optional args unknown in call to sendMessage(%s): %s" % (argsStr, extraStr)
        RuntimeError.__init__(self, msg)
        

def verifyArgsDifferent(allArgs, allParentArgs, topicName):
    extra = set(allArgs).intersection(allParentArgs)
    if extra:
        msg = 'Args %%s already used in parent of "%s"' % topicName
        raise InvalidArgsSpec( msg, tuple(extra) )
    
    
def verifySubset(all, sub, topicName, extraMsg=''):
    '''Verify that sub is a subset of all for topicName'''
    notInAll = set(sub).difference(all)
    if notInAll:
        msg = 'Args (%%s) missing from %s"%s"' % (extraMsg, topicName)
        raise InvalidArgsSpec(msg, tuple(notInAll) )
    
    
class ArgsInfoBase:
    SPEC_NONE     = 0 # specification not given
    SPEC_SUBONLY  = 1 # only subtopic args specified
    SPEC_ALL      = 2 # all args specified

    SPEC_MISSING  = 3 # no specification
    SPEC_USERDEFD = 4 # only user-specified sub args
    SPEC_COMPLETE = 5 # all args, but not confirmed via user spec
    SPEC_COMPLETE_FINAL = 6 # all args, confirmed by user


class ArgsInfoKwargs( ArgsInfoBase ):
    
    def __init__(self, getArgsSpec, topicNameTuple, parent, argsDocs, reqdArgs, argsSpec):
        argsDocs = argsDocs or {}
        reqdArgs = tuple(reqdArgs or ())
            
        # check that all args marked as required are in argsDocs
        missingArgs = set(reqdArgs).difference(argsDocs.keys())
        if missingArgs:
            msg = 'The argsDocs dict doesn\'t contain keys (%s) given in reqdArgs'
            raise InvalidArgsSpec(msg, missingArgs)
        
        self.allOptional = None # list of topic message optional argument names
        self.allRequired = None # list of topic message required argument names
        self.subArgsDocs = None # documentation for each subtopic arg (dict)
        self.subArgsReqd = None # which keys in subArgsDocs repr. required args (tuple)
        
        self.argsSpec = self.SPEC_NONE
        topicName = stringize(topicNameTuple)
        if argsSpec == self.SPEC_NONE:
            # other self.all* members will be updated when our sub args get set 
            assert not argsDocs
            assert not reqdArgs
            assert self.argsSpec == self.SPEC_NONE
            
            subArgsDocs, subArgsReqd = getArgsSpec(topicNameTuple)
            if subArgsDocs is not None:
                self.__setSubArgs(subArgsDocs, subArgsReqd, parent, topicName)
            
        elif argsSpec == self.SPEC_SUBONLY:
            self.__setSubArgs(argsDocs.copy(), reqdArgs, parent, topicName)

        else: 
            assert argsSpec == self.SPEC_ALL
            self.__setAllArgs(getArgsSpec, topicNameTuple, 
                parent, argsDocs.copy(), reqdArgs)
            
    def isComplete(self):
        return self.allOptional is not None
    
    def getArgs(self):
        return set(self.allOptional + self.allRequired)
    
    def numArgs(self):
        return len(self.allOptional or ()) + len(self.allRequired or ())
    
    def subKnown(self):
        return self.subArgsDocs is not None
    
    def check(self, msgKwargs):
        '''Check that the message arguments given satisfy the 
        topic arg specification. Raises MissingReqdArgs if some required
        args are missing or not known, and raises UnknownOptArgs if some 
        optional args are unknown. '''
        all = set(msgKwargs)
        # check that it has all required args
        needReqd = set(self.allRequired)
        hasReqd = (needReqd <= all)
        if not hasReqd:
            raise MissingReqdArgs(msgKwargs.keys(), needReqd - all)
        
        # check that all other args are among the optional spec
        optional = all - needReqd
        ok = (optional <= set(self.allOptional))
        if not ok:
            raise UnknownOptArgs( msgKwargs.keys(), optional - set(self.allOptional) )

    def filterArgs(self, msgKwargs):
        '''Returns a dict which contains only those items of msgKwargs 
        which are defined for topic. E.g. if msgKwargs is {a:1, b:'b'}
        and topic arg spec is ('a',) then return {a:1}. The returned dict
        is valid only if checkArgs(msgKwargs) was called, though that call
        can be on self OR child topic (assuming that child topics have
        superset of self arg spec).'''
        assert self.isComplete()
        if len(msgKwargs) == self.numArgs():
            return msgKwargs
        
        # only keep the keys from msgKwargs that are also in topic's kwargs
        # method 1: SLOWEST
        #newKwargs = dict( (k,msgKwargs[k]) for k in self.__msgArgs.allOptional if k in msgKwargs )
        #newKwargs.update( (k,msgKwargs[k]) for k in self.__msgArgs.allRequired )
        
        # method 2: FAST: 
        #argNames = self.__msgArgs.getArgs()
        #newKwargs = dict( (key, val) for (key, val) in msgKwargs.iteritems() if key in argNames )
        
        # method 3: FASTEST: 
        argNames = self.getArgs().intersection(msgKwargs)
        newKwargs = dict( (k,msgKwargs[k]) for k in argNames )
    
        return newKwargs

    def __setAllArgs(self, getArgsSpec, topicNameTuple, parent, argsDocs, reqdArgs):
        self.argsSpec = self.SPEC_NONE
        
        subArgsDocs, subArgsReqd = getArgsSpec(topicNameTuple)
        topicName = stringize(topicNameTuple)
        if subArgsDocs is None:
            # no user spec available, create spec from args given:
            allOptional = set( argsDocs.keys() ).difference( reqdArgs )
            self.allOptional = tuple(allOptional)
            self.allRequired = reqdArgs
            self.argsSpec = self.SPEC_COMPLETE
            
            if parent is None:
                self.subArgsDocs = argsDocs.copy()
                self.subArgsReqd = reqdArgs
                self.argsSpec = self.SPEC_COMPLETE_FINAL
                
            elif parent.argsSpecComplete():
                # verify that parent args is a subset of spec given:
                parentReqd, parentOpt, dummySpec = parent.getArgs()
                verifySubset(argsDocs.keys(), parentReqd+parentOpt, topicName)
                verifySubset(reqdArgs, parentReqd, topicName, 
                             'list of required args for ')
                # ok, good to go:
                subArgsOpt  = allOptional.difference(parentOpt)
                subArgsReqd = set(reqdArgs).difference(parentReqd)
                self.subArgsReqd = tuple(subArgsReqd)
                subArgs = tuple(subArgsOpt)+self.subArgsReqd
                self.subArgsDocs = dict( (k,argsDocs[k]) for k in subArgs )
            
        else: # user spec available, takes precedence
            if parent is None:
                if set(argsDocs) != set(subArgsDocs):
                    raise ValueError("bad listener due to args")
                if set(reqdArgs) != set(subArgsReqd):
                    raise ValueError("bad listener due to reqd args")
                
            elif parent.argsSpecComplete():
                # then arg spec given must be equal to parent spec + user def
                parentReqd, parentOpt, dummySpec = parent.getArgs()
                if set(argsDocs) != set(subArgsDocs).union(parentReqd+parentOpt):
                    raise ValueError("bad listener due to args")
                allReqd = set(subArgsReqd).union(parentReqd)
                if set(reqdArgs) != allReqd:
                    print 'all, sub', allReqd, reqdArgs
                    raise ValueError("bad listener due to reqd args")
                
            self.__setSubArgs(subArgsDocs, subArgsReqd, parent, topicName)
            if self.argsSpec == self.SPEC_SUBONLY:
                # then parent spec incomplete 
                assert (parent is not None) and not parent.argsSpecComplete()
                allOptional = set( argsDocs.keys() ).difference( reqdArgs )
                verifySubset(allOptional, subArgsDocs.keys(), topicName)
                verifySubset(reqdArgs, subArgsReqd, topicName, 
                             'list of required args for ')
                self.allOptional = tuple(allOptional)
                self.allRequired = reqdArgs
                self.argsSpec = self.SPEC_COMPLETE

    def __setSubArgs(self, subDocs, subReqd, parent, topicName):
        '''Set the topic sub args, i.e. the args that topic adds to 
        the args specified by parent. '''
        self.subArgsDocs, self.subArgsReqd = subDocs, subReqd
        self.argsSpec = self.SPEC_SUBONLY
        
        # see if all args can be infered:
        if parent is None:
            subOptional = set( subDocs.keys() ).difference( subReqd )
            self.allOptional = tuple(subOptional)
            self.allRequired = subReqd
            self.argsSpec = self.SPEC_COMPLETE_FINAL
            
        elif parent.argsSpecComplete():
            # check that none of the subArgs are already used by parent: 
            parentReqd, parentOpt, dummySpec = parent.getArgs()
            subOptional = set( subDocs.keys() ).difference( subReqd )
            verifyArgsDifferent(subOptional, parentOpt, topicName)
            assert not set(subReqd).intersection(parentReqd)
            # ok:
            self.allOptional = parentOpt  + tuple(subOptional)
            self.allRequired = parentReqd + subReqd
            self.argsSpec = self.SPEC_COMPLETE_FINAL
            


class ArgsInfoDataMsg( ArgsInfoBase ):
    def __init__(self, topicDefnProvider, topicNameTuple, parent, argsDocs, reqdArgs, argsSpec):
        if not argsDocs:
            self.argsSpec = self.SPEC_COMPLETE
            argsDocs = {'data':'message data'}
        else:
            self.argsSpec = self.SPEC_COMPLETE_FINAL
        
        self.allOptional = ()        # list of topic message optional argument names
        self.allRequired = ('data',) # list of topic message required argument names
        self.subArgsDocs = argsDocs  # documentation for each subtopic arg (dict)
        self.subArgsReqd = ('data',) # which keys in subArgsDocs repr. required args (tuple)
        
    def isComplete(self):
        return True
        
    def getArgs(self):
        return set(self.allOptional + self.allRequired)
    
    def numArgs(self):
        return len(self.allOptional or ()) + len(self.allRequired or ())
    
    def subKnown(self):
        return self.subArgsDocs is not None
        
        
_argsInfoClasses = dict(
    kwargs  = ArgsInfoKwargs, 
    dataArg = ArgsInfoDataMsg)
ArgsInfo = _argsInfoClasses[ Policies._msgDataProtocol ]

