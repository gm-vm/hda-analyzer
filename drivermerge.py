#!/usr/bin/python

import config
from sys import exit, stdin, stderr, stdout
from os import popen, mkdir, system, chdir, getcwd, remove, listdir
from os.path import isdir, exists, split
from shutil import rmtree
from utils import git_popen, git_system, git_repo, is_alsa_file, to_alsa_file2, \
                  tmpfile, tmpdir, diff_compare2, to_kernel_file, \
                  git_read_commits, raw_subject
import re

def error(lines, msg, *args):
    for line in lines:
      stderr.write('===> %s' % line)
    stderr.write('ERROR: ' + msg % args)

def check_email(lines, fullemail, commit = False):
    #print('E-mail: "%s"' % fullemail)
    name, email = fullemail.split('<')
    name = name.strip()
    email = email.strip()
    if not email.endswith('>'):
        error(lines, 'E-mail address "%s" is not valid...\n' % (line))
        return False
    email = email[:-1]
    if email.find('@') <= 0 or len(name) < 5 or fullemail.find('root@') >= 0:
        error(lines, 'E-mail address "%s" is not valid...\n' % (line))
        return False
    if not commit:
        return True
    return True

def analyze_diff(fp, full=False, filter_git=False,
                 filecheck=is_alsa_file, fileconv=to_alsa_file2):

    def afile(file, prefix):
        if file.startswith('/dev/'):
            return file
        return prefix + file

    def hdr(rlines, addfiles, rmfiles, afile1, afile2):
      rlines.append('diff --git %s %s\n' % (afile(afile1, 'a/'), afile(afile2, 'b/')))
      rlines += hlines
      if hlines and (hlines[0].startswith('new file mode ') or \
         hlines[0].startswith('old mode ')):
        addfiles.append(afile2)
      elif hlines and hlines[0].startswith('deleted file mode '):
        rmfiles.append(afile1)

    rlines = []
    hlines = []
    ok = False
    header = False
    addfiles = []
    rmfiles = []
    start = True
    while 1:
        line = fp.readline()
        if not line:
            break
        if filter_git:
            if line.startswith('index ') and line.find('..') > 0:
                continue
            if line.startswith('new file mode '):
                continue
            if line.startswith('old mode '):
                continue
            if line.startswith('new mode '):
                continue
        if line.startswith('diff --git a/'):
            if header and ok:
                hdr(rlines, addfiles, rmfiles, afile1, afile2)
            start = False
            header = True
            hlines = []
            file1, file2 = line[11:].split(' ')
            file1 = file1.strip()
            file2 = file2.strip()
            ok1 = filecheck(file1[2:])
            ok2 = filecheck(file2[2:])
            ok = False
            if ok1 or ok2:
                afile1 = fileconv(file1, 'a/')
                afile2 = fileconv(file2, 'b/')
                ok = True
        elif ok and line.startswith('--- /dev/null'):
            afile1 = line[4:].strip()
        elif ok and line.startswith('--- a/'):
            afile1 = fileconv(line[6:].strip())
        elif ok and line.startswith('+++ b/'):
            afile2 = fileconv(line[6:].strip())
            rlines.append('diff --git %s %s\n' % (afile1, afile2))
            rlines += hlines
            rlines.append('--- %s\n' % afile(afile1, 'a/'))
            rlines.append('+++ %s\n' % afile(afile2, 'b/'))
            addfiles.append(afile2)
            header = False
        elif ok and line.startswith('+++ /dev/null'):
            rmfiles.append(afile1)
            rlines.append('diff --git %s %s\n' % (afile1, '/dev/null'))
            rlines += hlines
            rlines.append('--- %s\n' % afile(afile1, 'a/'))
            rlines.append('+++ /dev/null\n')
            header = False
        elif header:
            hlines.append(line)
        elif ok or (full and start):
            rlines.append(line)
    fp.close()
    if header and ok:
        hdr(rlines, addfiles, rmfiles, afile1, afile2)
    return rlines, addfiles, rmfiles

def commit_is_merged(commit, driver_commits):
    lines = commit['comment'].splitlines()
    subj = raw_subject(lines[0])
    for commit2 in driver_commits:
      lines2 = commit2['comment'].splitlines()
      if subj == raw_subject(lines2[0]):
        return True
    return False

