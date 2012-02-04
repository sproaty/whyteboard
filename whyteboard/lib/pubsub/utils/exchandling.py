import sys, traceback


class TracebackInfo:
    '''
    Represent the traceback information for when an exception is 
    raised -- but not caught -- in a listener. The complete 
    traceback cannot be stored since this leads to circular 
    references (see docs for sys.exc_info()) which keeps 
    listeners alive even after the application is no longer 
    referring to them. 
    
    Instances of this object are given to listeners of the 
    'uncaughtExcInListener' topic as the excTraceback kwarg.
    The instance calls sys.exc_info() to get the traceback
    info but keeps only the following info: 
    
     * self.ExcClass: the class of exception that was raised and not caught
     * self.excArg: the argument given to exception when raised
     * self.traceback: list of quadruples as returned by traceback.extract_tb()
       
    Normally you just need to call one of the two getFormatted() methods. 
    '''
    def __init__(self):
        tmpInfo = sys.exc_info()
        self.ExcClass = tmpInfo[0]
        self.excArg   = tmpInfo[1]
        self.traceback = traceback.extract_tb(tmpInfo[2].tb_next.tb_next)
        del tmpInfo

    def getFormattedList(self):
        '''Get a list of strings as returned by the traceback module's
        format_list() and format_exception_only() functions.'''
        tmp = traceback.format_list(self.traceback)
        tmp.extend( traceback.format_exception_only(self.ExcClass, self.excArg) )
        return tmp
    
    def getFormattedString(self):
        '''Get a string similar to the stack trace that gets printed 
        to stdout by Python interpreter when an exception is not caught.'''
        return ''.join(self.getFormattedList())


class IExcHandler:
    '''Interface class for the exception handler. Such handler is called 
    whenever a listener raises an exception during a pub.sendMessage().
    You may give an instance of a class derived from IExcHandler to 
    pubsubconf.setListenerExcHandler().
    '''
    def __call__(self, listenerID):
        raise NotImplementedError('%s must override __call__()' % self.__class__)


class ExcPublisher(IExcHandler):
    topicUncaughtExc = 'uncaughtExcInListener'
    
    def __init__(self):
        self.__handling = None
        
    def init(self, topicMgr):
        '''Your code must call this after the first import of pubsub. It is
        possible that some modules imported by your application import pubsub.
        So it is recommended that you import pubsub in your main script, and 
        right after, call this method.'''
        self.__topicObj = topicMgr.newTopic(
            _name = self.topicUncaughtExc,
            _desc = 'generated when a listener raises an exception',
            listenerStr  = 'string representation of listener',
            excTraceback = 'instance of TracebackInfo containing exception info')
            
    def __call__(self, listenerID):
        '''An exception has been raised. Now we send the excInfo to 
        all subscribers of topic self.topicUncaughtExc. Note that if one of
        those listeners raises an exception, this __call__ will be called 
        again by pubsub. So we guard against infinite recursion. In such 
        case, we raise ExcHandlerError, which will interrupt the original 
        sendMessage.
        '''
        tbInfo = TracebackInfo()
        if self.__handling:
            raise ExcHandlerError(listenerID, tbInfo, *self.__handling)
        
        try:
            self.__handling = (listenerID, tbInfo)
            self.__topicObj.publish( 
                dict(listenerStr=listenerID, excTraceback=tbInfo) )
        finally:
            self.__handling = None


class ExcHandlerError(RuntimeError):
    '''
    Whenever an exception gets raised within some listener during a 
    sendMessage(), a message of topic ExcPublisher.topicUncaughtExc is 
    sent, and then sending to remaining listeners resumes. However, 
    if a listener of topic ExcPublisher.topicUncaughtExc *also* raises an 
    exception, the original sendMessage() operation must be aborted: 
    an ExcHandlerError exception gets raised. 
    
    Information about the exception raised in the "uncaught exception"
    listener is stored as members of class:
    
      - self.badExcListenerID = which "uncaught exception" *listener*
                                raised an exception
      - self.tbInfo           = instance of TracebackInfo for that exception 
      - self.origListenerID   = which "regular" listener raised the original 
                                "uncaught exception"
      - self.origListenerTbInfo = instance of TracebackInfo, for original 
                                  "uncaught exception"
    '''
    
    def __init__(self, badExcListenerID, tbInfo, 
        origListenerID, origListenerTbInfo):
        self.badExcListenerID = badExcListenerID
        self.tbInfo = tbInfo
        self.origListenerID = origListenerID
        self.origListenerTbInfo = origListenerTbInfo
        RuntimeError.__init__(self, str(self))
        
    def __str__(self):
        fmtStr = self.tbInfo.getFormattedString()
        return 'Exception listener %s raised exception:\n%s' \
            % (self.badExcListenerID, fmtStr)


