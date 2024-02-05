#!/usr/bin/env python3

import sys, os, os.path, shutil, encodings
import zipfile, glob
from optparse import OptionParser

parser = OptionParser()
parser.add_option('-r','--raw',type='string',default='wiff',dest='raw',
                  help='RAW file extension of files to unpack. Default: wiff.')
parser.add_option('-R','--remove',action='store_true',dest='remove',
                  help='Remove ZIP files. Default: False.')
parser.add_option('-v','--verbose',dest="verbose",action='count',default=0,
                  help='Verbose output, repeat for more verbosity. Default: Quiet.')
opts,args = parser.parse_args()

curdir = os.path.abspath(os.getcwd())
for f in glob.glob('*.%s.zip'%(opts.raw,)):
    if opts.verbose > 0:
        print("Exploding zip file:",f,file=sys.stderr)
    zf = zipfile.ZipFile(f, mode='r')
    if opts.verbose > 1:
        for f1 in zf.namelist():
            print("Writing file:",f1,file=sys.stderr)
    zf.extractall()
    zf.close()
    if opts.remove:
        try:
            if opts.verbose > 1:
                print("Removing zip file:",f,file=sys.stderr)
            os.unlink(f)
        except OSError:
            pass
