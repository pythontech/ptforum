#=======================================================================
#       Generic forum and site, subclassable
#=======================================================================
import logging
import os
import subprocess
import re
import sys
PY3 = sys.version_info[0] >= 3
import time
if PY3:
    from urllib.error import HTTPError
    from urllib.parse import urlsplit, quote
    from urllib.request import build_opener, Request, HTTPCookieProcessor
    from http.cookiejar import CookieJar
else:
    from urlparse import urlsplit
    from urllib2 import quote, build_opener, Request, HTTPCookieProcessor, HTTPError
    from cookielib import CookieJar

_logger = logging.getLogger('ptforum')

class Site(object):
    def __init__(self, baseUrl=None, cacheDir=None, 
                 fromPattern='%s', messageIdPattern=None, pageDelay=0,
                 sendmail='/usr/lib/sendmail'):
        if messageIdPattern is None:
            domain = urlsplit(baseUrl)[1].split(':')[0]
            if domain.startswith('www.'):
                domain = domain[4:]
            messageIdPattern = '%p@' + domain
        self.baseUrl = baseUrl
        self.set_cache(cacheDir)
        self.fromPattern = fromPattern
        self.messageIdPattern = messageIdPattern
        self.pageDelay = pageDelay
        self.sendmail = sendmail
        # User agent for HTTP requests
        cj = CookieJar()
        self.agent = build_opener(HTTPCookieProcessor(cj))

    def __repr__(self):
        return '<%s "%s">' % (self.__class__, self.baseUrl)

    def set_cache(self, cacheDir):
        if cacheDir is not None:
            self.cacheDir = os.path.expanduser(cacheDir)
        else:
            self.cacheDir = None

    def login(self, username, password):
        '''Post login credentials (needed to view some forums).'''
        raise NotImplementedError('%s needs to implement login method'
                                  % self.__class__)

    def get_forum_page(self, forum):
        '''Get the main page for a forum, containing a list of topics.'''
        raise NotImplementedError('%s needs to implement get_forum_page method'
                                  % self.__class__)

    def forum_page_topics(self, forum, html):
        '''Find all the topics on a forum page.'''
        raise NotImplementedError('%s needs to implement forum_page_topics method'
                                  % self.__class__)

    def get_topic_page(self, topic):
        '''Get main page of topic, containing list of posts.'''
        raise NotImplementedError('%s needs to implement get_topic_page method'
                                  % self.__class__)

    def topic_page_posts(self, topic, html):
        '''Scan a topic page and get a list of posts.'''
        raise NotImplementedError('%s needs to implement topic_page_posts method'
                                  % self.__class__)

    def forum_post_as_email(self, forum, post):
        '''Convert a post to email'''
        topic = post.topic
        sre, subject = re.match(r'(Re: )?(.*)',
                                post.subject).groups()
        if subject == '':
            if post.pid != topic.firstpost:
                sre = 'Re: '
            subject = topic.title or 'topic %s' % topic.tid
        subject = (sre or '') + forum.subjectPrefix + subject
        if post.datetime is not None:
            pass
        zauthor,n = re.subn(r'[^-A-Za-z0-9]+','_', post.author)
        fromm = _subst(self.fromPattern, u=zauthor)
        msgid = _subst(self.messageIdPattern, p=post.pid)
        hbody = ('<html><body>' +
                 post.body +
                 '</body></html>').encode('utf-8')
        try:
            from email.Message import Message 
            from email.Header import Header
            from email.Utils import formatdate
            # Force quoted-printable for utf-8 instead of base64 (for Thunderbird "View source")
            import email.Charset as cs
        except ImportError:
            from email.message import Message
            from email.header import Header
            from email.utils import formatdate
            import email.charset as cs
        #cs.add_charset('utf-8', cs.SHORTEST, cs.QP, 'utf-8')
        msg = Message()
        msg.add_header('From', fromm)
        msg.add_header('To', forum.recipient)
        hsubj = Header(subject)
        msg.add_header('Subject', str(hsubj))
        msg.add_header('Message-ID', '<%s>' % msgid)
        if topic.firstpost:
            firstid = _subst(self.messageIdPattern, p=topic.firstpost)
            msg.add_header('In-Reply-To', '<%s>' % firstid)
            msg.add_header('References', '<%s>' % firstid)
        if post.datetime is not None:
            date = formatdate(post.datetime)
            msg.add_header('Date', date)
        msg.set_payload(hbody)
        msg.set_type('text/html')
        msg.set_charset('utf-8')
        if hasattr(msg, 'as_bytes'): # PY3
            return msg.as_bytes()
        else:
            return msg.as_string()

    def get_page(self, relurl, query={}):
        '''Get a page from the site.  If cacheDir defined, use file from there, if present.'''
        url = self.baseUrl + relurl
        if query:
            url += '?' + urlencode(query)
        if self.cacheDir:
            tail = url.split('/')[-1]
            cachefile = '%s/%s' % (self.cacheDir, tail)
            if os.path.exists(cachefile):
                _logger.debug('Using cache: %s', cachefile)
                with open(cachefile,'r') as f:
                    content = f.read()
            else:
                content = self.really_get_page(url)
                try:
                    with open(cachefile,'wb') as f:
                        f.write(content)
                except Exception as e:
                    sys.stderr.write('Cannot write %s: %s\n' %
                                     (cachefile, e.args[0]))
                    #_logger.error('cache', exc_info=True)
                    pass
        else:
            content = self.really_get_page(url)
        return content

    def post_page(self, relurl, query={}):
        '''Post a request to the site, returning the resulting page content.'''
        url = self.baseUrl + relurl
        data = ''
        if query:
            data = urlencode(query)
        req = Request(url, headers={
                'User-Agent': 'curl/7.47.0', # raspberrypi.org dislikes python
                'Accept': '*/*',
                })
        doc = self.agent.open(req, data)
        content = doc.read()
        return content

    def really_get_page(self, url):
        '''Get a page, without consulting the cache.'''
        _logger.info("GET %s", url)
        req = Request(url, headers={
                'User-Agent': 'curl/7.47.0', # raspberrypi.org dislikes python
                'Accept': '*/*',
                })
        if self.pageDelay:
            time.sleep(self.pageDelay)
        try:
            doc = self.agent.open(req)
        except HTTPError as e:
            #print('HTTPError', vars(e))
            #print(e.hdrs)
            #while True:
            #    s = e.readline()
            #    if not s: break
            #    print(s)
            raise
        content = doc.read()
        return content

