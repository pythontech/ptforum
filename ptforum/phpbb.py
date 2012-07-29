#=======================================================================
#	Scrape phpBB forum pages
#	Converted from smf2.py and perl PythonTech::PhpBB
#=======================================================================
import re
import time
import ptforum
import ptforum.soup as soup

class Site(ptforum.Site):
    '''Site which uses phpBB'''

    def login(self, username, password):
        '''Post login credentials (needed to view some forums)'''
        html = self.post_page('/login.php', dict(username=username,
                                                 password=password,
                                                 login='Log in'))
        return html

    def get_forum_page(self, forum):
        '''Get the main page for a forum, containing a list of topics.'''
	html = self.get_page('/viewforum.php',
                             {'f': forum.forumId})
	return html

    def get_topic_page(self, topic):
        '''Get main page of topic, containing list of posts.'''
	html = self.get_page('/viewtopic.php',
                             {'t': topic.tid})
	return html

    def get_page(self, url, query={}):
        '''Get a web page, and fix up badness which even BeautifulSoup can't handle.'''
        html = ptforum.Site.get_page(self, url, query)
        # Pages from forumer bizarrely have <!\227- base url -->
        # which is an EM DASH in Windows code page 1252
        html = html.replace('<!\227-','<!--')
        # Avoid unicode weirdness (BeautifulSoup bug?)
        html = html.replace('&nbsp;', ' ')
        return html

    def forum_page_topics(self, forum, html):
	'''Find all the topics on a forum page.
        Page structure:
          <table ...>
           <table class="forumline">
            <tr><th>...
            <tr>
             <td>...</td>
             <td>...<span class="topictitle"></span><a href="...">topic title</a>...</td>
             <td><span>8</span></td>
             <td><span>&nbsp<a href="...">authorid</a>&nbsp;</span></td>
             <td><span>41</span></td>
             <td><span> Sun May 16, 2010 3:06 pm <br /><a>...</a> <a href="viewtopic...">...</td>
             ...
        </tr>
            
        '''
	topics = []
	doc = soup.BeautifulSoup(html, convertEntities='html')
        #soup.dump(doc)
        #self.dump(str(doc), 'topics.xml')
        #for table in doc.findAll('table'):
        #    print str(table)[:79].replace("\n",'')
        index = doc.find(soup.tagclass('table', 'forumline'))
        for tr in index.findAll('tr'):
            tds = tr.findAll('td')
            if len(tds) < 6:
                continue
            ntype, ntopic, nreplies, nauthor, nviews, nlastpost = tds[:6]

            title = tid = replies = author = lastpost = None
            topica = ntopic.find(soup.tagclass('a','topictitle'))
            if topica:
                title = soup.cdata(topica)
                href = topica['href']
                m = re.match('.*?t=(\d+)', href)
                if m:
                    tid = m.group(1)
            replies = soup.cdata(nreplies)
            authora = nauthor.find('a')
            if authora:
                author = soup.cdata(authora)
            # lastpost = soup.cdata(nlastpost)
            #print 'tid=%s title=%s author=%s replies=%s' % (tid, repr(title), author, replies)
	    # Create or update topic
	    topic = forum.topic_find(tid)
	    topic.title = title
	    topic.author = author
	    topic.replies = replies

	    topics.append(topic)
	return topics

    def topic_page_posts(self, topic, html):
	'''Scan a topic page and get a list of posts
         <table class="forumline">
         <tr>
          <td>...<a name="425" id="425"></a><strong>someuser</strong>...</td>
          <td><table>...</table> <table><tr><td class="postbody">...</td></tr>
        '''
	posts = []
	doc = soup.BeautifulSoup(html, fromEncoding='utf-8', convertEntities='html')
        titletd = doc.find(soup.tagclass('td','maintitle'))
        title = soup.cdata(titletd).strip()
        #print 'title',title.encode('utf-8')
        table = doc.find(soup.tagclass('table','forumline'))
        for tr in table.findAll('tr',recursive=False):
            tds = tr.findAll('td',recursive=False)
            if len(tds) < 2:
                continue
            #print str(tr)[:79]
            nauthor, nmessage = tds[:2]
            pid = author = datetime = subject = body = None
            namea = nauthor.find('a', {'name':True})
            if namea:
                #print ' a',namea
                pid = namea['name']
            b = nauthor.find(['strong','b'])
            if b:
                #print ' b',b
                author = soup.cdata(b)
            posttd = nmessage.find(soup.tagclass('td','postdetails'))
            if posttd:
                dateetc = soup.cdata(posttd)
                datetime = fixdate(dateetc)
            bodytd = nmessage.find(soup.tagclass('td','postbody'))
            if bodytd:
                subject = ''
                contents = bodytd.contents
                # Remove guff from start
                if contents and contents[0] == '\n':
                    contents = contents[1:]
                if contents and contents[0].name == 'hr':
                    contents = contents[1:]
                #for c in bodytd.contents:
                #    print '+',repr(str(c))
                body = ''.join(map(unicode, contents))
                # print ' body',repr(body)
	    post = ptforum.Post(pid=pid, topic=topic,
                                author=author, 
                                datetime=datetime,
                                subject=subject,
                                body=body)
	    posts.append(post)

            if not topic.firstpost:
                topic.firstpost = pid
	return posts

Forum = ptforum.Forum

def fixdate(when):
    '''Convert date and time as given by PhpBB into a timestamp.
    Input can be e.g. "Sun May 09, 2010 3:06 pm"
    '''
    m = re.search(r' (\w{3}) (\d{2}), (\d{4}) (\d+):(\d{2}) (am|pm)', when)
    if not m:
        print ' no date match',when
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
    t = time.mktime(map(int,(year,mn,dy, hr,mm,0, -1,-1,0)))
    return int(t)
