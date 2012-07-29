ptforum
=======

Screen-scrape web-based forums and send posts as email.

Pre-requisites
==============

* BeautifulSoup : used to parse possibly malformed HTML and XML.  See http://www.crummy.com/software/BeautifulSoup/  I have verion 3.0.7a on my production installation; there are newer versions e.g. version 4 but I have not tested with these.

* A Linux or other similar system to run the script on (it uses sendmail to send the emails).

Getting Going
=============

Ensure you have both ptforum and BeautifulSoup in your python path.

Take the example.py script and adapt for your needs.  You will need to change the 'me' email address, and probably add to or modify the Forum instances depending on which you are interested in.

On the first run, you will get warning about missing savefiles - these will be created as needed.  The first time you may get hundreds of emails since the script will send all posts from the first page of each topic on the first page of each forum.  On subsequent runs, you should only get new posts.

Typically when you are confident it is working OK, you will want to run the script automatically at regular intervals (e.g. every couple of hours).  A good way to do this is via a cron job - instructions for doing this are outside the scope of this document.

BUGS
====

* Only reads the first page of each forum.  Normally this has the most recently updated topics, but if there is activity in many topics between runs, you may miss some posts.
* Only reads the first page of each topic.  Newer posts tend to appear at the end, so this is definite lose for long-running discussions.
* Parse errors may hot be handled gracefully, so if the layout changes you may just get a python traceback.
* Save file grows indefinitely (one line per topic).  Maybe it should prune sufficiently old topics.
* It may not handle HTML entities correctly e.g. angle brackets in text get down-converted.  So code listings may get messed up.
