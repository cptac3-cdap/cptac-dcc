
import sys, os, os.path, shutil, encodings
import zipfile, glob
from optparse import OptionParser

parser = OptionParser()
parser.add_option('-r','--raw',type='string',default='wiff',dest='raw',
                  help='RAW file extension of files to unpack. Default: wiff.')
parser.add_option('-R','--remove',action='store_true',dest='remove',
                  help='Remove ZIP files. Default: False.')
parser.add_option('-d','--outdir',type='string',default='.',dest='outdir',
                  help='Write unpacked files to a specific directory. Default: Current working directory.')
parser.add_option('-v','--verbose',dest="verbose",action='count',default=0,
                  help='Verbose output, repeat for more verbosity. Default: Quiet.')
opts,args = parser.parse_args()

if len(args) < 1:
    userdirs = [ '.' ]
else:
    userdirs = []
    for a in args:
        userdirs.extend(glob.glob(a))

for d in userdirs:
  for root, dirs, files in os.walk(d):
    for f in files:
      if not f.endswith(".%s.zip"%(opts.raw,)):
        continue
      if opts.verbose > 0:
        print("Exploding zip file:",os.path.join(root,f),file=sys.stderr)
      zf = zipfile.ZipFile(os.path.join(root,f), mode='r')
      if opts.verbose > 1:
          for f1 in zf.namelist():
              print("Writing file:",os.path.join(opts.outdir,root,f,f1),file=sys.stderr)
      if not os.path.isdir(os.path.join(opts.outdir,root)):
          os.makedirs(os.path.join(opts.outdir,root))
      zf.extractall(os.path.join(opts.outdir,root))
      zf.close()
      if opts.remove:
          try:
              if opts.verbose > 1:
                  print("Removing zip file:",os.path.join(root,f),file=sys.stderr)
              os.unlink(os.path.join(root,f))
          except OSError:
              pass
