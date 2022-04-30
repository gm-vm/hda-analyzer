#!/usr/bin/env python3

URL="http://git.alsa-project.org/?p=alsa.git;a=blob_plain;f=hda-analyzer/"
FILES=["hda_analyzer.py", "hda_guilib.py", "hda_codec.py", "hda_proc.py",
       "hda_graph.py", "hda_mixer.py"]

try:
  import gi
except:
  print("Please, install python3-gi package")

import os
import sys
import urllib.request

if os.path.exists("/dev/shm"):
  TMPDIR="/dev/shm"
else:
  TMPDIR="/tmp"
TMPDIR += "/hda-analyzer"
print("Using temporary directory: %s" % TMPDIR)
print("You may remove this directory when finished or if you like to")
print("download the most recent copy of hda-analyzer tool.")
if not os.path.exists(TMPDIR):
  os.mkdir(TMPDIR)
for f in FILES:
  dest = TMPDIR + '/' + f
  if os.path.exists(dest):
    print("File cached " + dest)
    continue
  print("Downloading file %s" % f)
  urllib.request.urlretrieve(URL + f, dest)
print("Downloaded all files, executing %s" % FILES[0])
os.system("/usr/bin/env python3 %s" % TMPDIR + '/' + FILES[0] + ' ' + ' '.join(sys.argv[1:]))
