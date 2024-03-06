#!/usr/bin/env python3

from __future__ import print_function

import sys, os.path, os, re, encodings
from operator import itemgetter
import time
try:
    from hashlib import md5
    from hashlib import sha1
except ImportError:
    from md5 import md5
    from sha import sha as sha1

from optparse import OptionParser
from version import VERSION

parser = OptionParser(version=VERSION,
                      usage="%prog [options] <dir> [ <dir1> ... ]")
parser.add_option('-F','--cksumformat',dest='cksumformat',type='choice',
                  metavar="FORMAT",default='DCC',choices=["DCC","VU","NIST"],
                  help="Format (and default checksum file name and location) of checksum file. One of DCC, VU, NIST. Default: DCC")
parser.add_option('-f','--cksumfile',dest='cksumfile',type='string',
                  metavar="FILENAME",default=None,
                  help="Explicit path for the checksum file. Overrides the checksum file location implied by the -F/--cksumformat option.")
parser.add_option('-c','--checkonly',dest="checkonly",action='store_true',
                  help='Check the checksum file only, do not create if missing.',default=False)
parser.add_option('-m','--match',dest='match',type='string',
                  metavar="REGEX",default=None,
                  help="Regular expression that filenames must match.")
parser.add_option('-V','--verify',dest='verify',default=False,action='store_true',
                  help="Check (Verify) only files from the checksum file.")
parser.add_option('-C','--common',dest='common',default=False,action='store_true',
                  help="Check only files in common between checksum file and directory.")
parser.add_option('-U','--update',dest='update',default=False,action='store_true',
                  help="Update the checksum file if all checksums don't match.")
parser.add_option('-v','--verbose',dest='verbose',default=False,action='store_true',
                  help="Print statistics for hash computation.")
parser.add_option('-q','--quiet',dest='quiet',default=0,action='count',
                  help="Print summary of cksum check only. If doubled, be silent for folders where all checksums match.")
opts,args = parser.parse_args()

def filelist(folder,ignorefiles=[]):
    # print folder,os.path.realpath(os.path.abspath(folder))
    for root, dirs, files in os.walk(folder):
        dirs.sort()
        for f in sorted(files):
            fullf = os.path.join(root,f)
            realf = os.path.realpath(os.path.abspath(fullf))
            # print f,fullf,realf
            if f.startswith('.'):
                continue
            if os.path.islink(fullf) and not os.path.exists(fullf):
                continue
            if os.path.islink(fullf) and realf.startswith(os.path.realpath(os.path.abspath(folder))+os.sep):
                continue
            if realf in ignorefiles:
                continue
            if f in ignorefiles:
                continue
            # print ">",fullf
            yield fullf

def roundbytes(b):
    if b < 1024:
        return b,'B'
    if b < 10*1024:
        return "%.1f"%(b/1024.0),'KB'
    if b < 1024**2:
        return "%.0f"%(b/1024.0),'KB'
    if b < 10*1024**2:
        return "%.1f"%(b/1024.0**2),'MB'
    if b < 1024**3:
        return "%.0f"%(b/1024.0**2),'MB'
    if b < 10*1024**3:
        return "%.1f"%(b/1024.0**3),'GB'
    if b < 1024**4:
        return "%.0f"%(b/1024.0**3),'GB'
    if b < 10*1024**4:
        return "%.1f"%(b/1024.0**4),'TB'
    return "%.0f"%(b/1024.0**4),'TB'

def roundtime(t):
    if t < 10:
        return "%.1f"%t,"sec"
    if t < 60:
        return "%.0f"%t,"sec"
    if t < 10*60:
        return "%d:%02d"%(int(t)/60,int(t)%60), "min:sec"
    if t < 60*60:
        return "%d"%(t/60.0,),"min"
    return "%d:%d"%(int(t)/(60*60),(int(t)/60)%60), "hrs:min"

