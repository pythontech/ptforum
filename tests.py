#=======================================================================
#       $Id: tests.py,v 1.1 2010/06/08 13:49:11 pythontech Exp $
#	Regression tests for ptforum
#=======================================================================
import ptforum.phpbb
import ptforum.smf2
import unittest

class FakePhpbbSite(ptforum.phpbb.Site):
    def __init__(self, fakedir='.', *args, **kw):
        ptforum.phpbb.Site.__init__(self, *args, **kw)
        self.fakedir = fakedir

    def really_get_page(self, url):
        fakefile = self.fakedir + '/' + url.split('/')[-1]
        content = open(fakefile).read()
        return content

class FakeSmf2Site(ptforum.smf2.Site):
    def __init__(self, fakedir='.', *args, **kw):
        ptforum.smf2.Site.__init__(self, *args, **kw)
        self.fakedir = fakedir

    def really_get_page(self, url):
        fakefile = self.fakedir + '/' + url.split('/')[-1]
        content = open(fakefile).read()
        return content

class TestPhpbb(unittest.TestCase):
    def test_topics(self):
        import ptforum.phpbb
        site = FakePhpbbSite(fakedir='testdata/phpbb',
                             baseUrl='http://phpbb.example.com',
                             fromPattern='%u@example.com')
        forum = ptforum.phpbb.Forum(site=site, forumId='4',
                                    savefile='testdata/phpbb.save',
                                    subjectPrefix='[ex] ',
                                    recipient='nobody')
        fpage = site.get_forum_page(forum)
        self.assertTrue('</html>' in fpage)
        topics = site.forum_page_topics(forum, fpage)
        self.assertEqual(len(topics), 20)
        topic = topics[2]
        self.assertEqual(topic.tid, '805')
        self.assertEqual(topic.title, 'back in water  tomorrow')
        tpage = site.get_topic_page(topic)
        self.assertTrue('</html>' in tpage)
        posts = site.topic_page_posts(topic, tpage)
        post = posts[1]
        self.assertEqual(post.pid, '4514')
        self.assertEqual(post.topic, topic)
        self.assertEqual(post.author, 'Deano')
        self.assertEqual(post.datetime, 1275593220)
        self.assertEqual(post.body[:30], '\nBest of luck, all the hard wo')
        mail = site.forum_post_as_email(forum, post)
        #print repr(mail)
        hdrs = mail_header_dict(mail)
        self.assertEqual(hdrs['from'], 'Deano@example.com')
        self.assertEqual(hdrs['to'], 'nobody')
        self.assertEqual(hdrs['message-id'], '<4514@phpbb.example.com>')
        subj1 = mail_header_dict(site.forum_post_as_email(forum, posts[0]))['subject']
        self.assertEqual(subj1, '[ex] back in water  tomorrow')

class TestSmf2(unittest.TestCase):
    def test_topics(self):
        import ptforum.smf2
        site = FakeSmf2Site(fakedir='testdata/smf2',
                            baseUrl='http://smf2.example.com',
                            fromPattern='%u@example.com')
        forum = ptforum.smf2.Forum(site=site, forumId='9',
                                   savefile='testdata/smf2.save',
                                   subjectPrefix='[ex2] ',
                                   recipient='nobody')
        fpage = site.get_forum_page(forum)
        self.assertTrue('</html>' in fpage)
        topics = site.forum_page_topics(forum, fpage)
        self.assertEqual(len(topics), 20)
        topic = topics[2]
        self.assertEqual(topic.tid, '38573')
        self.assertEqual(topic.title, 'FAQ: Should I trust/follow the advice I get in this forum?')
        tpage = site.get_topic_page(topic)
        self.assertTrue('</html>' in tpage)
        posts = site.topic_page_posts(topic, tpage)
        post = posts[1]
        self.assertEqual(post.pid, '174924')
        self.assertEqual(post.topic, topic)
        self.assertEqual(post.author, 'imcintyre')
        self.assertEqual(post.datetime, 1190211411)
        self.assertEqual(post.body[:30], '<div class="inner" id="msg_174')
        mail = site.forum_post_as_email(forum, post)
        #print repr(mail)
        hdrs = mail_header_dict(mail)
        self.assertEqual(hdrs['from'], 'imcintyre@example.com')
        self.assertEqual(hdrs['to'], 'nobody')
        self.assertEqual(hdrs['message-id'], '<174924@smf2.example.com>')
        subj1 = mail_header_dict(site.forum_post_as_email(forum, posts[0]))['subject']
        self.assertEqual(subj1, '[ex2] FAQ: Should I trust/follow the advice I get in this forum?')

def mail_header_dict(mail):
    hdrtext = mail.split('\n\n')[0]
    hdrs = {}
    for hdr in hdrtext.split('\n'):
        name, value = hdr.split(':',1)
        hdrs[name.lower()] = value.strip()
    return hdrs

if __name__=='__main__':
    unittest.main()