def commit_is_merged_diff(driver_repo, kernel_repo, commit):
    ok = True
    for f in commit['files']:
        if not is_alsa_file(f):
            continue
        src = git_repo(driver_repo) + '/' + to_alsa_file2(f)
        dst = git_repo(kernel_repo) + '/' + f
        lines = popen("diff -uN %s %s 2> /dev/null" % (src, dst)).readlines()
        if lines:
            ok = False
            break
    return ok

def try_to_merge(driver_repo, driver_branch, src_repo, commit,
                 filecheck=is_alsa_file, fileconv=to_alsa_file2,
                 do_checkout=True):
    comment = commit['comment'].splitlines()
    ref = commit['ref']

    print 'Merging %s %s' % (ref[:7], comment[0])

    #fp = git_popen(src_repo, "diff --binary %s~1..%s" % (ref, ref))
    root = ''
    if 'root_flag' in commit and commit['root_flag']:
      root = '--root '
    fp = git_popen(src_repo, "diff-tree -p --binary %s%s" % (root, ref))
    rlines, addfiles, rmfiles = analyze_diff(fp, filecheck=filecheck, fileconv=fileconv)
    fp.close()

    patchfile = tmpfile('alsa-merge-patch')
    fp = open(patchfile, 'w+')
    fp.write(''.join(rlines))
    fp.close()

    commentfile = tmpfile('alsa-merge-comment')
    fp = open(commentfile, 'w+')
    fp.write(''.join(commit['comment']))
    fp.close()

    elems = re.compile('(.*?)\s+<(.*)>').match(commit['Author'])
    exports = 'export GIT_AUTHOR_NAME="%s" ; ' % elems.group(1)
    exports += 'export GIT_AUTHOR_EMAIL="%s" ; ' % elems.group(2)
    exports += 'export GIT_AUTHOR_DATE="%s" ; ' % commit['AuthorDate']
    elems = re.compile('(.*?)\s+<(.*)>').match(commit['Commit'])
    exports += 'export GIT_COMMITER_NAME="%s" ; ' % elems.group(1)
    exports += 'export GIT_COMMITER_EMAIL="%s" ; ' % elems.group(2)
    exports += 'export GIT_COMMITER_DATE="%s" ; ' % commit['CommitDate']
    exports += 'export GIT_COMMITTER_NAME="%s" ; ' % elems.group(1)
    exports += 'export GIT_COMMITTER_EMAIL="%s" ; ' % elems.group(2)
    exports += 'export GIT_COMMITTER_DATE="%s"' % commit['CommitDate']

    curdir = getcwd()
    if do_checkout and git_system(driver_repo, "checkout -q %s" % driver_branch):
        raise ValueError, 'git checkout'

    chdir(git_repo(driver_repo))
    lines = popen("LANG=C patch -f -p 1 --dry-run --reject-file=%s < %s" % (tmpfile("rejects"), patchfile)).readlines()
    print ''.join(lines)
    failed = fuzz = succeed = 0
    for line in lines:
      if line.find('FAILED') >= 0:
        failed += 1
      if line.find('succeed') >= 0:
        if line.find('fuzz') >= 0:
          fuzz += 1
        else:
          succeed += 1
    if failed:
   	print 'Merge skipped %s %s (%s failed)' % (ref[:7], comment[0], failed)
        chdir(curdir)
        if do_checkout and \
           ref[:7] in ['bdb527e', 'fc5b15f', '82b1d73', \
                       '02a237b', 'ef8d60f', 'c0fa6c8', \
                       '1605282', '3946860', 'd70f363', \
                       '6539799', '152a3a7', '79980d9']:
          print '  It is probably OK...'
          return False
        raise ValueError
        return False
    if git_system(driver_repo, "apply --check --binary --allow-binary-replacement %s" % patchfile):
   	print 'Merge skipped %s %s (apply check)' % (ref[:7], comment[0])
        chdir(curdir)
        if not do_checkout:
          raise ValueError
        return False
    if git_system(driver_repo, "apply --binary --allow-binary-replacement %s" % patchfile):
        chdir(curdir)
        raise ValueError, 'git apply'
    if addfiles and git_system(driver_repo, "add %s" % ' '.join(addfiles)):
        chdir(curdir)
        raise ValueError, 'git add'
    if rmfiles and git_system(driver_repo, "rm %s" % ' '.join(rmfiles)):
        chdir(curdir)
        raise ValueError, 'git rm'
    if git_system(driver_repo, "commit -F %s" % commentfile, exports=exports):
        chdir(curdir)
        raise ValueError, 'git commit'
    chdir(curdir)

    print 'Merge complete %s %s (%s fuzz)' % (ref[:7], comment[0], fuzz)
    return True

