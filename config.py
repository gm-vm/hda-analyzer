#! /usr/bin/python
# -*- Python -*-

import os

ROOT = os.path.abspath(os.getcwd())
USER = os.getenv('USER')
VERBOSE = False
GERRORS = 0
TMPDIR = '/dev/shm/alsatool'
GIT_KERNEL_MERGE = 'v2.6.30'
GIT_DRIVER_MERGE = 'v1.0.19'
REPOSITORIES = [
        'alsa', 'alsa-driver', 'alsa-kmirror', 'alsa-lib', 'alsa-utils',
        'alsa-tools', 'alsa-firmware', 'alsa-oss', 'alsa-plugins',
        'alsa-python'
]        
ALSA_FILES = (
	'Documentation/sound/alsa/',
	'sound/',
	'include/sound/'
)
NOT_ALSA_FILES = (
	'sound/oss/',
)
ALSA_TRANSLATE = {
        'Documentation/DocBook/alsa-driver-api.tmpl': 'Documentation/DocBook/alsa-driver-api.tmpl',
        'Documentation/sound/alsa/':        'Documentation/',
        'include/sound/':                   'include/',
        'sound/':                           ''
}
ALSA_RTRANSLATE = {}
for i in ALSA_TRANSLATE:
  ALSA_RTRANSLATE[ALSA_TRANSLATE[i]] = i
