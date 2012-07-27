#=======================================================================
#	$Id: smf2.py,v 1.2 2010/06/09 14:19:59 pythontech Exp $
#	Scrape SMF2 forum pages
#	Converted from perl PythonTech::SMF2
#=======================================================================
import re
import time
import ptforum
import ptforum.soup as soup

class Site(ptforum.Site):
    '''Site which uses SMF2'''

    def get_forum_page(self, forum):
        '''Get the main page for a forum, containing a list of topics.'''
	html = self.get_page('/index.php',
                             {'board': forum.forumId+'.0'})
	return html

    def get_topic_page(self, topic):
        '''Get main page of topic, containing list of posts.'''
	html = self.get_page('/index.php',
                             {'topic': topic.tid+'.0'})
	return html


    def forum_page_topics(self, forum, html):
	'''Find all the topics on a forum page'''
	topics = []
	doc = soup.BeautifulSoup(html, convertEntities='html')
	index = doc.find('div', id='messageindex')
	subjtds = index.findAll(soup.tagclass('td','subject'))
	for subjtd in subjtds:
	    span = subjtd.find('span')
	    a = span.find('a')
	    href = a['href']
	    tid = re.search(r'topic[=,](\d+)', href).group(1)
	    title = a.string.strip()
	    tr = subjtd.parent
	    starttd = tr.find(soup.tagclass('td','starter'))
	    author = soup.cdata(starttd).strip()
	    reptd = tr.find(soup.tagclass('td','replies'))
	    replies = soup.cdata(reptd).strip()

	    # Create or update topic
	    topic = forum.topic_find(tid)
	    topic.title = title
	    topic.author = author
	    topic.replies = replies

	    topics.append(topic)
	return topics

    def topic_page_posts(self, topic, html):
	'''Scan a topic page and get a list of posts'''
	posts = []
	doc = soup.BeautifulSoup(html, convertEntities='html')
	padivs = doc.findAll(soup.tagclass('div','postarea'))
	for padiv in padivs:
	    pdiv = padiv.parent
	    poster = pdiv.find(soup.tagclass('div','poster'))
	    author = soup.cdata(poster.h4)
	    keyinfo = padiv.find(soup.tagclass('div','keyinfo'))
	    h5 = keyinfo.h5
	    subject = soup.cdata(h5.a)
	    dd = h5.findNextSibling('div')
	    dateetc = soup.cdata(dd).strip()
	    datetime = fixdate(dateetc)
	    post = padiv.find(soup.tagclass('div','post'))
            inner = post.find(soup.tagclass('div','inner'))
	    pid = re.match(r'msg_(\d+)',inner['id']).group(1)
	    body = unicode(str(inner),'utf-8')
	    # print 'body=',repr(body)
	    # print ("pid=%s author=%s datetime=%s subject=%s body=%s" % \
	    # (pid,author,dateetc,subject,body)).encode('utf-8')
	    
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
    '''Convert date and time as given by SMF2 into a timestamp.
    Input can be e.g. "Today at 08:30:19 PM"
    or "January 3, 2009, 12:08:34 AM"
    '''
    m = re.search(r'on: (?:(Today|Yesterday) at|(\w{3})\w* (\d+), (\d+),) (\d\d):(\d\d):(\d\d) (AM|PM)', when)
    (rel,mon,day,year,hh,mm,ss,ampm) = m.groups()
    if rel:
	# FIXME gmtime
        tm = time.time()
        if rel == 'Yesterday':
            tm -= 86400
	year,mn,dy = time.gmtime(tm)[:3]
    else:
	dy = day
	mn = dict(Jan=1,Feb=2,Mar=3,Apr=4,May=5,Jun=6,
		  Jul=7,Aug=8,Sep=9,Oct=10,Nov=11,Dec=12)[mon]
    hr = int(hh)
    if ampm=='PM':
	if hr != 12: hr += 12
    else:
	if hr == 12: hr -= 12
    # Assumes in current timezone
    t = time.mktime(map(int,(year,mn,dy, hr,mm,ss, -1,-1,0)))
    return int(t)
