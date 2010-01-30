"""
Provides useful functions and classes. Most useful are probably 
printTreeDocs and printTreeSpec. 
"""


__all__ = ('StructMsg', 'Callback',
           'TopicTreeTraverser', 'TopicTreePrinter', 'TopicTreeAsSpec',
           'printTreeDocs', 'printTreeSpec')


class StructMsg:
    '''
    This *can* be used to package message data. Each of the keyword 
    args given at construction will be stored as a member of the 'data' 
    member of instance. E.g. "m=Message2(a=1, b='b')" would succeed 
    "assert m.data.a==1" and "assert m.data.b=='b'". However, use of 
    Message2 makes your messaging code less documented and harder to 
    debug. 
    '''
    
    def __init__(self, **kwargs):
        class Data: pass
        self.data = Data()
        self.data.__dict__.update(kwargs)


class Callback:
    '''This can be used to wrap functions that are referenced by class 
    data if the data should be called as a function. E.g. given 
    >>> def func(): pass 
    >>> class A: 
    ....def __init__(self): self.a = func
    then doing 
    >>> boo=A(); boo.a()
    will fail since Python will try to call a() as a method of boo, 
    whereas a() is a free function. But if you have instead 
    "self.a = Callback(func)", then "boo.a()" works as expected.  
    '''
    def __init__(self, callable_):
        self.__callable = callable_
    def __call__(self, *args, **kwargs):
        return self.__callable(*args, **kwargs)
    

from textwrap import TextWrapper, dedent


class TopicTreeTraverser:
    '''
    Topic tree traverser. Provides the traverse() method 
    which traverses a topic tree and calls self._onTopic() for 
    each topic in the tree that satisfies self._accept(). 
    Additionally it calls self._startChildren() whenever it
    starts traversing the subtopics of a topic, and 
    self._endChildren() when it is done with the subtopics. 
    Finally, it calls self._doneTraversal() when traversal 
    has been completed. 
    
    Derive from TopicTreeTraverser and override one or more of the 
    four self._*() methods described above. Call traverse()
    on instances to "execute" the traversal.
    '''
    
    DEPTH   = 'Depth first through topic tree'
    BREADTH = 'Breadth first through topic tree'
    MAP     = 'Sequential through topic manager\'s topics map'
    
    def _accept(self, topicObj):
        '''Override this to filter nodes of topic tree. Must return 
        True (accept node) of False (reject node). Note that rejected
        nodes cause traversal to move to next branch (no children 
        traversed).'''
        return True
    
    def _startTraversal(self):
        '''Override this to define what to do when traversal() starts.'''
        pass

    def _onTopic(self, topicObj):
        '''Override this to define what to do for each node.'''
        pass
    
    def _startChildren(self):
        '''Override this to take special action whenever a 
        new level of the topic hierarchy is started (e.g., indent
        some output). '''
        pass
        
    def _endChildren(self):
        '''Override this to take special action whenever a 
        level of the topic hierarchy is completed (e.g., dedent
        some output). '''
        pass
        
    def _doneTraversal(self):
        '''Override this to take special action when traversal done.'''
        pass
    
    def traverse(self, topicObj, how=DEPTH, onlyFiltered=True):
        '''Start traversing tree at topicObj. Note that topicObj is a 
        Topic object, not a topic name. The how defines if tree should
        be traversed breadth or depth first. If onlyFiltered is
        False, then all nodes are accepted (_accept(node) not called). 
        '''
        if how == self.MAP:
            raise NotImplementedError('not yet available')
        
        self._startTraversal()
        
        if how == self.BREADTH:
            self.__traverseBreadth(topicObj, onlyFiltered)
        else: #if how == self.DEPTH:
            self.__traverseDepth(topicObj, onlyFiltered)
            
        self._doneTraversal()
            
    def __traverseBreadth(self, topicObj, onlyFiltered):
        def extendQueue(subtopics):
            topics.append(self._startChildren)
            topics.extend(subtopics)
            topics.append(self._endChildren)
            
        topics = [topicObj]
        while topics:
            topicObj = topics.pop(0)
            
            if topicObj in (self._startChildren, self._endChildren):
                topicObj()
                continue
            
            if onlyFiltered:
                if self._accept(topicObj):
                    extendQueue( topicObj.getSubtopics() )
                    self._onTopic(topicObj)
            else:
                extendQueue( topicObj.getSubtopics() )
                if self._accept(topicObj):
                    self._onTopic(topicObj)
                    
    def __traverseDepth(self, topicObj, onlyFiltered):
        def extendStack(topicTreeStack, subtopics):
            topicTreeStack.insert(0, self._endChildren) # marker functor
            # put subtopics in list in alphabetical order
            subtopicsTmp = subtopics
            subtopicsTmp.sort(reverse=True, key=topicObj.__class__.getName)
            for sub in subtopicsTmp:
                topicTreeStack.insert(0, sub) # this puts them in reverse order
            topicTreeStack.insert(0, self._startChildren) # marker functor
            
        topics = [topicObj]
        while topics:
            topicObj = topics.pop(0)

            if topicObj in (self._startChildren, self._endChildren):
                topicObj()
                continue
            
            if onlyFiltered:
                if self._accept(topicObj):
                    extendStack( topics, topicObj.getSubtopics() )
                    self._onTopic(topicObj)
            else:
                extendStack( topics, topicObj.getSubtopics() )
                if self._accept(topicObj):
                    self._onTopic(topicObj)
                    

