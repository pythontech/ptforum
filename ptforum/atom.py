#=======================================================================
#       Atom feed e.g. from phpBB3
#=======================================================================
import ptforum
import re
import calendar
import time
import urlparse
import xml.etree.ElementTree

# XML namespaces
atom='{http://www.w3.org/2005/Atom}'

class Site(ptforum.Site):
    '''Atom feed'''

    def get_forum_page(self, forum):
        xml = self.get_page('/forum/%s' % forum.forumId)
        return xml

    def forum_page_posts(self, forum, page_xml):
        '''
        <feed>
         <title>...
         <subtitle>...
         <link href="..." />
         <updated>$date</updated>
         <author><name>$site</name></author>
         <id>...</id>
         <entry>
          <author><name>$author</name></author>
          <updated>$date</updated>
          <published>$date</published>
          <id>$posturl</id>
          <link href="$posturl"/>
          <title type="$type">$title</title>
          <category term="$forumname" scheme="$forumurl" label="$forumname"/>
          <content type="$type" xml:base="$baseurl>$content</content>
         </entry>
        '''
        xfeed = xml.etree.ElementTree.XML(page_xml)
        if xfeed.tag != atom+'feed':
            raise ValueError('Root element is %s, not atom:feed' % xfeed.tag)
        posts = []
        for xentry in xfeed.findall(atom+'entry'):
            pid = name = datetime = subject = body = None
            # Get author name
            xauthor = xentry.find(atom+'author')
            xname = xauthor.find(atom+'name')
            name = xname.text
            # Get published date
            xpublished = xentry.find(atom+'published')
            pubdate = xpublished.text # yyyymmddThhmmss
            # Get post URL and hence topic id
            url = xentry.find(atom+'id').text
            pid = url_params(url)['p'][0]
            tid = url_params(url)['t'][0]
            topic = forum.topic_find(tid)
            # Get post title
            xtitle = xentry.find(atom+'title')
            ttype = xtitle.attrib['type']
            subject = xtitle.text
            # Get content
            xcontent = xentry.find(atom+'content')
            ctype = xcontent.attrib['type']
            body = xcontent.text
            post = ptforum.Post(pid=pid, topic=topic,
                                author=name,
                                datetime=convert_time(pubdate),
                                subject=subject,
                                body=body)
            posts.append(post)
        posts.sort(key=lambda p: p.datetime)
        for p in posts:
            if not p.topic.firstpost:
                p.topic.firstpost = p.pid
            if not p.topic.title:
                p.topic.title = p.subject
        return posts

# FIXME allow timezone offset
timeRE = re.compile(r'(\d\d\d\d)-(\d\d)-(\d\d)T(\d\d):(\d\d):(\d\d)(?:\+00:00)?')

def convert_time(date):
    """Convert e.g. 2012-01-04T21:42:54+00:00"""
    m = timeRE.match(date)
    if not m:
        raise ValueError('Unexpected date format %r' % date)
    year,mn,dy,hr,mi,se = [int(g)  for g in m.groups()]
    t = calendar.timegm((year,mn,dy, hr,mi,se, -1,-1,0))
    return int(t)

def url_params(url):
    squery = urlparse.urlparse(url).query
    params = urlparse.parse_qs(squery)
    return params

