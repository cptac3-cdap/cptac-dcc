#!/bin/env python

import sys, os, shutil, os.path, zipfile
from py2exe import freeze

def rmminusrf(top):
    if not os.path.exists(top):
        return
    for root, dirs, files in os.walk(top, topdown=False):
        for name in files:
            os.remove(os.path.join(root, name))
        for name in dirs:
            os.rmdir(os.path.join(root, name))
    os.rmdir(top)

base = sys.argv[1]
progs = sys.argv[2:]
rmminusrf(base)

freeze(console = progs, 
       options = dict(
         dist_dir = base, 
         verbose= 4,
       ))

datadir = "%s.data"%(base,)
if os.path.isdir(datadir):
  for f in os.listdir(datadir):
    if f.startswith('.svn'):
        continue
    if os.path.isdir(os.path.join(datadir,f)):
        shutil.copytree(os.path.join(datadir,f),os.path.join(base,f))
    else:
        shutil.copyfile(os.path.join(datadir,f),os.path.join(base,f))

for root, dirs, files in os.walk(base):
  dirs1 = []
  for d in dirs:
    if d in ('.svn','.git'):
        rmminusrf(os.path.join(root,d))
        # os.rmdir(os.path.join(root,d))
    else:
       dirs1.append(d)
  dirs = dirs1

if os.path.exists("%s.iss"%(base,)):
    os.system(r'call "c:\Program Files\Inno Setup 6\ISCC.exe" %s.iss'%(base,))
if os.path.exists('%s.zip'%(base,)):
    os.remove('%s.zip'%(base,))
# os.system("zip -r %s.zip %s"%(base,base))
shutil.make_archive(base,"zip",base)