class TopicTreePrinter(TopicTreeTraverser):
    '''
    Example topic tree TopicTreeTraverser that prints a prettified 
    representation
    of topic tree by doing a depth-first traversal of topic tree and 
    print information at each (topic) node of tree. Extra info to be 
    printed is specified via the 'extra' kwarg. Its value must be a 
    list of characters, the order determines output order: 
    - D: print description of topic
    - A: print topic kwargs and their description
    - a: print kwarg names only
    - L: print listeners currently subscribed to topic
    
    E.g. TopicTreePrinter(extra='LaDA') would print, for each topic, 
    the list of subscribed listeners, the topic's list of kwargs, the
    topic description, and the description for each kwarg, 
    
        >>> Topic "delTopic"
           >> Listeners:
              > listener1_2880 (from yourModule)
              > listener2_3450 (from yourModule)
           >> Names of Message arguments:
              > arg1
              > arg2
           >> Description: whenever a topic is deleted
           >> Descriptions of Message arguments:
              > arg1: (required) its description
              > arg2: some other description
    
    '''
    
    allowedExtras = frozenset('DAaL') # must NOT change
    
    def __init__(self, extra=None, width=70, indentStep=4, 
        bulletTopic='\\--', bulletTopicItem='|==', bulletTopicArg='-', fileObj=None):
        '''Topic tree printer will print listeners for each topic only 
        if printListeners is True. The width will be used to limit 
        the width of text output, while indentStep is the number of 
        spaces added each time the text is indented further. The 
        three bullet parameters define the strings used for each 
        item (topic, topic items, and kwargs). '''
        self.__contentMeth = dict(
            D = self.__printTopicDescription, 
            A = self.__printTopicArgsAll,
            a = self.__printTopicArgNames,
            L = self.__printTopicListeners)
        assert self.allowedExtras == set(self.__contentMeth.keys())
        import sys
        self.__destination = fileObj or sys.stdout
        self.__output = []

        self.__content = extra or ''
        unknownSel = set(self.__content) - self.allowedExtras 
        if unknownSel:
            msg = 'These extra chars not known: %s' % ','.join(unknownSel)
            raise ValueError(msg)
        
        self.__width   = width
        self.__wrapper = TextWrapper(width)
        self.__indent  = 0
        self.__indentStep = indentStep
        self.__topicsBullet     = bulletTopic
        self.__topicItemsBullet = bulletTopicItem
        self.__topicArgsBullet  = bulletTopicArg
        
    def getOutput(self):
        return '\n'.join( self.__output )
    
    def _doneTraversal(self):
        if self.__destination is not None: 
            self.__destination.write(self.getOutput())
            
    def _onTopic(self, topicObj):
        '''This gets called for each topic. Print as per specified content.'''
        
        # topic name
        self.__wrapper.width = self.__width
        indent = self.__indent
        head = '%s Topic "%s"' % (self.__topicsBullet, topicObj.getTailName())
        self.__output.append( self.__formatDefn(indent, head) )
        indent += self.__indentStep

        # each extra content (assume constructor verified that chars are valid)
        for item in self.__content:
            function = self.__contentMeth[item]
            function(indent, topicObj)
            
    def _startChildren(self):
        '''Increase the indent'''
        self.__indent += self.__indentStep
        
    def _endChildren(self):
        '''Decrease the indent'''
        self.__indent -= self.__indentStep

    def __formatDefn(self, indent, item, defn='', sep=': '):
        '''Print a definition: a block of text at a certain indent, 
        has item name, and an optional definition separated from 
        item by sep. '''
        if defn: 
            prefix = '%s%s%s' % (' '*indent, item, sep)
            self.__wrapper.initial_indent = prefix
            self.__wrapper.subsequent_indent = ' '*(indent+self.__indentStep)
            return self.__wrapper.fill(defn)
        else:
            return '%s%s' % (' '*indent, item)
    
    def __printTopicDescription(self, indent, topicObj):
        # topic description
        defn = '%s Description' % self.__topicItemsBullet
        self.__output.append( 
            self.__formatDefn(indent, defn, topicObj.getDescription()) )
        
    def __printTopicArgsAll(self, indent, topicObj, desc=True):
        # topic kwargs
        args = topicObj.getArgDescriptions()
        if args:
            #required, optional, complete = topicObj.getArgs()
            headName = 'Names of Message arguments:'
            if desc:
                headName = 'Descriptions of message arguments:'
            head = '%s %s' % (self.__topicItemsBullet, headName)
            self.__output.append( self.__formatDefn(indent, head) )
            tmpIndent = indent + self.__indentStep
            required = topicObj.getArgs()[0]
            for key, arg in args.iteritems():
                if not desc:
                    arg = ''
                elif key in required:
                    arg = '(required) %s' % arg
                msg = '%s %s' % (self.__topicArgsBullet,key)
                self.__output.append( self.__formatDefn(tmpIndent, msg, arg) )

    def __printTopicArgNames(self, indent, topicObj):
        self.__printTopicArgsAll(indent, topicObj, False)
        
    def __printTopicListeners(self, indent, topicObj):
        if topicObj.hasListeners():
            listeners = topicObj.getListeners()
            item = '%s Listeners:' % self.__topicItemsBullet
            self.__output.append( self.__formatDefn(indent, item) )
            tmpIndent = indent + self.__indentStep
            for listener in listeners:
                item = '%s %s (from %s)' % (self.__topicArgsBullet, listener.name(), listener.module())
                self.__output.append( self.__formatDefn(tmpIndent, item) )
    
    
