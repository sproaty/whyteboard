'''
Provides the Publisher class, which manages subscribing callables to 
topics and sending messages. 
'''

from pubsubconf import Policies


class PublisherBase:
    '''
    Represent the class that send messages to listeners of given 
    topics and that knows how to subscribe/unsubscribe listeners
    from topics. 
    '''
    def __init__(self, topicMgr):
        self.__notifyOnSend = False
        self.__notifyOnSubscribe = False
        self.__notifyOnUnsubscribe = False
        
        self.__topicMgr = topicMgr
        assert self.__topicMgr is not None
        
    def __call__(self):
        '''For backwards compatilibity with pubsub v1 (wxPython).'''
        return self
    
    def sendMessage(self, topicName, *args, **kwargs):
        raise NotImplementedError
    
    def setNotification(self, sendMessage=None, subscribe=None, unsubscribe=None):
        '''Note that notifications that are None are left at their 
        current value.'''
        # create special topics if not already done
        if (sendMessage or subscribe or unsubscribe): # otherwise topics not needed
            if Policies._notificationHandler is None:
                raise RuntimeError('Must call pubsubconf.setNotificationHandler() first' )
            
        if sendMessage is not None:
            self.__notifyOnSend = sendMessage
        if subscribe is not None:
            self.__notifyOnSubscribe = subscribe
        if unsubscribe is not None:
            self.__notifyOnUnsubscribe = unsubscribe

    def subscribe(self, listener, topicName):
        '''Subscribe listener to named topic. Raises ListenerInadequate 
        if listener isn't compatible with the topic's args. Returns 
        (Listener, didit), where didit is False if listener was already 
        subscribed, and Listener is instance of pub.Listener wrapping 
        listener.
        
        Note that, if 'subscribe' notification was turned on via 
        setNotification(), the handler's notifySubscribe is called.'''
        topicObj = self.__topicMgr.getTopicOrNone(topicName)
        if topicObj is None:
            noDesc = 'TBD (defined from listener)'
            topicObj = self.__topicMgr._newTopicFromTemplate_(
                            topicName, desc=noDesc, usingCallable=listener)
        elif not topicObj.isSendable():
            topicObj._updateArgsSpec_(listener, self.__topicMgr)
            
        assert topicObj is not None
        assert topicObj.isSendable()
            
        # subscribe listener
        subdLisnr, didit = topicObj._subscribe_(listener)
        
        # notify of subscription
        if self.__notifyOnSubscribe:
            Policies._notificationHandler.notifySubscribe(subdLisnr, topicObj, didit)

        return subdLisnr, didit
        
    def unsubscribe(self, listener, topicName):
        '''Unsubscribe from given topic. If 'unsubscribe' notification 
        is on, notification handler will be called. Returns the pub.Listener 
        instance that has unsubscribed listener.'''
        topicObj = self.__topicMgr.getTopic(topicName)
        unsubdLisnr = topicObj._unsubscribe_(listener)
        if self.__notifyOnUnsubscribe:
            assert listener == unsubdLisnr.getCallable()
            Policies._notificationHandler.notifyUnsubscribe(unsubdLisnr, topicObj)
                
        return unsubdLisnr
    
    def unsubAll(self, topicName = None, 
        listenerFilter = None, topicFilter = None):
        '''Unsubscribe all listeners from specified topicName. If no
        topic name given, will unsubscribe all listeners that satisfy
        listenerFilter(listener) == True, from all topics that satisfy 
        topicFilter(topicName) == True. If no listener or topic
        filter is given, 'accept all' is assumed.  
        Note: call will generate one notification (see 
        pubsub.setNotification()) message for each unsubscription.'''
        unsubdListeners = []
        
        if topicName is None: 
            # unsubscribe all listeners from all non-pubsub topics
            topicsMap = self.__topicMgr._topicsMap
            for topicName, topicObj in topicsMap.iteritems():
                if topicFilter is None or topicFilter(topicName):
                    tmp = topicObj._unsubscribeAllListeners_(listenerFilter)
                    unsubdListeners.extend(tmp)
        
        else:
            topicObj = self.__topicMgr.getTopic(topicName)
            unsubdListeners = topicObj._unsubscribeAllListeners_(listenerFilter)
            
        # send notification regarding all listeners actually unsubscribed
        if self.__notifyOnUnsubscribe:
            for unsubdLisnr in unsubdListeners:
                Policies._notificationHandler.notifyUnsubscribe(unsubdLisnr, topicObj)
                
        return unsubdListeners