def try_to_merge_hard(driver_repo, driver_branch, kernel_repo, kernel_branch, commit):
    ref = commit['ref']
    fp = git_popen(kernel_repo, "diff %s~1..%s" % (ref, ref))
    rlines, addfiles, rmfiles = analyze_diff(fp)
    fp.close()
    patchfile = tmpfile('alsa-kmirror-patch')
    fp = open(patchfile, 'w+')
    fp.write(''.join(rlines))
    fp.close()
    curdir = getcwd()
    chdir(git_repo(driver_repo))
    lines = git_popen(driver_repo, "apply -v --check %s 2>&1" % patchfile).readlines()
    patch = plines = None
    for line in lines:
        if line.startswith('Checking patch '):
            patch = line[15:-4]
            plines = None
        elif line == 'error: while searching for:\n':
            plines = []
        elif line.startswith('error: '):
            if patch and plines is not None:
                break
            patch = plines = None
        else:
            if plines is not None:
                plines.append(line)
    if not patch and not plines:
        return False
    chdir(git_repo(kernel_repo))
    lines = git_popen(kernel_repo, "annotate %s %s" % (to_kernel_file(patch), ref)).readlines()
    start = end = None
    idx = -1
    missing = plines[:]
    missingrefs = []
    for line in lines:
        idx += 1
        pos = line.find('\t')
        if pos < 0:
            continue
        hash = line[:pos]
        pos = line.find(')')
        if pos < 0:
            continue
        code = line[pos+1:]
        if code in missing:
            missing.remove(code)
            if start is None:
                start = idx
            end = idx
        elif start is not None:
            missing.append(code)
    if start is None:
        return False
    for idx in range(max(0, start-1), min(len(lines), end+2)):
        line = lines[idx]
        pos = line.find('\t')
        if pos < 0:
            continue
        hash = line[:pos]
        if hash == ref[:8]:
            continue
        pos = line.find(')')
        if pos < 0:
            continue
        code = line[pos+1:]
        for m in missing:
            if code == m:
                if not hash in missingrefs:
                    missingrefs.append(hash)
    chdir(curdir)
    ok = False
    for mref in missingrefs:
        commits = git_read_commits(kernel_repo, mref + "~1", mref)
        if commits and try_to_merge(driver_repo, driver_branch, kernel_repo, commits[0]):
            ok = True
    return ok

