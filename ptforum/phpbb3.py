#=======================================================================
"""
Scrape phpBB3 forum pages
"""
#       Converted from phpbb.py
#=======================================================================
import re
import time
import ptforum
import ptforum.soup as soup
import logging

t_nRE = re.compile(r'\bt=(\d+)')
p_nRE = re.compile(r'\bp=(\d+)')

_logger = logging.getLogger('ptforum.phpbb3')

class Site(ptforum.Site):
    """Site which uses phpBB"""

    def login(self, username, password):
        pass

    def get_forum_page(self, forum):
        """Get the main page for a forum, containing a list of topics."""
        html = self.get_page('/viewforum.php',
                             {'f': str(forum.forumId)})
        return html

    def get_topic_page(self, topic):
        """Get main page of topic, containing list of posts."""
        html = self.get_page('/viewtopic.php',
                             {'t': str(topic.tid)})
        return html

    def get_page(self, url, query={}):
        """Get a web page, and fix up badness which even BeautifulSoup can't handle."""
        html = ptforum.Site.get_page(self, url, query)
        ## Pages from forumer bizarrely have <!\227- base url -->
        ## which is an EM DASH in Windows code page 1252
        #html = html.replace(b'<!\227-',b'<!--')
        ## Avoid unicode weirdness (BeautifulSoup bug?)
        #html = html.replace(b'&nbsp;', b' ')
        return html

    def forum_page_topics(self, forum, html):
        """Find all the topics on a forum page.
        Page structure:
          <ul class="topiclist topics">
           <li class="row bg1">
            <dl class="row-fluid">
             <dt ...>
              <a...>
              <a class="topictitle" href="./viewtopic.php?f=35&t=10369">@title</a>
             <dd ...>
              7 <dfn>Replies</dfn>
             <dd ...>
              <a href="./memberlist.php...">@USER</a>
             <dd ...>
              <dfn>Last post</dfn> by <a href="./memberlist.php..">@LASTUSER</a>
              <br>
              <a href="./viewtopic.php?f=35&t=10396&p=117246#p117246"><time...></a>
             ...
           <li>...
           ...
         <div class="paging ...">
          <span>
           <a href="./viewforum.php?f=35&start=25">2</a>

        OR

        <>
         <li class="row bg2">
          <dl class="icon topic_read">
           <dt title="No unread posts">
            <div class="list-inner">
             <a class="topictitle" href="./viewtopic.php?t=@TID">@TITLE</a>
             <span class="topic-ap"><i></i></span> by
             <a class="username" href="./memberlist.php?...u=@UID">@USER</a>
             * Thus Oct 26, 2023 7:53 am
             <div class="r-lastpost-container">
              <a class="r-lastpost" href="./viewtopic.php?p=@PID#@PID" title="...">
               <i></i></a>
        N.B. There may be more than one <ul class="topiclist topics"> 
        """
        topics = []
        doc = soup.BeautifulSoup(html, features='lxml')
        for index in doc.findAll(soup.tagclass('ul', 'topics')):
            for li in index.findAll('li'):
                _logger.debug('-- li %s', li['class'])
                dl = li.find('dl')
                dt = dl.find('dt')
                title = tid = replies = author = lastpost = None
                topica = dt.find(soup.tagclass('a','topictitle'))
                if topica:
                    title = soup.cdata(topica)
                    _logger.info('TITLE %s', title)
                    href = topica['href']
                    m = t_nRE.search(href)
                    if m:
                        tid = m.group(1)
                        _logger.info('TID %s', tid)
                    else:
                        _logger.warn('** no tid')
                for dd in dl.findAll('dd'):
                    dfn = dd.find('dfn')
                    if not dfn:
                        a = dd.find('a')
                        href = a['href']
                        if 'memberlist.php' in href.split('?')[0]:
                            author = soup.cdata(a)
                            _logger.info('AUTHOR %s', author)
                    else:
                        text = soup.cdata(dfn)
                        if 'Replies' in text:
                            replies = soup.cdata(dd).split()[0]
                            _logger.info('REPLIES %s', replies)
                        elif 'Last post' in text:
                            _logger.debug('-- Last post')
                            for a in dd.findAll('a'):
                                href = a['href']
                                if 'viewtopic.php' in href.split('?')[0]:
                                    m = p_nRE.search(href)
                                    if m:
                                        lastpost = m.group(1)
                                        _logger.info('LASTPOST %s', lastpost)
                                    else:
                                        _logger.warn('** t=%s no lastpost',
                                                     tid)
                # Create or update topic
                topic = forum.topic_find(tid)
                topic.title = title
                topic.author = author
                topic.replies = replies

                topics.append(topic)
        return topics

    def topic_page_posts(self, topic, html):
        """Scan a topic page and get a list of posts
        <div...>
          <h2>SUBJECT</h2>
        </div>
        <div id="pPID" class="post ...">
         <div class="postbody ...">
          <div class="author">by <strong><a href="./memberlist.php...">AUTHOR</a></strong>
           &raquo; DAY MON DD, YEAR H:MM PM </div>
          <div class="content">BODY</div>
        """
        posts = []
        doc = soup.BeautifulSoup(html, features='lxml')
        h2 = doc.find('h2')
        title = soup.cdata(h2)
        _logger.info('TITLE %s', title)
        for post in doc.findAll(soup.tagclass('div','post')):
            pid = author = datetime = subject = body = None
            pid = post['id'].lstrip('p')     # E.g. 'p12345' -> '12345'
            author, datetime = self.post_author_datetime(post)
            contdiv = post.find(soup.tagclass('div','content'))
            if not contdiv:
                _logger.warn('** no div.content')
            else:
                contents = contdiv.contents
                body = ''.join(str(part) for part in contents)
            post = ptforum.Post(pid=pid, topic=topic,
                                author=author, 
                                datetime=datetime,
                                subject=subject or title,
                                body=body)
            posts.append(post)

            if not topic.firstpost:
                topic.firstpost = pid
        return posts

    def post_author_datetime(self, post):
        author = datetime = None
        authdiv = post.find(soup.tagclass('div','author'))
        if authdiv:
            a = authdiv.find('a')
            if not a:
                _logger.warn('** no a in div.author')
            else:
                author = soup.cdata(a)
                _logger.info('AUTHOR %s' % author)
            date_cdata = soup.cdata(authdiv)
            _logger.debug('date %r', date_cdata)
            datetime = fixdate(date_cdata)
            _logger.info('DATETIME %s' % datetime)
        else:
            profile = post.find(soup.tagclass('dl','postprofile'))
            if not profile:
                _logger.warn('** neither div.author nor dl.postprofile')
            else:
                a = profile.find('a')
                if not a:
                    _logger.warn('** no a in dl.profile')
                author = soup.cdata(a)
            authdiv = post.find(soup.tagclass('p','author'))
            if not authdiv:
                _logger.warn('** neither div.author nor p.author')
            a = authdiv.find('a')
            if not a:
                _logger.warn('** no a in p.author')
            else:
                date_cdata = soup.cdata(a)
                _logger.debug('date %r', date_cdata)
                datetime = fixdate(date_cdata)
                _logger.info('DATETIME %s' % datetime)
        return author, datetime

Forum = ptforum.Forum

def fixdate(when):
    """Convert date and time as given by PhpBB into a timestamp.
    Input can be e.g. "Sun May 09, 2010 3:06 pm"
    """
    m = re.search(r' (\w{3}) (\d{2}), (\d{4}) (\d+):(\d{2}) (am|pm)', when)
    if not m:
        print(' no date match',when)
        return '?'
    mon,day,year,hh,mm,ampm = m.groups()
    dy = day
    mn = dict(Jan=1,Feb=2,Mar=3,Apr=4,May=5,Jun=6,
              Jul=7,Aug=8,Sep=9,Oct=10,Nov=11,Dec=12)[mon]
    hr = int(hh)
    if ampm=='pm':
        if hr != 12: hr += 12
    else:
        if hr == 12: hr -= 12
    # Assumes in current timezone
    t = time.mktime(tuple(int(x) for x in (year,mn,dy, hr,mm,0, -1,-1,0)))
    return int(t)
