ptforum
=======

Screen-scrape forums and send posts as email

Pre-requisites
==============

* BeautifulSoup : used to parse possibly malformed HTML and XML.  See http://www.crummy.com/software/BeautifulSoup/  I have verion 3.0.7a on my production installation but there are newer versions

BUGS
====

* Only reads the first page of each forum.  Normally this has the most recently updated topics, but if there is activity in many topubetween runs, you may miss some posts.
* Only reads the first page of each topic.  Newer posts tend to appear at the end, so this is definite lose for long-running discussions.
* Parse errors may hot be handled gracefully, so if the layout changes you may just get a python traceback.
* Save file grows indefinitely (one line per topic).  Maybe it should prune sufficiently old topics.
* Fails if savefile does not exist on first run.  The workaround is to 'touch' it first.
* It may not handle HTML entities correctly e.g. angle brackets in text get down-converted.  So code listings may get messed up.