class PublisherKwargs(PublisherBase):
    '''
    Publisher used for kwargs protocol, ie when sending message data 
    via kwargs. 
    '''
    
    def sendMessage(self, _topicName, **kwargs):
        '''Send message of type _topicName to all subscribed listeners, 
        with message data in kwargs. If topicName is a subtopic, listeners 
        of topics more general will also get the message. Note also that 
        kwargs must be compatible with topic.
        
        Note that any listener that lets a raised exception escape will 
        interrupt the send operation, unless an exception handler was
        specified via pubsubconf.setListenerExcHandler().  
        '''
        topicMgr = self._PublisherBase__topicMgr
        topicObj = topicMgr.getTopicOrNone(_topicName)
        if topicObj is None:
            args = ','.join( kwargs.keys() )
            desc = 'Topic created from sendMessage(%s)' % args
            topicObj = topicMgr._newTopicNoSpec_(_topicName, desc)
            
        # don't care if topic not final: topicObj.getListeners() 
        # will return nothing if not final but notification will still work
        
        # check that _topic isn't 'pubsub.sendMessage'
        if self._PublisherBase__notifyOnSend:
            Policies._notificationHandler.notifySend('pre', topicObj)
            topicObj.publish(kwargs)
            Policies._notificationHandler.notifySend('post', topicObj)
                    
        else:
            topicObj.publish(kwargs)


class PublisherKwargsAsDataMsg(PublisherKwargs):
    '''
    This is used when transitioning from DataMsg to Kwargs 
    messaging protocol.
    '''
    
    def __init__(self, topicMgr):
        PublisherKwargs.__init__(self, topicMgr)
        
        from datamsg import Message
        self.Msg = Message
        #from topicutils import tupleize
        def tupleize(name): return name
        self.tupleize = tupleize

    def sendMessage(self, _topicName, **kwargs):
        commonArgName = Policies._msgDataArgName
        data = kwargs.get(commonArgName, None)
        kwargs[commonArgName] = self.Msg( self.tupleize(_topicName), data)
        PublisherKwargs.sendMessage( self, _topicName, **kwargs )


class PublisherDataMsg(PublisherBase):
    '''
    Publisher that allows old-style Message.data messages to be sent
    to listeners. Listeners take one arg (required, unless there is an
    *arg), but can have kwargs (since they have default values). 
    '''
    
    def __getTopicObj(self, topicName, data):
        topicMgr = self._PublisherBase__topicMgr
        topicObj = topicMgr.getTopicOrNone(topicName)
        if topicObj is None:
            argVal = ''
            if data is not None: 
                argVal = 'data=%s' % (data,)
            desc = 'Topic created from sendMessage(%s)' % argVal
            topicObj = topicMgr._newTopicNoSpec_(topicName, desc)
            
        return topicObj
        
    def sendMessage(self, topicName, data=None):
        '''Send message of type topicName to all subscribed listeners, 
        with message data. If topicName is a subtopic, listeners 
        of topics more general will also get the message. 
        
        Note that any listener that lets a raised exception escape will 
        interrupt the send operation, unless an exception handler was
        specified via pubsubconf.setListenerExcHandler().  
        '''
        topicObj = self.__getTopicObj(topicName, data)
        
        # don't care if topic not final: topicObj.getListeners() 
        # will return nothing if not final but notification will still work
        
        if self._PublisherBase__notifyOnSend:
            Policies._notificationHandler.notifySend('pre', topicObj)
            topicObj.publish(data)
            Policies._notificationHandler.notifySend('post', topicObj)
                    
        else:
            topicObj.publish(data)
        

# select which publisher to use at first load:

_PublisherClasses = dict(
    kwargs  = (PublisherKwargsAsDataMsg, PublisherKwargs),
    dataArg = (PublisherDataMsg, PublisherDataMsg) )

Publisher = _PublisherClasses[Policies._msgDataProtocol][Policies._msgDataArgName is None]
