#=======================================================================
#       Use BeautifulSoup to make sense of not-quite-HTML pages
#=======================================================================
import BeautifulSoup as BS

BeautifulSoup = BS.BeautifulSoup

def tagclass(name,klass):
    '''Create a matcher for BeautifulSoup find or findAll etc.
    which matches a tag of given name and of the given class'''
    return (lambda tag:
            tag.name==name and
            klass in tag.get('class','').split())

def cdata(tag):
    '''Get the character data inside an element, ignoring all markup'''
    return ''.join(tag.findAll(text=True))

def dump(tag,indent=0):
    for child in tag.findAll(lambda x: getattr(x,'name',None),recursive=False):
        print('%*s%s' % (indent,'', child.name))
        dump(child,indent+1)

