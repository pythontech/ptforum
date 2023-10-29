#=======================================================================
#       Use BeautifulSoup to make sense of not-quite-HTML pages
#=======================================================================
from bs4 import BeautifulSoup

def tagclass(name,klass):
    '''Create a matcher for BeautifulSoup find or findAll etc.
    which matches a tag of given name and of the given class'''
    def match(tag):
        if tag.name != name:
            return False
        classes = tag.get('class',[])
        return klass in classes
    return match

def cdata(tag):
    '''Get the character data inside an element, ignoring all markup'''
    return ''.join(tag.findAll(text=True))

def dump(tag,indent=0):
    for child in tag.findAll(lambda x: getattr(x,'name',None),recursive=False):
        print('%*s%s' % (indent,'', child.name))
        dump(child,indent+1)

