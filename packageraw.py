#!/usr/bin/env python3

import sys, os, os.path, subprocess, shutil, encodings
import zipfile, glob
from optparse import OptionParser

parser = OptionParser()
parser.add_option('-r','--raw',type='string',default='wiff',dest='raw',
                  help='RAW file extension of files to package. Default: wiff.')
# parser.add_option('-x','--xml',type='string',default='mzML',dest='extn',
#                 help='XML format to convert to. Default: mzML.')
parser.add_option('-R','--remove',action='store_true',dest='remove',
                  help='Remove raw files. Default: False.')
parser.add_option('-d','--outdir',type='string',default='.',dest='outdir',
                  help='Write packaged files to a specific directory. Default: Current working directory.')
parser.add_option('-v','--verbose',dest="verbose",action='count',default=0,
                  help='Verbose output, repeat for more verbosity. Default: Quiet.')
opts,args = parser.parse_args()

if opts.outdir != ".":
    if not os.path.exists(opts.outdir):
        os.makedirs(opts.outdir)

if len(args) < 1:
    userdirs = [ '.' ]
else:
    userdirs = []
    for a in args:
        userdirs.extend(glob.glob(a))
    
for d in userdirs:
  for root, dirs, files in os.walk(d):
    for f in (files+dirs):
        try:
            b,e = f.rsplit('.',1)
        except ValueError:
            continue
        if e != opts.raw:
            continue
        allfs = []
        for f1 in (files+dirs):
            if f1.startswith(b+'.') and not f1.endswith('.zip'):
                allfs.append(f1)
        if len(allfs) <= 1 and not os.path.isdir(os.path.join(root,f)):
            continue
        if os.path.isdir(os.path.join(root,f)):
            dirs.remove(f)
        ff = os.path.join(opts.outdir,os.path.join(root,f))
        ff = os.path.realpath(ff)
        if not os.path.isdir(os.path.split(ff)[0]):
            os.makedirs(os.path.split(ff)[0])
        if ff.startswith(os.getcwd()+"/"):
            ff = ff[len(os.getcwd())+1:]
        if opts.verbose > 0:
            print("Creating zip file:",ff+'.zip',file=sys.stderr)
        zf = zipfile.ZipFile(ff+'.zip', mode='w', compression=zipfile.ZIP_DEFLATED)
        for f1 in allfs:
            # print(os.path.join(root,f1))
            if not os.path.isdir(os.path.join(root,f1)):
                if opts.verbose > 1:
                    print("Adding to zip file:",os.path.join(root,f1),file=sys.stderr)
                zf.write(os.path.join(root,f1))
            else:
                for root1,dirs1,files1 in os.walk(os.path.join(root,f1)):
                    for f11 in files1:
                        f111 = os.path.join(root1,f11)
                        if opts.verbose > 1:
                            print("Adding to zip file:",f111[len(root)+1:],file=sys.stderr)
                        zf.write(f111,arcname=f111[len(root)+1:])
        zf.close()
        # cmd = [zip_prog]+zip_args+[f+'.zip']+allfs
        # if opts.verbose:
        #     print(' '.join([s if ' ' not in s else '"'+s+'"' for s in cmd]))
        #     sys.stdout.flush()
        # subprocess.call(cmd,cwd=root,shell=('win' in sys.platform))
        if opts.remove:
            for f1 in allfs:
                if os.path.isdir(os.path.join(root,f1)):
                    if opts.verbose > 1:
                        print("Removing directory:",f1,file=sys.stderr)
                    shutil.rmtree(os.path.join(root,f1),ignore_errors=True)
                else:
                    try:
                        if opts.verbose > 1:
                            print("Removing file:",f1,file=sys.stderr)
                        os.unlink(os.path.join(root,f1))
                    except OSError:
                        pass
