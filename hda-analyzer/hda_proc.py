#!/usr/bin/env python

from dircache import listdir

PROC_DIR = '/proc/asound'

CODEC_TREE = {}

def read_verbs2(card, codec):
  CODEC_TREE[card][codec] = {}
  info = {}
  fp = open("%s/card%s/codec#%s" % (PROC_DIR, card, codec))
  src = fp.read(1024*1024)
  CODEC_TREE[card][codec]['src'] = src
  node = -1
  for line in src.split('\n'):
    if line.startswith('Node '):
      if node >= 0:
        CODEC_TREE[card][codec][node] = data
      data = line + '\n'
      a = line.split(' ')
      node = a[1].startswith('0x') and int(a[1][2:], 16) or int(a[1])
    elif node >= 0:
      data += line + '\n'
  if node >= 0:
    CODEC_TREE[card][codec][node] = data

def read_verbs1(card):
  CODEC_TREE[card] = {}
  for l in listdir('%s/card%s' % (PROC_DIR, card)):
    if l.startswith('codec#') and l[6] >= '0' and l[6] <= '9':
      read_verbs2(card, int(l[6:]))

def read_verbs():
  for l in listdir(PROC_DIR):
    if l.startswith('card') and l[4] >= '0' and l[4] <= '9':
      read_verbs1(int(l[4:]))