def compare_trees(driver_repo, driver_branch, kernel_repo, kernel_branch):
    print 'comparing %s/%s (old) and %s/%s (new) repos' % (driver_repo, driver_branch, kernel_repo, kernel_branch)
    worktree = tmpdir('alsa-driver-repo')
    worktreek = tmpdir('alsa-kernel-repo')
    rmtree(worktree, ignore_errors=True)
    rmtree(worktreek, ignore_errors=True)
    mkdir(worktree)
    mkdir(worktreek)
    if git_system(driver_repo, "archive --format=tar %s mirror | tar xf - -C %s" % (driver_branch, worktree)):
        raise ValueError, 'git export (alsa-driver)'
    if git_system(kernel_repo, "archive --format=tar %s sound include/sound Documentation/DocBook Documentation/sound/alsa | tar xf - -C %s" % (kernel_branch, worktreek)):
        raise ValueError, 'git export (kernel)'
    git_system(driver_repo, "checkout %s" % driver_branch)
    git_system(kernel_repo, "checkout %s" % kernel_branch)
    curdir = getcwd()
    chdir(tmpdir())
    for f in listdir("alsa-kernel-repo/Documentation/DocBook"):
      if not f in ['.', '..', 'alsa-driver-api.tmpl']:
        x = "alsa-kernel-repo/Documentation/DocBook/" + f
        if isdir(x):
          rmtree(x)
        else:
          remove(x)
    remove("alsa-driver-repo/mirror/.gitignore")
    rmtree("alsa-driver-repo/mirror/scripts")
    rmtree("alsa-driver-repo/mirror/sound/oss")
    rmtree("alsa-kernel-repo/sound/oss")
    if 0:
      for i in ['.git-ok-commits', '.hgignore', '.hgtags', '.gitignore', 'kernel', 'scripts',
                'oss', 'usb/usbmixer.h', 'usb/usbmixer_maps.c']:
          if isdir("alsa-kmirror-repo/%s" % i):
              rmtree("alsa-kmirror-repo/%s" % i)
          elif exists("alsa-kmirror-repo/%s" % i):
              remove("alsa-kmirror-repo/%s" % i)
      for i in ['oss', 'pci/ac97/ak4531_codec.c', 'isa/sb/sb16_csp_codecs.h',
                'pci/korg1212/korg1212-firmware.h', 'pci/ymfpci/ymfpci_image.h',
                'pci/hda/hda_patch.h',
                'isa/ad1848/ad1848_lib.c', 'isa/cs423x/cs4231_lib.c', 'isa/cs423x/cs4232.c',
                'include/cs4231.h', 'soc/at91/eti_b1_wm8731.c',
                'aoa/codecs/snd-aoa-codec-onyx.c', 'aoa/codecs/snd-aoa-codec-onyx.h',
                'aoa/codecs/snd-aoa-codec-tas-basstreble.h', 'aoa/codecs/snd-aoa-codec-tas-gain-table.h',
                'aoa/codecs/snd-aoa-codec-tas.c', 'sound/aoa/codecs/snd-aoa-codec-tas.h',
                'aoa/codecs/snd-aoa-codec-toonie.c', 'aoa/core/snd-aoa-alsa.c',
                'aoa/core/snd-aoa-alsa.h', 'aoa/core/snd-aoa-core.c',
                'aoa/core/snd-aoa-gpio-feature.c', 'aoa/core/snd-aoa-gpio-pmf.c',
                'aoa/fabrics/snd-aoa-fabric-layout.c', 'aoa/soundbus/i2sbus/i2sbus-control.c',
                'aoa/soundbus/i2sbus/i2sbus-core.c', 'aoa/soundbus/i2sbus/i2sbus-interface.h',
                'aoa/soundbus/i2sbus/i2sbus-pcm.c', 'aoa/codecs/snd-aoa-codec-tas.h',
                'include/uda1341.h', 'i2c/l3/', 'arm/sa11xx-uda1341.c',
                'soc/at91/', 'soc/at32/', 'soc/s3c24xx/',
                'usb/caiaq/caiaq-audio.c', 'usb/caiaq/caiaq-audio.h',
                'usb/caiaq/caiaq-control.c', 'usb/caiaq/caiaq-control.h',
                'usb/caiaq/caiaq-device.c', 'usb/caiaq/caiaq-device.h',
                'usb/caiaq/caiaq-input.c', 'usb/caiaq/caiaq-input.h',
                'usb/caiaq/caiaq-midi.c', 'usb/caiaq/caiaq-midi.h',
                'usb/usbmixer.h',
                'usb/usbmixer_maps.c',
                'isa/wavefront/yss225.c'
                ]:
          if isdir("alsa-kernel-repo/%s" % i):
              rmtree("alsa-kernel-repo/%s" % i)
          elif exists("alsa-kernel-repo/%s" % i):
              remove("alsa-kernel-repo/%s" % i)
    fp = popen("diff -ruNp alsa-driver-repo/mirror alsa-kernel-repo")
    notempty = False
    while 1:
        line = fp.readline()
        if not line:
            break
        stdout.write(line)
        notempty = True
    if notempty:
        stdout.write('\n')
    rmtree(worktree, ignore_errors=True)
    rmtree(worktreek, ignore_errors=True)
    if notempty:
        stderr.write('repositories does not match, please, fix it\n')
        return False
    return True