class TopicTreeAsSpec(TopicTreeTraverser):
    '''
    Prints the class representation of topic tree, as Python code
    that can be imported. The printout goes to stdout, unless an
    open file object is given to constructor via the fileObj parameter.
    '''
        
    def __init__(self, width=70, indentStep=4, header=None, footer=None, fileObj=None):
        '''Can specify the width of output, the indent step, the header 
        and footer to print, and the destination fileObj. If no destination 
        file, then stdout is assumed.  Typically, the only argument is 
        the destination file in which to put the output.''' 
        import sys
        self.__destination = fileObj or sys.stdout
        self.__output = []
        self.__header = header
        self.__footer = footer
        
        self.__width   = width
        self.__wrapper = TextWrapper(width)
        self.__indent  = 0
        self.__indentStep = indentStep
        
        from pubsub import pub
        self.__ROOT_TOPIC = pub.ALL_TOPICS
        
        self.__comment = '''\
automatically generated by pubsub.utils.printTreeSpec(**kwargs)
with kwargs = %(printKwargs)s
'''  % dict(printKwargs = 
              dict(width=width, indentStep=indentStep, header=header, 
                   footer=footer, fileObj=fileObj) )

        
    def getOutput(self):
        return '\n'.join( self.__output )
    
    def _startTraversal(self):
        # output comment
        self.__wrapper.initial_indent = '# '
        self.__wrapper.subsequent_indent = self.__wrapper.initial_indent
        self.__output.append( self.__wrapper.fill(self.__comment) )
        self.__output.append('')
        self.__output.append('')

        # output header:
        if self.__header:
            self.__output.append(self.__header)
        
    def _doneTraversal(self):
        if self.__footer:
            self.__output.append('')
            self.__output.append('')
            self.__output.append(self.__footer)
        
        if self.__destination is not None: 
            self.__destination.write(self.getOutput())
            
    def _onTopic(self, topicObj):
        '''This gets called for each topic. Print as per specified content.'''
        if topicObj.getName() == self.__ROOT_TOPIC:
            return
        
        self.__output.append( '' )
        # topic name
        self.__wrapper.width = self.__width
        head = 'class %s:' % topicObj.getTailName()
        self.__formatItem(head)

        # each extra content (assume constructor verified that chars are valid)
        self.__printTopicDescription(topicObj)
        self.__printTopicArgsAll(topicObj)
            
    def _startChildren(self):
        '''Increase the indent'''
        self.__indent += self.__indentStep
        
    def _endChildren(self):
        '''Decrease the indent'''
        self.__indent -= self.__indentStep

    def __printTopicDescription(self, topicObj):
        indent = self.__indentStep
        self.__formatItem("'''", indent)
        self.__formatBlock( topicObj.getDescription(), indent )
        self.__formatItem("'''", indent)
        
    def __printTopicArgsAll(self, topicObj):
        indent = self.__indentStep
        argsDocs = topicObj.getArgDescriptions()
        for key, argDesc in argsDocs.iteritems():
            msg = "%s = '%s'" % (key, argDesc)
            self.__formatItem(msg, indent)

        required = topicObj.getArgs()[0]
        if required:
            self.__formatItem('_required = %s' % `required`, indent)

    def __formatItem(self, item, extraIndent=0):
        indent = extraIndent + self.__indent
        self.__output.append( '%s%s' % (' '*indent, item) )

    def __formatBlock(self, text, extraIndent=0):
        self.__wrapper.initial_indent = ' '*(self.__indent + extraIndent)
        self.__wrapper.subsequent_indent = self.__wrapper.initial_indent
        self.__output.append( self.__wrapper.fill(text) )
    