class MultiHash(object):
    def __init__(self,md5=None,sha1=None,len=None):
        self.md5 = md5
        self.sha1 = sha1
        self.len = len
    def check(self,mh):
        if self.md5 != None and mh.md5 != None and self.md5 != mh.md5:
            return False
        if self.sha1 != None and mh.sha1 != None and self.sha1 != mh.sha1:
            return False
        if self.len != None and mh.len != None and self.len != mh.len:
            return False
        return True
    @staticmethod
    def hash(f,verbose=False):
        assert os.path.exists(f), f
        bufsize = 128*1024;
        size = os.path.getsize(f)
        sha1hash = sha1()
        md5hash  = md5()
        starttime = time.time()
        h = open(f,'rb')
        while True:
            try:
                buf = h.read(bufsize)
            except IOError:
                break
            if not buf:
                break
            sha1hash.update(buf) 
            md5hash.update(buf)
        h.close()
        sha1_hash = sha1hash.hexdigest().lower()
        md5_hash = md5hash.hexdigest().lower()
        if verbose:
            elapsed = (time.time() - starttime)
            if elapsed > 0:
                rate = float(size)/elapsed
            else:
                elapsed = 0
                rate = 0
            sizestr,sizeunits = roundbytes(size)
            ratestr,rateunits = roundbytes(rate)
            timestr,timeunits = roundtime(elapsed)
            print("%s: %s %s in %s %s at %s %s/s"%(os.path.split(f)[1],sizestr,sizeunits,timestr,timeunits,ratestr,rateunits))
        return MultiHash(md5=md5_hash,sha1=sha1_hash,len=size)

class ChecksumTable:
    def __init__(self,directory=None,cksumfile=None,path=None,verbose=False):
        if path and os.path.exists(path):
            if os.path.isdir(path) and not directory:
                directory = path
            elif not os.path.isdir(path) and not cksumfile:
                cksumfile = path
        if directory:
            self.directory = directory
        if cksumfile:
            self.path = cksumfile
        if not directory:
            self.directory = self.autounpath()
            # print self.directory
        if not cksumfile:
            self.path = self.autopath()
            # print self.path
        if not os.path.exists(self.directory):
            raise RuntimeError("No directory: %s"%self.directory)
        if not os.path.isdir(self.directory):
            raise RuntimeError("Not a directory: %s"%self.directory)
        self.prefixlen = len(os.path.realpath(os.path.abspath(self.directory)).strip(os.sep).split(os.sep))
        self.files = {}
        self.verbose = verbose
    def normalize(self,f):
        return '/'.join(os.path.realpath(os.path.abspath(f)).strip(os.sep).split(os.sep)[self.prefixlen:])
    def allfiles(self):
        return iter(self.files.keys())
    def empty(self):
        return (len(self.files) == 0)
    def test(self):
        return os.path.exists(self.path)
    def add(self,f):
        try:
            h = MultiHash.hash(f,verbose=self.verbose)
            nf = self.normalize(f)
            self._add(nf,h)
        except (OSError,IOError) as e:
            print("I/O error computing checksums for %s: %s"%(f,str(e)), file=sys.stderr)

    def _add(self,nf,h):
        if nf not in self.files:
            self.files[nf] = h
        elif h != self.files[nf]:
            print("Repeated normalized file with inconsistent hash: %s"%(nf,), file=sys.stderr)
    def remove(self,f):
        nf = self.normalize(f)
        assert nf in self.files, f
        del self.files[nf]
    def has(self,f):
        # print self.normalize(f),self.files
        return self.normalize(f) in self.files
    def check(self,f,hash=None):
        if not hash:
            try:
                hash = MultiHash.hash(f,verbose=self.verbose)
            except (OSError,IOError) as e:
                print("I/O error computing checksums for %s: %s"%(f,str(e)), file=sys.stderr)
                return False 
        return self.files[self.normalize(f)].check(hash)
    def truncated(self,f):
        nf = self.normalize(f)
        if self.files[nf].len != None and self.files[nf].len > os.path.getsize(f):
            return True
        return False

class VUChecksumTable(ChecksumTable):
    def autounpath(self):
        return os.path.split(self.path)
    def autopath(self):
        return os.path.join(self.directory.rstrip(os.sep),'md5sums.txt')
    def read(self,d):
        h=open(self.path)
        for l in h:
            sl = l.strip().split(None,1)
            self._add(sl[1],MultiHash(md5=sl[0]))
        h.close()