def commit_is_merged_hard(kernel_repo, commit, driver_repo, driver_commits):
    ref = commit['ref']
    fp = git_popen(kernel_repo, "diff %s~1..%s" % (ref, ref))
    rlines, addfiles, rmfiles = analyze_diff(fp)
    fp.close()
    files = addfiles + rmfiles
    for dc in driver_commits:
      ok = True
      for f in files:
        if not f in dc['files']:
          ok = False
          break
      if ok:
        ref1 = dc['ref']
        curdir = getcwd()
        chdir(git_repo(driver_repo))
        fp = git_popen(driver_repo, "diff %s~1..%s %s" % (ref1, ref1, ' '.join(files)))
        chdir(curdir)
        lines = fp.readlines()
        fp.close()
        #print 'Candidate', dc['ref'][:7], dc['comment'].splitlines()[0]
        #if ref1[:7] == 'd26326d':
        #  open("/dev/shm/aaa.1", "w+").write(''.join(lines))
        #  open("/dev/shm/aaa.2", "w+").write(''.join(rlines))
        if diff_compare2(lines, rlines):
          return dc
    return None

def driver_merge(driver_repo, driver_branch, kernel_repo, kernel_branch):
    if git_system(driver_repo, "checkout -q %s" % driver_branch):
        raise ValueError, 'git checkout'
    if git_system(kernel_repo, "checkout -q %s" % kernel_branch):
        raise ValueError, 'git checkout'
    driver_commits = git_read_commits(driver_repo, config.GIT_DRIVER_MERGE, driver_branch)
    kernel_commits = git_read_commits(kernel_repo, config.GIT_KERNEL_MERGE, kernel_branch, kernel_tree=True)
    #kernel_commits = git_read_commits(kernel_repo, 'd80852223ecabd1ab433a9c71436d81b697ef1fc~1', 'd80852223ecabd1ab433a9c71436d81b697ef1fc', kernel_tree=True)
    if not driver_commits or not kernel_commits:
      print 'Nothing to do'
      return
    print 'Analyzing merged commits:'
    remove = []
    for commit in reversed(kernel_commits):
        if commit_is_merged(commit, driver_commits):
            remove.append(commit)
        elif commit_is_merged_diff(driver_repo, kernel_repo, commit):
            remove.append(commit)
    print '  %s commits are already merged' % len(remove)
    ok = []
    for commit in reversed(kernel_commits):
      if commit in remove:
        continue
      if try_to_merge(driver_repo, driver_branch, kernel_repo, commit):
        ok.append(commit)
    print '*** %s merged %s already merged %s remaining' % (len(ok), len(remove), len(kernel_commits)-len(remove)-len(ok))
    failed = []
    for commit in reversed(kernel_commits):
      if commit in remove or commit in ok:
        continue
      if commit_is_merged_diff(driver_repo, kernel_repo, commit):
        print 'NOCHANGE: %s %s' % (commit['ref'][:7], commit['comment'].splitlines()[0])
        continue
      res = commit_is_merged_hard(kernel_repo, commit, driver_repo, driver_commits)
      if res:
        print '  HARD  : %s %s' % (commit['ref'][:7], commit['comment'].splitlines()[0])
        print '        : in commit %s %s' % (res['ref'][:7], res['comment'].splitlines()[0])
        continue
      else:
        failed.append(commit)
      #else:
      #  if not try_to_merge_hard(driver_repo, driver_branch, kernel_repo, kernel_branch, commit):
      #    failed.append(commit)
      #  else:
      #    print '  HARDM : %s %s' % (commit['ref'][:7], commit['comment'].splitlines()[0])
    if failed:
      print '  *********'
    for commit in failed:
      print '  FAILED: %s %s' % (commit['ref'][:7], commit['comment'].splitlines()[0])

if __name__ == '__main__':
    driver_merge('alsa-kmirror', 'master', 'alsa-kernel', 'tiwai-fornext')
    #compare_trees('alsa-kmirror', 'master', 'alsa-kernel', 'tiwai-fornext')
    #print try_to_merge_hard('alsa-kmirror', 'master',
    #                        'alsa-kernel', 'tiwai-fornext',
    #          git_read_commits('alsa-kernel', 
    #                       '5409fb4e327a84972483047ecf4fb41f279453e2~1',
    #                       '5409fb4e327a84972483047ecf4fb41f279453e2')[0])