def printTreeDocs(rootTopic=None, **kwargs):
    '''Uses the TopicTreePrinter to print out the topic tree 
    to stdout, starting at rootTopic The kwargs are the same as 
    for TopicTreePrinter constructor. '''
    printer = TopicTreePrinter(**kwargs)
    if rootTopic is None:
        from pubsub import pub
        rootTopic = pub.getDefaultRootTopic()
    assert rootTopic is not None
    printer.traverse(rootTopic)


defaultTopicTreeSpecHeader = \
"""\
from pubsub.utils import TopicTreeDefnSimple


class MyTopicTree(TopicDefnProvider):
    '''
    Topic tree for application. Note that hierarchy can be 
    extended at run-time (e.g. by modules or plugins), 
    and that more than one hierarchy can be used as 
    specification. In this case, the first "provider" 
    to provide a topic specification will be used. 
    '''\
"""

defaultTopicTreeSpecFooter = \
"""\
# Following lines will cause the above topic tree 
# specification to be registered with pubsub as soon as
# you import this file.

from pubsub import pub
pub.addTopicDefnProvider( MyTopicTree() )
"""


def printTreeSpec(rootTopic=None, **kwargs):
    '''Prints the topic tree specification starting from rootTopic. 
    If not specified, the whole topic tree is printed. The kwargs are the 
    same as TopicTreeAsSpec's constructor. If no header or footer are given, the 
    defaults are used (see defaultTopicTreeSpecHeader and 
    defaultTopicTreeSpecFooter), such that the resulting output can be 
    imported in your application. E.g.::
    
        pyFile = file('appTopicTree.py','w')
        printTreeSpec( pyFile )
        pyFile.close()
        import appTopicTree
    '''
    kwargs.setdefault('header', defaultTopicTreeSpecHeader)
    kwargs.setdefault('footer', defaultTopicTreeSpecFooter)
    printer = TopicTreeAsSpec(**kwargs)
    if rootTopic is None:
        from pubsub import pub
        rootTopic = pub.getDefaultRootTopic()
    assert rootTopic is not None
    printer.traverse(rootTopic)


class Enum:
    '''Used only internally. Represent one value out of an enumeration 
    set.  It is meant to be used as:: 
    
        class YourAllowedValues:
            enum1 = Enum()
            # or:
            enum2 = Enum(value)
            # or:
            enum3 = Enum(value, 'descriptionLine1')
            # or:
            enum3 = Enum(None, 'descriptionLine1', 'descriptionLine2', ...)
            
        val = YourAllowedValues.enum1
        ...
        if val is YourAllowedValues.enum1:
            ...
    '''
    nextValue = 0
    values = set()
    
    def __init__(self, value=None, *desc):
        '''Use value if given, otherwise use next integer.'''
        self.desc = '\n'.join(desc)
        if value is None:
            assert Enum.nextValue not in Enum.values
            self.value = Enum.nextValue
            Enum.values.add(self.value)
            
            Enum.nextValue += 1
            # check that we haven't run out of integers!
            if Enum.nextValue == 0:
                raise RuntimeError('Ran out of enumeration values?')
            
        else:
            try:
                value + Enum.nextValue
                raise ValueError('Not allowed to assign integer to enumerations')
            except TypeError:
                pass
            self.value = value
            if self.value not in Enum.values:
                Enum.values.add(self.value)


