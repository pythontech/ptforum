#!/usr/bin/env python
#=======================================================================
#       Example of scraping two forums on a site
#=======================================================================
import ptforum
import ptforum.phpbb3
import logging

# Where to send email to
me = 'me@localhost'             # <-- Change to your email address
fromdomain = 'example.com'

rpi = ptforum.phpbb3.Site(baseUrl='http://www.raspberrypi.org/phpBB3',
                          fromPattern='%u-rpi@'+fromdomain,
                          messageIdPattern='%p-rpi@'+fromdomain,
                          pageDelay=1)

rpi_python = ptforum.Forum(site=rpi,
                           forumId='32',
                           savefile="~/tmp/rpi-python.save",
                           dumpDir='~/tmp',
                           subjectPrefix='[RPi Python] ',
                           recipient=me)

rpi_raspbian = ptforum.Forum(site=rpi,
                             forumId='66',
                             savefile="~/tmp/rpi-raspbian.save",
                             dumpDir='~/tmp',
                             subjectPrefix='[RPi Raspbian] ',
                             recipient=me)

logging.basicConfig(level=logging.WARNING)

for forum in (rpi_python, rpi_raspbian):
    forum.state_load()
    try:
        posts = forum.new_posts()
        for post in posts:
            forum.post_mail(post)
        forum.update_lastposts(posts)
    finally:
        forum.state_save()