class NISTChecksumTable(ChecksumTable):
    def autounpath(self):
        return os.path.split(self.path)[0]
    def autopath(self):
        return os.path.join(self.directory.rstrip(os.sep),'md5.txt')
    def read(self):
        h=open(self.path)
        next(h)
        for l in h:
            sl = l.strip().rsplit(None,1)
            self._add(sl[0],MultiHash(md5=sl[1]))
        h.close()        

class DCCChecksumTable(ChecksumTable):
    def autounpath(self):
        if not self.path.endswith('.cksum'):
            raise RuntimeError('Can\'t infer directory from checksum file without .cksum ending')
        if os.path.isdir(self.path[:-6]):
            return self.path[:-6]
        dir,fname = os.path.split(self.path)
        if os.path.split(dir)[1] == fname[:-6]:
            return dir
        raise RuntimeError('Can\'t infer directory from checksum file')
    def autopath(self):
        return self.directory.rstrip(os.sep)+'.cksum'
    def read(self):
        h=open(self.path)
        for l in h:
            sl = l.strip().split(None,3)
            sl[2] = int(sl[2])
            self.files[sl[3]] = MultiHash(*(sl[:3]))
        h.close()
    def write(self):
        wh = open(self.path,'w')
        for fn,mh in sorted(self.files.items()):
            print("\t".join(map(str,[mh.md5,mh.sha1,mh.len,fn])), file=wh)
        wh.close()

if len(args) < 1:
    parser.print_help()
    sys.exit(1)
    
args1 = []
for p in args:
    if not os.path.exists(p):
        parser.error("Path %s does not exist"%p)

exitstatus = 0
for d in args:

    # Defaults correspond to DCC with autofilename
    try:
        cksum = eval("%sChecksumTable(path=d,cksumfile=opts.cksumfile,verbose=opts.verbose)"%opts.cksumformat)
    except RuntimeError as e:
        parser.error(str(e))

    check=False
    write=False
    update=opts.update
    if cksum.test():
        cksum.read()
        check=True
        if not opts.quiet:
            print("Checking %s ..."%(cksum.directory,))
    else:
        if opts.checkonly:
            if opts.quiet == 0:
                print("Checksum file for %s is missing"%(cksum.directory,))
            else:
                print("%s: Checksums missing"%(cksum.directory,))
            continue
        if opts.cksumformat != "DCC":
            parser.error("Can only write DCC format checksum file!")
        write=True
        if not opts.quiet:
            print("Computing checksums for "+cksum.directory)

    newfiles = 0
    missing = 0
    changed = 0

    seen = set()
    for f in filelist(cksum.directory,ignorefiles=["md5.txt","md5sums.txt",os.path.split(cksum.path)[1]]):
        if opts.match and not re.search(opts.match,os.path.split(f)[1]):
            continue
        if write:
            cksum.add(f)
        if check:
            if not cksum.has(f):
                if not opts.common and not opts.verify:
                    newfiles += 1
                    if not opts.quiet:
                        print("  File %s is new"%(f,))
                    if update:
                        cksum.add(f)
            elif not cksum.check(f):
                changed += 1
                if not opts.quiet:
                    if cksum.truncated(f):
                        print("  File %s is truncated"%(f,))
                    else:
                        print("  File %s has changed"%(f,))
                if update:
                    cksum.remove(f)
                    cksum.add(f)
            seen.add(cksum.normalize(f))

    if check:
        expected = set(cksum.allfiles())
        for nf in (expected - seen):
            if not opts.common:
                missing += 1
                if not opts.quiet:
                    print("  File %s is missing"%(nf,))
                if update:
                    cksum.remove(f)

        if (missing + changed + newfiles) == 0:
            if opts.quiet == 0:
                print("  All checksums match!")
            if opts.quiet == 1:
                print("%s: All checksums match!"%(cksum.directory,))
        else:
            if not update:
                exitstatus = 1
            if opts.quiet > 0:
                print("%s: Changed: %d, Missing: %d, New: %d"%(cksum.directory,changed,missing,newfiles), file=sys.stderr)

    if write or (update and (missing + changed + newfiles) > 0):
        cksum.write()

sys.exit(exitstatus)