class Forum(object):
    def __init__(self, site=None, forumId='1', baseUrl=None,
                 savefile='forum.save', dumpDir='.', cacheDir=None,
                 subjectPrefix='',
                 subjectRemove='',
                 fromPattern='%s', recipient=None, messageIdPattern='%p',
                 pageDelay=0, sendmail='/usr/lib/sendmail'):
        if site is None:
            site = Site(baseUrl=baseUrl,
                        fromPattern=fromPattern, messageIdPattern=messageIdPattern,
                        pageDelay=pageDelay, cacheDir=cacheDir,
                        sendmail=sendmail)
        self.site = site
        self.forumId = forumId
        if savefile is not None:
            savefile = os.path.expanduser(savefile)
        self.savefile = savefile
        if dumpDir is not None:
            dumpDir = os.path.expanduser(dumpDir)
        self.dumpDir = dumpDir
        self.subjectPrefix = subjectPrefix
        self.subjectRemove = subjectRemove
        self.recipient = recipient
        self.use_cache = False
        self.topics = {}

    def dump(self, text, fname):
        if not self.dumpDir:
            return
        filename = '%s/%s-%s' % (self.dumpDir, self.forumId, fname)
        try:
            with open(filename,'w') as f:
                f.write(text)
            _logger.info('Wrote %s', filename)
        except Exception as e:
            _logger.error('Writing %s: %s', filename, e)

    def state_save(self):
        '''Save topic details to persistent store'''
        with open(self.savefile,'w') as save:
            tids = sorted(self.topics.keys())
            # print tids
            for tid in tids:
                topic = self.topics[tid]
                save.write('topic %s firstpost=%s lastpost=%s\n' %
                           (tid, 
                            topic.firstpost or '', topic.lastpost or ''))

    def state_load(self):
        '''Load topic details from persistent store'''
        if not os.path.exists(self.savefile):
            _logger.warning('Skipping missing savefile %s', self.savefile)
            return
        with open(self.savefile) as save:
            topics = {}
            topicRE = re.compile(r'topic (\d+) firstpost=(\d*) lastpost=(\d*)')
            for line in save:
                m = topicRE.match(line)
                if m:
                    tid, first, last = m.groups()
                    topics[tid] = Topic(tid=tid,
                                        firstpost=first,
                                        lastpost=last)
                else:
                    raise ValueError('Unknown line in %s: %s\n' %
                                     (self.savefile, line))
        self.topics = topics

    def mail_new(self):
        newposts = self.new_posts()
        for post in newposts:
            self.post_mail(post)
        # For backward compatibility, update lastpost when sent
        self.update_lastposts(newposts)

    def new_posts(self):
        posts = []
        page = self.site.get_forum_page(self)
        if hasattr(self.site, 'forum_page_posts'):
            # Direct forum -> posts e.g. from Atom feed
            for post in self.site.forum_page_posts(self, page):
                if post.is_new():
                    posts.append(post)
        else:
            topics = self.site.forum_page_topics(self, page)
            _logger.info('forum %s topic=%d', self.forumId, len(topics))
            for topic in topics:
                posts += self.topic_new_posts(topic)
        posts.sort(key=lambda p: p.datetime)
        _logger.debug('forum %s new_posts=%d', self.forumId, len(posts))
        return posts

    def topic_find(self, tid):
        '''Find or create a topic'''
        topic = self.topics.get(tid)
        if not topic:
            topic = self.topics[tid] = Topic(tid=tid)
        return topic

    def post_as_email(self, post):
        '''Convert a post to email'''
        return self.site.forum_post_as_email(self, post)

    def topic_new_posts(self, topic):
        '''Get the new posts on ths topic'''
        html = self.site.get_topic_page(topic)
        posts = self.site.topic_page_posts(topic, html)
        new_posts = [p  for p in posts  if p.is_new()]
        _logger.info('topic %s posts=%d new=%d',
                     topic.tid, len(posts), len(new_posts))
        return new_posts

    def update_lastposts(self, posts):
        '''Update lastpost attribute of topics to include given posts'''
        for post in posts:
            if post.is_new():
                # pid > lastpost
                post.topic.lastpost = post.pid

    def post_mail(self, post):
        email = self.post_as_email(post)
        # FIXME sendmail
        if 0:
            print(email)
        else:
            _logger.info('posting %s', post.pid)
            cmd = self.site.sendmail+' -t -oi'
            _logger.debug('command %r', cmd)
            if False:
                with open(os.path.expanduser('~/ptforum-tmp.eml'),'wb') as f:
                    f.write(email)
            p = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE)
            p.communicate(email)

class Topic(object):
    def __init__(self, tid, title=None, author=None, replies=0, firstpost=None, lastpost=None):
        self.tid = tid
        self.title = title
        self.author = author
        self.replies = replies
        self.firstpost = firstpost
        self.lastpost = lastpost

    def __repr__(self):
        return '<Topic %s %r>' % (self.tid, self.title)

class Post(object):
    def __init__(self, pid, subject=None, author=None, datetime=None, body=None, topic=None):
        self.pid = pid
        self.subject = subject
        self.author = author
        self.datetime = datetime
        self.body = body
        self.topic = topic

    def __repr__(self):
        return '<Post %s %r>' % (self.pid, self.subject)

    def is_new(self):
        return (int(self.pid) > int(self.topic.lastpost or 0))

def urlencode(vars):
    return '&'.join(['='.join([quote(t,safe='')  for t in kv])
                     for kv in vars.items()])

def _subst(pattern, **kw):
    result,n = re.subn(r'%(.)', lambda m: kw.get(m.group(1),''), pattern)
    return result
