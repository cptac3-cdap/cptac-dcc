#!/usr/bin/env python3

import sys, os, os.path, subprocess, shutil, encodings
import zipfile
from optparse import OptionParser

parser = OptionParser()
parser.add_option('-r','--raw',type='string',default='wiff',dest='raw',
                  help='RAW file extension of files to package. Default: wiff.')
# parser.add_option('-x','--xml',type='string',default='mzML',dest='extn',
#                 help='XML format to convert to. Default: mzML.')
parser.add_option('-R','--remove',action='store_true',dest='remove',
                  help='Remove raw files. Default: False.')
parser.add_option('-v','--verbose',dest="verbose",action='count',default=0,
                  help='Verbose output, repeat for more verbosity. Default: Quiet.')
opts,args = parser.parse_args()

curdir = os.path.abspath(os.getcwd())
for root, dirs, files in os.walk(curdir):
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
        if opts.verbose > 0:
            print("Creating zip file:",f+'.zip',file=sys.stderr)
        zf = zipfile.ZipFile(f+'.zip', mode='w', compression=zipfile.ZIP_DEFLATED)
        for f1 in allfs:
            if not os.path.isdir(f1):
                if opts.verbose > 1:
                    print("Adding to zip file:",f1,file=sys.stderr)
                zf.write(f1)
            else:
                for root1,dirs1,files1 in os.walk(f1):
                    for f11 in files1:
                        f111 = os.path.join(root1,f11)
                        if opts.verbose > 1:
                            print("Adding to zip file:",f111,file=sys.stderr)
                        zf.write(f111)
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
