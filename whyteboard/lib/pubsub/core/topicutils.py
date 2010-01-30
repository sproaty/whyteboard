'''
Various little utilities used by topic-related modules. 
'''

from textwrap import TextWrapper, dedent


def smartDedent(paragraph):
    '''
    Dedents a paragraph that is a triple-quoted string. If the first
    line of the paragraph does not contain blanks, the dedent is applied
    to the remainder of the paragraph. This handles the case where a user
    types a documentation string as 
    
    """A long string spanning
    several lines."""
    
    Regular textwrap.dedent() will do nothing to this text because of the 
    first line. Requiring that the user type the docs as """\ with line 
    continuation is not acceptable. 
    '''
    if paragraph.startswith(' '):
        para = dedent(paragraph)
    else:
        lines = paragraph.split('\n')
        exceptFirst = dedent('\n'.join(lines[1:]))
        para = lines[0]+exceptFirst
    return para


class TopicNameInvalid(RuntimeError):
    def __init__(self, name, reason):
        msg = 'Topic name "%s" invalid: %s' % (name, reason)
        RuntimeError.__init__(self, msg)


def stringize(topicNameTuple):
    '''If topicName is a string, do nothing and return it 
    as is. Otherwise, convert it to one, using dotted notation,
    i.e. ('a','b','c') => 'a.b.c'. Empty name is not allowed 
    (ValueError). The reverse operation is tupleize(topicName).'''
    if isinstance(topicNameTuple, str):
        return topicNameTuple
    
    try:
        name = '.'.join(topicNameTuple)
    except Exception, exc:
        raise TopicNameInvalid(topicNameTuple, str(exc))
    
    return name


def tupleize(topicName):
    '''If topicName is a tuple of strings, do nothing and return it 
    as is. Otherwise, convert it to one, assuming dotted notation 
    used for topicName. I.e. 'a.b.c' => ('a','b','c'). Empty 
    topicName is not allowed (ValueError). The reverse operation 
    is stringize(topicNameTuple).'''
    # assume name is most often str; if more often tuple, 
    # then better use isinstance(name, tuple)
    if isinstance(topicName, str): 
        topicTuple = tuple(topicName.split('.'))
    else:
        topicTuple = tuple(topicName) # assume already tuple of strings
        
    if not topicTuple:
        raise TopicNameInvalid(topicTuple, "Topic name can't be empty!")
                
    return topicTuple


