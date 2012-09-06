#! /usr/bin/python
# -*- Python -*-

import os
import sys
import config

def package(repo):
    if repo == 'alsa-python':
        return 'pyalsa'
    return repo

def tmpdir(extra=''):
    if not os.path.exists(config.TMPDIR):
        os.mkdir(config.TMPDIR)
    if extra and extra[0] != '/':
        extra = '/' + extra
    if extra and not os.path.exists(config.TMPDIR + extra):
	os.mkdir(config.TMPDIR + extra)
    return os.path.abspath(config.TMPDIR + extra)

def tmpfile(file, extra=''):
    return tmpdir(extra) + '/' + file

def eprint(msg):
    sys.stderr.write(msg + '\n')

def is_alsa_file(file):
    for i in config.NOT_ALSA_FILES:
        if file.startswith(i):
            return False
    for i in config.ALSA_FILES:
        if file.startswith(i):
            return True
    return False

def to_alsa_file(gitfile, prefix=''):
    if gitfile == '/dev/null':
        return '/dev/null'
    if prefix and gitfile.startswith(prefix):
        gitfile = gitfile[len(prefix):]
    for t in config.ALSA_TRANSLATE:
        if gitfile.startswith(t[0]):
            return prefix + t[1] + gitfile[len(t[0]):]
    raise ValueError, repr(gitfile)

def to_alsa_file2(gitfile, prefix=''):
    return prefix + 'mirror/' + gitfile

def to_kernel_file(gitfile, prefix=''):
    if gitfile == '/dev/null':
        return '/dev/null'
    if prefix and gitfile.startswith(prefix):
        gitfile = gitfile[len(prefix):]
    for t in config.ALSA_RTRANSLATE:
        if gitfile.startswith(t[0]):
            return prefix + t[1] + gitfile[len(t[0]):]
    raise ValueError, repr(gitfile)

def git_repo(repo):
    if repo == '.':
        return os.path.abspath(repo)
    if repo[0] != '/':
        repo = config.ROOT + '/' + repo
    return os.path.abspath(repo)

def git(repo):
    repo = git_repo(repo)
    return "LANG=C git --work-tree=%s --git-dir=%s" % (repo, repo + '/.git')

def git_popen(repo, cmd):
    if config.GIT_DEBUG:
        print "%s %s" % (git(repo), cmd)
    return os.popen("%s %s" % (git(repo), cmd))
    
def git_system(repo, cmd, exports=None):
    if exports is None:
        exports = ''
    else:
        exports += ' ; '
    if config.GIT_DEBUG:
        print "%s%s %s" % (exports, git(repo), cmd)
    return os.system("%s%s %s" % (exports, git(repo), cmd))

def git_read_commits(repo, old, head, kernel_tree=False, reverse=False):

    def check_files():
      commit['comment'] = commit['comment'].strip()
      if not kernel_tree:
        return True
      for file in commit['files']:
        if is_alsa_file(file):
          return True
      return False

    reverse = reverse and " --reverse" or ""
    curdir = os.getcwd()
    os.chdir(git_repo(repo))
    if old.startswith('__'):
      a, b = old[2:], head
      if a != b:
          a += ' ' + b
      fp = git_popen(repo, "log --name-only --pretty=fuller --date=iso%s %s" % (reverse, a))
    else:
      a, b = old, head
      if a != b:
          a += '..' + b
      print 'Analyzing %s %s:' % (repo, a)
      fp = git_popen(repo, "log --name-only --pretty=fuller --date=iso%s %s" % (reverse, a))
    res = []
    commit = None
    while 1:
        line = fp.readline()
        if not line:
            break
        if line.startswith('commit '):
            if commit is not None and check_files():
                res.append(commit)
            commit = {'comment':'', 'files':[]}
            commit['ref'] = line[7:].strip()
        elif line.startswith('Author:') or line.startswith('AuthorDate:') or \
             line.startswith('Commit:') or line.startswith('CommitDate:') or \
             line.startswith('Merge:'):
            line = line.replace('Signed-off-by:', '')
            a = line.split(': ')
            commit[a[0].strip()] = a[-1].strip()
        elif line.startswith('    '):
            commit['comment'] += line[4:].strip() + '\n'
        else:
            line = line.strip()
            if line:
              commit['files'].append(line)
    if commit is not None and check_files():
        res.append(commit)
    fp.close()
    if not old.startswith('__'):
        print '  %s commits read' % len(res)
    os.chdir(curdir)
    return res

def diff_compare2(diff1, diff2):
    if len(diff1) != len(diff2):
        return False
    for idx in range(0, len(diff1)-1):
        if diff1[idx].startswith('index ') and diff2[idx].startswith('index '):
            continue
	elif diff1[idx].startswith('@@ ') and diff2[idx].startswith('@@ '):
	    a = diff1[idx].split(' ')
	    b = diff2[idx].split(' ')
	    a1 = a[1].split(',')
	    a2 = a[2].split(',')
	    b1 = b[1].split(',')
	    b2 = b[2].split(',')
	    if len(a1) < 2:
		a1.append('XXX')
            if len(b1) < 2:
		b1.append('XXX')
            if a1[1] != b1[1] or a2[1] != b2[1]:
		return False
            elif diff1[idx] != diff2[idx]:
		return False
    return True

def diff_compare(repo1, commit1, repo2, commit2):
    diff1 = git_popen(repo1, "diff %s~1..%s" % (commit1, commit1)).readlines()
    diff2 = git_popen(repo2, "diff %s~1..%s" % (commit2, commit2)).readlines()
    return diff_compare2(diff1, diff2)

def raw_subject(str):
    strings = ['ALSA:', 'SOUND:', 'ASOC:', '[ALSA]', '[SOUND]', '[ASOC]']
    up = str.upper() 
    for s in strings:
        if up.startswith(s):
            return raw_subject(str[len(s):].strip())
    return str
