#!/usr/bin/env python

URL="http://git.alsa-project.org/?p=alsa.git;a=blob_plain;f=hda-analyzer/"
FILES=["hda_analyzer.py", "hda_codec.py"]

try:
  import gobject
  import gtk
  import pango
except:
  print "Please, install pygtk2 package"

import os
from urllib import splithost
from httplib import HTTP

if os.path.exists("/dev/shm"):
  TMPDIR="/dev/shm"
else:
  TMPDIR="/tmp"
TMPDIR += "/hda-analyzer"
print "Creating temporary directory: %s" % TMPDIR
if not os.path.exists(TMPDIR):
  os.mkdir(TMPDIR)
for f in FILES:
  print "Downloading file %s" % f
  host, selector = splithost(URL[5:])
  h = HTTP(host)
  h.putrequest('GET', URL + f)
  h.endheaders()
  h.getreply()
  contents = h.getfile().read(2*1024*1024)
  h.close()
  open(TMPDIR + '/' + f, "w+").write(contents)
print "Downloaded all files, executing %s" % FILES[0]
os.system("python %s" % TMPDIR + '/' + FILES[0])
