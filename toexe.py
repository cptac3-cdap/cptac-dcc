#!/bin/env python

import sys, os, shutil, os.path, shutil
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

if not os.path.isdir("build"):
    os.makedirs("build")

from version import VERSION
VER = VERSION.split()[2]
base = sys.argv[1]
fullbase0 = "build%s%s-%s"%(os.sep,base,VER)
fullbase1 = "build%s%s-%s%s%s"%(os.sep,base,VER,os.sep,base)
if not os.path.isdir(fullbase0):
    os.makedirs(fullbase0)

progs = sys.argv[2:]
rmminusrf(fullbase1)

freeze(console = progs, 
       options = dict(
         dist_dir = fullbase1, 
         verbose= 4,
       ))

datadir = "%s.data"%(base,)
if os.path.isdir(datadir):
  for f in os.listdir(datadir):
    if f.startswith('.svn'):
        continue
    if os.path.isdir(os.path.join(datadir,f)):
        shutil.copytree(os.path.join(datadir,f),os.path.join(fullbase1,f))
    else:
        shutil.copyfile(os.path.join(datadir,f),os.path.join(fullbase1,f))

for root, dirs, files in os.walk(fullbase1):
  dirs1 = []
  for d in dirs:
    if d in ('.svn','.git'):
        rmminusrf(os.path.join(root,d))
        # os.rmdir(os.path.join(root,d))
    else:
       dirs1.append(d)
  dirs = dirs1


if not os.path.isdir("dist"):
    os.makedirs("dist")

if os.path.exists("%s.iss"%(base,)):
    innosetupfile = "dist%s%s-%s.win.exe"%(os.sep,base,VER)
    if os.path.exists(innosetupfile):
        os.unlink(innosetupfile)
    if os.path.exists('%s.exe'%(base,)):
        os.unlink('%s.exe'%(base,))
    os.system(r'call "c:\Program Files (x86)\Inno Setup 6\ISCC.exe" /DBASE=%s %s.iss'%(fullbase1,base,))
    shutil.move("%s.exe"%(base,),innosetupfile)
zipfile = "dist%s%s-%s.win.zip"%(os.sep,base,VER)
if os.path.exists(zipfile):
    os.unlink(zipfile)
shutil.make_archive(zipfile[:-4],"zip",fullbase0)