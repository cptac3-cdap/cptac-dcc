#!/bin/env python

from distutils.core import setup
import py2exe, sys, os, shutil, os.path

def rmminusrf(top):
    if not os.path.exists(top):
	return
    for root, dirs, files in os.walk(top, topdown=False):
        for name in files:
            os.remove(os.path.join(root, name))
        for name in dirs:
            os.rmdir(os.path.join(root, name))
    os.rmdir(top)

f = sys.argv[1]
assert(f.endswith('.py'))
base = f[:-3]

rmminusrf(base)

l = []
l.append('setup.py')
l.append('py2exe')
# l.append('-c')
l.append('-d')
l.append(base)
sys.argv = l
# print l
setup(console = [f],
      options = {
        "py2exe": {
            "dll_excludes": ["MSVCP90.dll",
			     "API-MS-Win-Core-LocalRegistry-L1-1-0.dll",
			     "API-MS-Win-Core-ProcessThreads-L1-1-0.dll",
			     "API-MS-Win-Security-Base-L1-1-0.dll",
			     "POWRPROF.dll"]
        }
    },
)

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
	if d == '.svn':
	    rmminusrf(os.path.join(root,d))
	    # os.rmdir(os.path.join(root,d))
	else:
	   dirs1.append(d)
    dirs = dirs1

if os.path.exists("%s.iss"%(base,)):
    os.system(r'call "c:\Program Files\Inno Setup 6\ISCC.exe" %s.iss'%(base,))
if os.path.exists('%s.zip'%(base,)):
    os.remove('%s.zip'%(base,))
os.system("zip -r %s.zip %s"%(base,base))
