#!/usr/bin/env python3

from __future__ import print_function

import sys, os, os.path
import copy
import encodings
import platform
import version

# monkeypatch to get around issues with Georgetown's certificates!
try:
    import ssl
    ssl._create_default_https_context = ssl._create_unverified_context
except (ImportError,AttributeError):
    pass

import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)
try:
    from urllib.parse import urlparse, quote_plus, urlencode, urlsplit
    from urllib.request import URLopener
except ImportError:
    from urlparse import urlparse, urlsplit
    from urllib import quote_plus, urlencode
    from urllib import URLopener

try:
    import http.cookies as Cookie
except ImportError:
    import Cookie
# import mysjson as json
import json
import configfile
import re
import cgi
import datetime
import getpass
import time
import inspect
import subprocess
import traceback
import signal
import glob, fnmatch
from optparse import OptionParser, Values
from operator import itemgetter
from lockfile import FileLock, LockTimeout

class CPTACDataPortal(object):
    commands = ('list','get','put','mkdir','delete')
    tokenurl = 'dataPrivate/getTokenAuth'

    def __init__(self,**kwargs):
        cmdline = kwargs.get('cmdline',False)
        if cmdline:
            self.verbose = sys.argv[1:].count('-v')
        else:
            self.verbose = False
        self.verbose = kwargs.get('verbose',self.verbose)
        self.read_config(verbose=(self.verbose>0))
        self.set_version()
        self.find_aspera()
        self.parse_arguments(cmdline=cmdline)
        if not cmdline:
            for k,v in list(kwargs.items()):
                setattr(self.opts,k,v)
        self.check_opts(self.opts,cmdline=cmdline)
        self.verbose = self.opts.verbose
        self.urlopener = SessionOpener(self.VERSION)
        self.sessiontime = 0
        if self.opts.sessiontime > 0:
            self.sessiontime = (self.opts.sessiontime*60.0)
        self.sessionfile = None
        if self.opts.sessioncache:
            self.sessionfile = os.path.expanduser('~'+os.sep+'.'+self.portal+'.session.txt')
        self.lastlogin = None
        self.transspec = None
        self.listcache = dict()
        if cmdline:
            self.execute(self.args)

    def setopt(self,k,v):
        setattr(self.opts,k,v)
        
    def read_config(self,verbose=False):
        if getattr(sys, 'frozen', False):
            prog = sys.executable
        else:
            prog = __file__
        prog = os.path.abspath(os.path.realpath(prog))
        script = os.path.join(os.path.split(prog)[0],self.portal)
        cfg = configfile.readconfig(script,verbose=verbose)

        # Expected to be set in config (throws exception otherwise)
        default_force = cfg.getboolean('Portal','Force')
        default_cksum = cfg.getboolean('Portal','Checksum')
        default_quiet = cfg.getboolean('Portal','Quiet')
        default_echo = cfg.getboolean('Portal','Echo')
        default_ip = cfg.get('Portal','Address')
        default_sessioncache = cfg.getboolean('Portal','SessionCache')
        default_sessiontime = cfg.getfloat('Portal','SessionTime')

        default_resume = cfg.get('Aspera','Resume')
        self.ascp_opts = cfg.get('Aspera','Options')
        self.ascp_opts = self.ascp_opts.split()
        
        # May not be set in config
        default_user = configfile.get(cfg,'Portal','User',None)
        default_password = configfile.get(cfg,'Portal','Password',None)

        self.cfg = cfg
        self.default = dict(force=default_force,cksum=default_cksum,quiet=default_quiet,
                            echo=default_echo,ip=default_ip,sessioncache=default_sessioncache,
                            sessiontime=default_sessiontime,resume=default_resume,
                            user=default_user,password=default_password)

    def find_aspera(self):
        VARIABLES = copy.copy(os.environ)
        if 'INSTALL' not in VARIABLES:
            if getattr(sys, 'frozen', False):
                prog = sys.executable
            else:
                prog = __file__
            prog = os.path.abspath(os.path.realpath(prog))
            installdir = os.path.split(prog)[0]
            base = self.portal
            if base == "cptactransfer":
                base = "cptacdcc"
            # os.path.split(os.path.abspath(sys.argv[0]))[1]
            # if base.endswith('.py') or base.endswith('.exe'):
            #     base = base.rsplit('.',1)[0]
            if os.path.isdir(os.path.join(installdir,base+'.data')):
                VARIABLES['INSTALL'] = os.path.join(installdir,base+'.data')
            elif os.path.isdir(os.path.join('.',base+'.data')):
                VARIABLES['INSTALL'] = os.path.join('.',base+'.data')
            else:
                VARIABLES['INSTALL'] = installdir
        if 'SYSTEM' not in VARIABLES:
            VARIABLES['SYSTEM'] = platform.system()
            bits = platform.architecture()[0][:2]
        if VARIABLES['SYSTEM'] == 'Linux' and bits == '64':
            VARIABLES['SYSTEM'] = 'Linux64'
        ASPERA = os.path.abspath(self.cfg.get('Aspera','Install',raw=True)%VARIABLES)
        if VARIABLES['SYSTEM'] == 'Darwin':
            self.ascp = os.path.join(ASPERA,'Contents','Resources','ascp')
            self.ascpkey = os.path.join(ASPERA,'Contents','Resources','asperaweb_id_dsa.putty')
        elif VARIABLES['SYSTEM'] == 'Windows':
            self.ascp = os.path.join(ASPERA,'bin','ascp.exe')
            self.ascpkey = os.path.join(ASPERA,'etc','asperaweb_id_dsa.openssh')
        else:
            self.ascp = os.path.join(ASPERA,'bin','ascp')
            self.ascpkey = os.path.join(ASPERA,'etc','asperaweb_id_dsa.openssh')

        assert os.path.isdir(ASPERA), "ASPERA install directory does not exist - check %s.ini file"%(self.portal,)

        assert os.path.exists(self.ascp), "ASPERA ascp program not found, expected location: %s"%(self.ascp,)
        assert os.access(self.ascp,os.X_OK), "ASPERA ascp program not executable: %s"%(self.ascp,)
        assert os.path.exists(self.ascpkey), "ASPERA public key file asperaweb_id_dsa not found, expected location: %s"(self.ascpkey,)

    def set_version(self):
        self.VERSION = version.VERSION + ' (%s, %s, %s bit)'%(sys.argv[0].split('/')[-1],
                                                              platform.system(),
                                                              platform.architecture()[0][:2])
        
    def add_login_options(self,parser):
        # override for public portal
        parser.add_option('-u','--user',dest="user",type='string',default=self.default['user'],
                          help="CPTAC portal user-name. Required.")
        parser.add_option('-p','--password',dest="password",type='string',default=self.default['password'],
                          help=" ".join("""
                          CPTAC portal password. If value is a file, password is read from
                          the file. If value is \"-\" password is read from stdin. If missing,
                          user is prompted for password. Default: Prompt.
                          """.split()))

    def parse_arguments(self,cmdline=True):
        parser = OptionParser(version=self.VERSION)
        self.add_login_options(parser)
        self.add_sort_options(parser)
        
        parser.add_option('-f','--force',dest="force",action='store_const',
                          const=(not self.default['force']),default=self.default['force'],
                          help="Toggle whether to update changed files on download/upload. Default: %s."%self.default['force'])
        parser.add_option('-k','--resume',dest="resume",type='choice',choices=list(map(str,list(range(4)))),
                          default=self.default['resume'],
                          help='File-check stringency for file-skipping on resume. One of: always retransfer (0); check file-size (1); sparse checksum (2); or full checksum (3). Default: %s.'%self.default['resume'])
        # parser.add_option('-C','--checksum',dest="checksum",action='store_const',
        #                   const=(not self.default['cksum']),default=self.default['cksum'],
        #                   help="Toggle whether to download and check (get) or compute and upload (put) checksum files (using cksum) for folder transfers. Default: %s."%self.default['cksum'])
        parser.add_option('-q','--quiet',dest="quiet",action='store_const',
                          const=(not self.default['quiet']),default=self.default['quiet'],
                          help="Toggle whether to execute ascp in quiet mode. Default: %s."%self.default['quiet'])
        parser.add_option('-e','--echo',dest="echo",action='store_const',
                          const=(not self.default['echo']),default=self.default['echo'],
                          help="Toggle whether to echo ascp command for get and put. Default: %s."%self.default['echo'])
        parser.add_option('-n','--noexecute',dest="noexecute",action='store_true',default=False,
                          help="Do not execute the ascp command for get and put. Implies -e/--echo.")
        parser.add_option('--sessioncache',dest="sessioncache",action='store_const',
                          const=(not self.default['sessioncache']),default=self.default['sessioncache'],
                          help="Toggle whether to cache session keys on the filesystem. Default: %s."%self.default['sessioncache'])
        parser.add_option('--sessiontime',dest="sessiontime",type='float',
                          default=self.default['sessiontime'],
                          help="Lenth of time to use session keys. Default: %s."%self.default['sessiontime'])
        parser.add_option('-v','--verbose',dest="verbose",action='count',default=0,
                          help="Print diagnostic and debugging information to standard error. Double for more information.")
        if cmdline:
            opts,args = parser.parse_args()
        else:
            opts,args = parser.parse_args([])

        opts.checksumfile = False
        opts.echo = (opts.echo or opts.noexecute)

        opts.sort = 'name'
        if hasattr(opts,'time') and opts.time:
            opts.sort = 'date'
        if opts.size:
            opts.sort = 'size'

        self.opts,self.args = opts,args

    def execute(self,args):
        cmd = "list"
        if len(args) > 0 and args[0] in self.commands:
            cmd = args.pop(0)

        if cmd == "list":
            self.check_list_args(args)
            if len(args) > 0:
                self.print_list(args[0])
            else:
                self.print_list()
        elif cmd == "get":
            self.check_get_args(args)
            self.get(*args)
        elif cmd == "put":
            self.check_put_args(args)
            self.put(*args)
        elif cmd == "delete":
            self.check_delete_args(args)
            self.delete(*args)
        elif cmd == "mkdir":
            self.check_mkdir_args(args)
            self.mkdir(*args)
        else:
            raise BadCommand(cmd)

    def check_list_args(self,args):
        if len(args) > 1:
            raise CommandArgumentError("Portal command list got unexpected arguments")

    def check_get_args(self,args):
        if len(args) < 1:
            raise CommandArgumentError("Portal command get requires a data portal file or folder")
        # if len(args) > 1:
        #     raise CommandArgumentError("Portal command get got unexpected arguments")

    def check_put_args(self,args):
        if len(args) < 2:
            raise CommandArgumentError("Portal command put requires a local file or folder and a data portal folder.")
        # if len(args) > 2:
        #     raise CommandArgumentError("Portal command get got unexpected arguments")

    def check_delete_args(self,args):
        if len(args) == 0:
            raise CommandArgumentError("Portal command delete requires a data portal file or folder")
        if len(args) > 1:
            raise CommandArgumentError("Portal command delete got unexpected arguments")

    def check_mkdir_args(self,args):
        if len(args) == 0:
            raise CommandArgumentError("Portal command mkdir requires a data portal folder name")
        if len(args) > 1:
            raise CommandArgumentError("Portal command mkdir got unexpected arguments")
            
    def get_password(self,opts,cmdline=False):
        if cmdline and (opts.password == None or opts.password == "-"):
            opts.password = getpass.getpass()
        elif os.path.exists(opts.password):
            opts.password = open(opts.password).read().strip()

        if opts.password in (None,"-"):
            raise PasswordRequired()

    def server(self):
        return self.default['ip']

    def baseurl(self):
        return 'https://%s/cptac'%(self.server(),)

    def geturl(self,path):
        return "/".join([self.baseurl(),path])
    
    def extract_fasp(self,url):
        assert(url.startswith('fasp:') or url.startswith('faspe:'))
        r = urlsplit(url.split(':',1)[1])
        fasp = dict(remote_user=r.username,remote_host=r.hostname,remote_port=r.port)
        query = cgi.parse_qs(r.query)
        fasp['path'] = r.path.rstrip('/')
        if r.path == "/":
            fasp['name'] = ""
        else:
            fasp['name'] = r.path.rstrip('/').rsplit('/',1)[1]
        for k,v in list(query.items()):
            fasp[k] = v[0]
        return fasp

    def parse_json(self,folder,rawlisting):

        upload_details = {}
        if isinstance(rawlisting,dict):
            if rawlisting.get('uploadUrl','').startswith('fasp:'):
                upload_details = self.extract_fasp(rawlisting['uploadUrl'])
                upload_details['uploadToken'] = upload_details['token']
            folder = '/'+rawlisting['folder'].strip('/')
            rawlisting = rawlisting['folderContent']

        listing = {}
        for item in rawlisting:
            current_item = copy.copy(item)
            current_item.update(self.extract_fasp(item['downloadUrl']))
            if 'modifyTime' in item:
                modtimestr = item['modifyTime']
                modtimestr = modtimestr.replace('T',' ').replace('Z',' ')
                current_item['date'] = datetime.datetime.strptime(modtimestr, "%Y-%m-%d %H:%M:%S ")
            if 'isSymLink' not in item:
                item['isSymLink'] = item['mode'].startswith('l')
                if item['isSymLink']:
                    item['isDirectory'] = False
            else:
                assert item['isSymLink'] in ('true','false',True,False), item
                item['isSymLink'] = (item['isSymLink'] in ('true',True))
            current_item['namefolder'] = current_item['name']
            current_item['fullpath'] = current_item['path']
            current_item['path'] = self.split(current_item['path'])[0]
            current_item['isFolder'] = False
            if item['isSymLink']:
                current_item['namefolder'] += '@'
            if item['isDirectory']:
                current_item['namefolder'] += '/'
                current_item['isFolder'] = True
            if 'size' in current_item:
                current_item['size'] = int(current_item['size'])
            elif 'fileSize' in current_item:
                current_item['size'] = int(current_item['fileSize'])
            if item.get('userId') == None:
                current_item['userId'] = "-"
            dummy,current_item['sizeAndUnit'] = self.convertsize(current_item['sizeAndUnit'])
            listing[current_item['fileName']] = current_item
            if not upload_details:
                upload_details = copy.copy(current_item)

        return self.clean_listing(folder=folder,upload=upload_details,files=listing)

    def parse_asphtml(self,folder,buffer):
        intable = False; intbody = False; inrow = False;
        transspec = None
        rows = []
        for l in buffer.splitlines():
            # print >>sys.stderr, l
            if 'transferSpec' in l and 'fasp_port' in l and transspec == None:
                jsonstr = l.split("'",1)[1].rsplit("'",1)[0]
                transspec = json.loads(jsonstr)
                transspec['remote_port'] = transspec['fasp_port']
            if not intable and '<table' in l:
                intable = True
                # print >>sys.stderr, "INTABLE"
                continue
            if intable and '</table>' in l:
                intable = False
                # print >>sys.stderr, "NOT INTABLE"
                continue
            if intable and "<tbody" in l:
                intbody = True
                # print >>sys.stderr, "INTBODY"
                continue
            if intbody and "</tbody>" in l:
                intbody = False
                # print >>sys.stderr, "NOT INTBODY"
                continue
            if intbody and "<tr" in l:
                inrow = True
                # print >>sys.stderr, "INTR"
                rows.append([])
                poscnt = 0
                continue
            if inrow and "</tr>" in l:
                inrow = False
                # print >>sys.stderr, "NOT INTR"
                continue
            if inrow and '<td ' in l:
                poscnt += 1
                if poscnt < 2:
                    continue
                if poscnt == 2:
                    if 'Download Folder' in l or 'icon_download_folder' in l:
                        rows[-1].append("Folder")
                    elif 'Download File' in l or 'icon_download_file' in l:
                        rows[-1].append("File")
                    else:
                        rows[-1].append("")
                else:
                    value = re.sub(r'\</?(td|a|input)( [^>]+)?\>','',l.strip())
                    value = value.strip()
                    value = value.replace("&lt;", "<")
                    value = value.replace("&gt;", ">")
                    value = value.replace("&amp;", "&")
                    rows[-1].append(value)
                continue

        if not transspec:
            transspec = dict()

        listing = {}
        for r in rows:
            if len(r) == 3:
                d = dict(fileName=r[1],path=folder,fullpath=self.join(folder,r[1]),
                         sizeAndUnit=r[2])
            elif len(r) == 5:
                d = dict(fileName=r[1],path=folder,fullpath=self.join(folder,r[1]),
                         sizeAndUnit=r[2],userId=r[3],date=r[4])
            else:
                continue
            d.update(transspec)
            d['size'],d['sizeAndUnit'] = self.convertsize(d['sizeAndUnit'])
            if not d.get('date'):
                d['date'] = "-"
            else:
                d['date'] = self.convertdate(d['date'])
            d['name'] = d['fileName']
            d['namefolder'] = d['fileName']
            d['isFolder'] = False
            if not d.get('userId'):
                d['userId'] = "-"
            if r[0] == 'Folder':
                d['namefolder'] += '/'
                d['isFolder'] = True
            listing[d['fileName']] = d

        return self.clean_listing(folder=folder,upload=transspec,files=listing)
        
    def clean_listing(self,folder,upload,files):
        for f in files:
            for k,v in list(files[f].items()):
                if isinstance(v,str) and v.strip() == "":
                    del files[f][k]
                    continue
                if not isinstance(k,str):
                    del files[f][k]
                    files[f][str(k)] = v
                    continue
        for k,v in list(upload.items()):
            if isinstance(v,str) and v.strip() == "":
                del upload[k]
                continue
            if not isinstance(k,str):
                del upload[k]
                upload[str(k)] = v
                continue
        return dict(folder=folder,upload=upload,files=files)

    def normalize(self,path):
        if path == None:
            return "/"
        return "/"+path.strip('/')

    def split(self,path):
        folder,filename = self.normalize(path).rsplit('/',1)
        if not folder:
            folder = "/"
        return folder,filename

    def join(self,*args):
        return self.normalize("/"+"/".join([a.strip("/") for a in args]))

    def login(self):

        now = time.time()
        if self.lastlogin != None and self.lastlogin > (now - self.sessiontime):
            return
        
        lock = None
        if self.sessionfile:
            lock = FileLock(self.sessionfile)

        try:
            
            if lock != None:
                # what if 10 seconds is not enough?
                lock.acquire(timeout=10)
            
            if self.sessionfile and os.path.exists(self.sessionfile) and \
                   now < (os.path.getmtime(self.sessionfile) + self.sessiontime):
                jsessionid = open(self.sessionfile).read().strip()
                self.lastlogin = os.path.getmtime(self.sessionfile)-10
                
            else:
        
                so = SessionOpener(self.VERSION)

                jsessionid = None
                try:
                    if self.verbose >= 2:
                        print("LoginURL: "+",".join(self.loginurl()), file=sys.stderr)
                    h = so.open(*self.loginurl())
                    jsessionid = so.getcookie(h.info())
                except GotCookie as e:
                    jsessionid = e.args[0]
                except LoginError:
                    raise PermissionDenied(self.loginurl()[0])
                except IOError as e:
                    if 'Unhandled HTTP Error' in e.args[0]:
                        raise ServerError(self.loginurl()[0],e.args[0].split(':',1)[1].strip())
                    else:
                        raise ConnectionErrorExtra(self.server(),"\n  ".join(map(str,e.args)))

                if not jsessionid:
                    if self.sessionfile and os.path.exists(self.sessionfile):
                        os.unlink(self.sessionfile)
                    raise PermissionDenied(self.loginurl()[0])

                if self.sessionfile != None:
                    wh = open(self.sessionfile,'w'); wh.write(jsessionid); wh.close();
                    self.lastlogin = now

                time.sleep(10);
                    
            if self.verbose >= 2:
                print("SetCookie: "+jsessionid, file=sys.stderr)
            self.urlopener.setheader('Cookie',jsessionid)
            self.jsessionid = jsessionid

        finally:
            if lock:
                lock.release()

    def urlread(self,url,data=None):
        
        self.login()

        if self.verbose >= 2:
            print("URLRead: "+url, file=sys.stderr)

        try:
            if not data:
                h = self.urlopener.open(url)
            else:
                h = self.urlopener.open(url,urlencode(data))
            return h.read().decode('utf8')
        except IOError as e:
            traceback.print_exc()
            if 'Unhandled HTTP Error' in e.args[0]:
                raise ServerError(url,e.args[0].split(':',1)[1].strip())
            else:
                raise ConnectionError(self.server())
        except (GotCookie,LoginError) as e:
            # traceback.print_exc()
            raise PermissionDenied(url)
        
    def list(self,path=None):
        # if self.verbose >= 3:
        #     print >>sys.stderr, "list: %s"%(path,)

        paths = self.expand_portal_path(path)

        # print path,paths

        if len(paths) == 0:
            raise PortalPathNotFound(path)

        if len(paths) > 1:
            raise PortalPathAmbiguous(path)

        path = paths[0]

        if path in self.listcache:
            return self.listcache[path]

        listing = self.getlisting(path)

        if len(listing['files']) <= 1 and not self.isPortalFolder(path):
            raise PortalFolderNotFound(path)

        self.listcache[path] = listing
        return self.listcache[path]

    def clear_listcache(self):
        self.listcache.clear()

    def get_token(self,**kwargs):

        tokenurl = kwargs.get('tokenGeneratorURL',self.geturl(self.tokenurl))
        params = dict(files=kwargs['fullpath'],user=kwargs['remote_user'],direction=kwargs.get('direction','receive'))
        # params['_'] = kwargs['cookie'].split('_')[-1]
        params = urlencode(params)
        tokenurl += '?' + params

        buffer = self.urlread(tokenurl)
        retval = json.loads(buffer.split('(',1)[1].rsplit(')',1)[0])
        return retval

    def get_token_node(self,**kwargs):
        direction = kwargs.get('direction','receive')
        if direction == 'receive':
            tokenurl = self.geturl(kwargs.get('portal')+'/downloadSetup')
            params = dict(sources=kwargs['fullpath'])
        elif direction == 'send':
            tokenurl = self.geturl(kwargs.get('portal')+'/uploadSetup')
            params = dict(path=kwargs['fullpath'])
        else:
            raise("Bad direction")
        buffer = self.urlread(tokenurl,params)
        retval = json.loads(buffer)
        retval = retval['transfer_specs'][0]['transfer_spec']
        retval['remote_port'] = retval['fasp_port']
        return retval
        
    def walk_portal_paths(self,root=None):
        toexplore = [self.normalize(root)]
        while len(toexplore) > 0:
            current  = toexplore.pop(0)
            files = self.list(current)['files']
            for fn in files:
                # print root,current,fn,files[fn]
                pth = self.join(current,fn)
                if files[fn]['isFolder']:
                    toexplore.insert(0,pth)
                else:
                    yield pth

    def expand_portal_path(self,path,root=None):

        if root==None:
            if path in ("/",None):
                return ["/"]
            root = "/"
            path = self.normalize(path).split("/")[1:]

        if len(path) == 0:
            return [root]

        result = []
        if re.search('[*?]',path[0]):
            for fn in self.list(root)['files']:
                if fnmatch.fnmatch(fn,path[0]):
                    result.extend(self.expand_portal_path(path[1:],self.join(root,fn)))
        else:
            result = self.expand_portal_path(path[1:],self.join(root,path[0]))
        return sorted(result)

    def get(self,*args):
        for arg in args:
            any = False
            for path in self.expand_portal_path(arg):
                folder,filename = self.split(path)
                files = self.list(folder)['files']
                if os.path.exists(filename) and not self.opts.force:
                    raise LocalFileExists(filename)
                if filename not in files:
                    raise PortalPathNotFound(path)
                filemetadata = files[filename]
                if 'token' not in filemetadata:
                    filemetadata.update(self.get_token(**filemetadata))
                self.aspera_get(path,filename,filemetadata)
                any = True
            if not any:
                raise PortalPathNotFound(arg)

    def isPortalFolder(self,folder):
        if self.normalize(folder) == "/":
            return True
        folderfolder,foldername = self.split(folder)
        folderlist = self.list(folderfolder)['files']
        if foldername not in folderlist or \
               not folderlist[foldername]['namefolder'].endswith('/'):
            return False
        return True

    def put(self,*args):
        localpaths = args[:-1]
        folder = args[-1]
        if not self.isPortalFolder(folder):
            raise PortalFolderNotFound(folder)
        folder,upload,files = list(map(self.list(folder).get,["folder","upload","files"]))
        for localpath in localpaths:
            localdir,localfilename = os.path.split(localpath)
            if localfilename in files and not self.opts.force:
                raise PortalPathExists(self.join(folder,localfilename))
        if 'token' not in upload:
            upload.update(self.get_token(direction='send',fullpath=folder,**upload))
        self.aspera_put(localpaths,folder,upload)

    def mkdir(self,*args):
        for path in args:
            folder,filename = self.split(path)
            paths = self.expand_portal_path(folder)
            if len(paths) == 0:
                raise PortalPathNotFound(folder)
            if len(paths) > 1:
                raise PortalPathAmbiguous(folder)
            folder = paths[0]
            if not self.isPortalFolder(folder):
                raise PortalFolderNotFound(folder)
            if filename in self.list(folder)['files']:
                raise PortalPathExists(self.join(folder,filename))
            self.domkdir(folder,filename)

    def delete(self,*args):
        for arg in args:
            any = False
            for path in self.expand_portal_path(arg):
                folder,filename = self.split(path)
                files = self.list(folder)['files']
                if filename not in files:
                    raise PortalPathNotFound(path)
                self.dodelete(path)
                any = True
            if not any:
                raise PortalPathNotFound(arg)

    def convertsize(self,s):
        if not s:
            return 0, "0 B"
        m = re.search(r'^(-?\d+(\.\d+)?) *(B|KB|MB|GB|TB|K|M|G|T|null)?$',s)
        assert m, repr(s)
        value = float(m.group(1))
        units = m.group(3)
        if units in ("B",None,"") :
            return int(value),"%d B "%(int(value),)
        if value == int(value):
            value = int(value)
        else:
            value = round(value,2)
        if units in ("KB","K"):
            return int(round(value*1024,0)),"%s KB"%(value,)
        if units in ("MB","M"):
            return int(round(value*1024*1024,0)),"%s MB"%(value,)
        if units in ("GB","G"):
            return int(round(value*1024*1024*1024,0)),"%s GB"%(value,)
        if units in ("TB","T"):
            return int(round(value*1024*1024*1024*1024,0)),"%s TB"%(value,)
        if units in ("null",):
            return 0,"0 B"
        raise RuntimeError("Bad units!")

    def convertdate(self,s):
        return datetime.datetime.strptime(s, "%d-%b-%Y %H:%M")

    def print_list(self,path=None):
        listing = self.list(path)
        folder = listing['folder']
        listing = listing['files']
        try:
            maxnamelen = max([len(listing[n]['namefolder']) for n in listing])
        except ValueError:
            maxnamelen = 10
        print("Folder:",folder)
        if not self.opts.human:
            try:
                maxsizelen = max([len(str(listing[n]['size'])) for n in listing])
            except ValueError:
                maxsizelen = 10
            fmtstr = '%%(namefolder)- %ds   %%(size)%ds'%(maxnamelen,maxsizelen,)
        else:
            fmtstr = '%%(namefolder)- %ds   %%(sizeAndUnit)9s'%(maxnamelen,)
        if len(listing) > 0 and list(listing.values())[0]['date'] not in ("-",""):
            fmtstr += '   %(date)- 19s'
        if len(listing) > 0 and list(listing.values())[0]['userId'] not in ("-",""):
            fmtstr += '   %(userId)- 10s'
        for p in sorted(list(listing.values()),key=itemgetter(self.opts.sort),reverse=self.opts.reverse):
            print(fmtstr%p)

    def aspera_get(self,portal_path,local_path,metadata):
        # print portal_path,local_path,metadata
        cmd = [self.ascp,
               '-i', self.ascpkey,
               '-P', '%(remote_port)s'%metadata,
               '-O', '%(remote_port)s'%metadata,
               '-v' if (not self.opts.quiet) else '-q',       # verbose
               '-k', self.opts.resume,
               '-u', self.VERSION,
               ] + self.ascp_opts + [
               '-W', '%(token)s'%metadata,
               '--user', '%(remote_user)s'%metadata,
               '--host', '%(remote_host)s'%metadata,
               '--mode', 'recv',
               portal_path,
               local_path]
        self.aspera_execute(cmd)

    def aspera_put(self,local_path,portal_path,metadata):

        # print local_path,portal_path,metadata
        cmd = [self.ascp,
               '-i', self.ascpkey,
               '-P', '%(remote_port)s'%metadata,
               '-O', '%(remote_port)s'%metadata,
               '-v' if (not self.opts.quiet) else '-q',       # verbose
               '-k', self.opts.resume,
               '-u', self.VERSION,
               ] + self.ascp_opts + [
               '-W', '%(token)s'%metadata,
               '--user', '%(remote_user)s'%metadata,
               '--host', '%(remote_host)s'%metadata,
               '--mode', 'send'] + \
               list(local_path) + \
               [portal_path]
        self.aspera_execute(cmd)

    def aspera_execute(self,cmd):

        if self.opts.echo or self.verbose:
            print(' '.join([s if ' ' not in s else '"%s"'%s for s in cmd]))
            sys.stdout.flush()

        if self.opts.noexecute:
            return

        os.environ['ASPERA_SCP_COOKIE'] = "Client: "+self.VERSION

        if sys.platform == 'win32':
            try:
                p = subprocess.Popen(cmd,executable=cmd[0],creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
            except OSError:
                raise ASCPExecuteError(1)

        else:
            try:
                p = subprocess.Popen(cmd)
            except OSError:
                raise ASCPExecuteError(1)

        try:
            while True:
                p.poll()
                if p.returncode != None:
                    break
                time.sleep(1)
        except KeyboardInterrupt:
            if sys.platform == 'win32':
                os.kill(p.pid,signal.CTRL_BREAK_EVENT)
                sys.exit(1)
            else:
                os.kill(p.pid,signal.SIGKILL)
                sys.exit(1)
        if p.returncode:
            raise AsperaExecuteError(p.returncode)

class CPTACPublic_JSON(CPTACDataPortal):
    portal = 'cptacpublic'
    tags = ['publicjson','cptacpublicjson']
    commands = ('list','get')
    loginpath = 'study/acceptDisclaimer'
    listpath = 'dataPublic/listJSON'
    
    def __init__(self,**kwargs):
        super(CPTACPublic_JSON,self).__init__(**kwargs)

    def add_login_options(self,parser):
        parser.add_option('--accept',dest="accept",action='store_true',default=False,
                  help="Accept data use aggreement. Required.")
            
    def add_sort_options(self,parser):
        parser.add_option('-t','--time',dest='time',action='store_true',
                          default=False,help="Sort listings by modification time.")
        parser.add_option('-s','--size',dest='size',action='store_true',
                          default=False,help="Sort listings by file/folder size.")
        parser.add_option('-r','--reverse',dest='reverse',action='store_true',
                          default=False,help="Reverse the order of the listing sort.")
        parser.add_option('--humansizes',dest='human',action='store_true',
                          default=False,help="Human readable file/folder sizes.")

    def check_opts(self,opts,cmdline):
        if not opts.accept:
            raise MissingOptionError("CPTAC DCC public portal data use agreement must be accepted.\nSee https://%s/cptac/dataPublic/disclaimer."%self.default['ip'])

    def loginurl(self):
        return self.geturl(self.loginpath),

    def getlisting(self,path=None):

        listurl = self.geturl(self.listpath)
        listPath = self.normalize(path)
        if listPath != "/":
            listurl += ('?' + urlencode(dict(currentPath=listPath)))

        try:
            buffer = self.urlread(listurl)
            rawlisting = json.loads(buffer)
        except NotFound:
            raise PortalPathNotFound(listPath)
        except ValueError:
            raise BadJSONListing()

        return self.parse_json(listPath,rawlisting)

class CPTACPublic_HTTP(CPTACPublic_JSON):
    tags = ['publichttp','cptacpublichttp']

    def check_opts(self,opts,cmdline):
        super(CPTACPublic_HTTP,self).check_opts(opts,cmdline)
        setattr(opts,'human',True)

    def convertdate(self,s):
        return datetime.datetime.strptime(s, "%Y-%m-%d %H:%M")

    def get_token(self,**kwargs):
        return self.get_token_node(portal='study',**kwargs)

    def getlisting(self,path=None):

        # if not self.transspec:
            # queryurl = self.geturl(self.querypath)
            # buffer = self.urlread(queryurl)
            # for l in buffer.splitlines():
                # if 'transferSpec' in l:
                    # jsonstr = l.split("'",1)[1].rsplit("'",1)[0]
                    # # jsonstr = jsonstr.decode( 'unicode-escape' ).encode( 'ascii' )
                    # self.transspec = json.loads(jsonstr)
                    # self.transspec['remote_port'] = self.transspec['fasp_port']
                    # break

        # if not self.transspec:
        #     self.transspec = self.get_token_node(portal='dataPublic',fullpath='/')
        self.transspec = {'remote_host': 'cptc-xfer.uis.georgetown.edu', 'port': 33001, 'remote_user': 'public_gcp'}

        listurl = 'https://%(remote_host)s/publicData'%self.transspec
        listPath = self.normalize(path)
        listurl += (listPath+"/")

        try:
            buffer = self.urlread(listurl)
        except NotFound:
            raise PortalPathNotFound(listPath)

        rows = []
        for l in buffer.splitlines():
            if 'Parent Directory' in l:
                continue
            if l.startswith('<tr>'):
                if '[DIR]' in l:
                    isdir = 'Folder'
                else:
                    isdir = 'File'
                rows.append([isdir])
                for i,m in enumerate(re.finditer(r'<td.*?</td>',l)):
                    if i not in (1,2,3):
                        continue
                    value = m.group(0)
                    m = re.search(r'<a href="([^ "]*)">',value)
                    if m:
                        value = m.group(1).strip('/')
                    else:
                        value = re.sub(r'\</?(td|a|img)( [^>]+)?\>','',value)
                    value = value.strip()
                    if value == "-":
                        value = ""
                    rows[-1].append(value)

        listing = {}
        for r in rows:
            if len(r) != 4:
                continue
            if r[0] == 'Folder':
                r[1] = r[1].rstrip('/')
            d = dict(fileName=r[1],path=listPath,fullpath=self.join(listPath,r[1]),
                     sizeAndUnit=r[3],date=r[2])
            d.update(self.transspec)
            if r[0] != 'Folder':
                d['size'],d['sizeAndUnit'] = self.convertsize(d['sizeAndUnit'])
            else:
                d['size']= 0
                d['sizeAndUnit'] = "-"
            d['date'] = self.convertdate(d['date'])
            d['name'] = d['fileName']
            d['namefolder'] = d['fileName']
            d['userId'] = "-"
            d['isFolder'] = False
            if r[0] == 'Folder':
                d['namefolder'] += '/'
                d['isFolder'] = True
            listing[d['fileName']] = d

        return self.clean_listing(folder=listPath,upload=self.transspec,files=listing)

class CPTACPublic_Scraper(CPTACPublic_JSON):
    tags = ['publicscrape','cptacpublicscrape']
    listpath = 'dataPublic/list'

    def check_opts(self,opts,cmdline):
        super(CPTACPublic_Scraper,self).check_opts(opts,cmdline)

        setattr(opts,'human',True)

    def add_sort_options(self,parser):
        parser.add_option('-t','--time',dest='time',action='store_true',
                          default=False,help="Sort listings by modification time.")
        parser.add_option('-s','--size',dest='size',action='store_true',
                          default=False,help="Sort listings by fie/folder size.")
        parser.add_option('-r','--reverse',dest='reverse',action='store_true',
                          default=False,help="Reverse the order of the listing sort.")

    def getlisting(self,path=None):
        
        listurl = self.geturl(self.listpath)
        listPath = self.normalize(path)
        if listPath != "/":
            folder,name = self.split(listPath)
            listurl += ('/'+quote_plus(name)+'?' + urlencode(dict(currentPath=folder)))

        try:
            buffer = self.urlread(listurl)
        except NotFound:
            raise PortalPathNotFound(listPath)

        return self.parse_asphtml(listPath,buffer)

class CPTACPublic_NodeScraper(CPTACPublic_Scraper):
    tags = ['publicnodescrape','cptacpublicnodescrape']

    def get_token(self,**kwargs):
        return self.get_token_node(portal='dataPublic',**kwargs)

class CPTACPublic(CPTACPublic_HTTP):
    tags = ['cptacpublic','public']

class CPTACDCC_JSON(CPTACDataPortal):
    portal = 'cptacdcc'
    # loginpath = 'j_spring_security_check'
    loginpath = 'login/authenticate'
    listpath = 'dataPrivate/listJSON'
    mkdirpath = 'dataPrivate/createFolder'
    tags = ['dccjson','cptacdccjson']
    
    def __init__(self,**kwargs):
        super(CPTACDCC_JSON,self).__init__(**kwargs)

    def add_sort_options(self,parser):
        parser.add_option('-t','--time',dest='time',action='store_true',
                          default=False,help="Sort listings by modification time.")
        parser.add_option('-s','--size',dest='size',action='store_true',
                          default=False,help="Sort listings by file/folder size.")
        parser.add_option('-r','--reverse',dest='reverse',action='store_true',
                          default=False,help="Reverse the order of the listing sort.")
        parser.add_option('--humansizes',dest='human',action='store_true',
                          default=False,help="Human readable file/folder sizes.")

    def check_opts(self,opts,cmdline):
        
        if not opts.user:
            raise MissingOptionError("CPTAC portal username must be specified")

        self.get_password(opts,cmdline)

    def loginurl(self):
            
        params = dict(username=self.opts.user,
                      password=self.opts.password)

        return self.geturl(self.loginpath),urlencode(params)

    def getlisting(self,path=None):
        
        listurl = self.geturl(self.listpath)
        listPath = self.normalize(path)
        if listPath != "/":
            folder,name = self.split(listPath)
            urlencode(dict(currentPath=folder))
            listurl += ('/'+quote_plus(name)+'?' + urlencode(dict(currentPath=folder)))

        try:
            buffer = self.urlread(listurl)
            rawlisting = json.loads(buffer)
        except NotFound:
            raise PortalPathNotFound(listPath)
        except ValueError:
            raise BadJSONListing()

        return self.parse_json(listPath,rawlisting)

    def domkdir(self,folder,dirname):
        mkdirurl = self.geturl(self.mkdirpath)
        params = dict(currentPath=folder,folderName=dirname)
        buffer = self.urlread(mkdirurl,params)
        try:
            result = json.loads(buffer)
        except ValueError:
            raise BadJSONStatus()
        if not result['success']:
            raise MakeDirFailed(self.join(folder,dirname))

    def dodelete(self,path):
        listurl = self.geturl(self.listpath)
        listPath = self.normalize(path)
        if listPath != "/":
            folder,name = self.split(listPath)
            folder,name = self.split(folder)
            listurl += ('/'+quote_plus(name)+'?'+urlencode(dict(currentPath=folder)))
        params = {'_action_delete': 'Delete',
                  'itemChecked_1': listPath}
        try:
            buffer = self.urlread(listurl,params)
        except PermissionDenied as e:
            pass

class CPTACDCC_Scraper(CPTACDCC_JSON):
    tags = ['dccscrape','cptacdccscrape']
    listpath = 'dataPrivate/list'

    def check_opts(self,opts,cmdline):
        super(CPTACDCC_Scraper,self).check_opts(opts,cmdline)

        setattr(opts,'human',True)

    def add_sort_options(self,parser):
        parser.add_option('-t','--time',dest='time',action='store_true',
                          default=False,help="Sort listings by modification time.")
        parser.add_option('-s','--size',dest='size',action='store_true',
                          default=False,help="Sort listings by fie/folder size.")
        parser.add_option('-r','--reverse',dest='reverse',action='store_true',
                          default=False,help="Reverse the order of the listing sort.")

    def getlisting(self,path=None):
        
        listurl = self.geturl(self.listpath)
        listPath = self.normalize(path)
        if listPath != "/":
            folder,name = self.split(listPath)
            listurl += ('/'+quote_plus(name)+'?' + urlencode(dict(currentPath=folder)))

        try:
            buffer = self.urlread(listurl)
        except NotFound:
            raise PortalPathNotFound(listPath)

        return self.parse_asphtml(listPath,buffer)

class CPTACDCC_NodeScraper(CPTACDCC_Scraper):
    tags = ['dccnodescrape','cptacdccnodescrape']
    commands = ('list','get','put','mkdir')

    def get_token(self,**kwargs):
        return self.get_token_node(portal='dataPrivate',**kwargs)

class CPTACDCC(CPTACDCC_NodeScraper):
    tags = ['dcc','cptacdcc']

class CPTACTransfer(CPTACDataPortal):
    portal = 'cptactransfer'
    tags = ['xfer','cptacxfer','cptactransfer','transfer']

    def add_sort_options(self,parser):
        parser.add_option('-t','--time',dest='time',action='store_true',
                          default=False,help="Sort listings by modification time.")
        parser.add_option('-s','--size',dest='size',action='store_true',
                          default=False,help="Sort listings by file/folder size.")
        parser.add_option('-r','--reverse',dest='reverse',action='store_true',
                          default=False,help="Reverse the order of the listing sort.")

    def check_opts(self,opts,cmdline):

        if not opts.user:
            raise MissingOptionError("CPTAC portal username must be specified")

        self.get_password(opts,cmdline)

        setattr(opts,'human',True)

    def listurl(self):
        return 'https://%s:%s@%s/aspera/user/'%(self.opts.user,self.opts.password,self.server())

    def login(self):
        pass

    def convertdate(self,s):
        return datetime.datetime.strptime(s, "%b %d, %Y %H:%M:%S %p")
    
    def getlisting(self,path=None):

        listPath = self.normalize(path)
        thelisturl = self.listurl()
        if listPath != "/":
            thelisturl += '?B='+quote_plus(listPath,)

        try:
            buffer = self.urlread(thelisturl)
        except NotFound:
            raise PortalPathNotFound(listPath)

        upload_details = None
        current_item = None
        rows = []
        for i,l in enumerate(buffer.splitlines()):

            if 'icon_download_file.png' in l:
                m = re.search(r' data-fasp-url="([^"]*)"',l)
                current_item = self.extract_fasp(m.group(1))
                current_item.update({'isFolder': False, 'lineno': i})
                continue

            if 'icon_download_folder.png' in l:
                m = re.search(r' data-fasp-url="([^"]*)"',l)
                current_item = self.extract_fasp(m.group(1))
                current_item.update({'isFolder': True, 'lineno': i})
                continue

            if '"Upload"' in l:
                m = re.search(r' data-fasp-url="([^"]*)"',l)
                assert m
                upload_details = self.extract_fasp(m.group(1))
                current_item = None
                continue

            if current_item == None:
                continue

            if i == (current_item['lineno'] + 2):
                m = re.search(r'>(.*)<',l)
                sizestr = m.group(1)
                current_item['sizeAndUnit'] = sizestr
                continue

            if i == (current_item['lineno'] + 3):
                m = re.search(r'<span>([^<]*)</span><',l)
                date = m.group(1)
                current_item['date'] = date
                rows.append(current_item)
                continue

        listing = {}
        for r in rows:
            d = dict(list(r.items()))
            if d.get('sizeAndUnit'):
                d['size'],d['sizeAndUnit'] = self.convertsize(d['sizeAndUnit'])
            else:
                d['size'],d['sizeAndUnit'] = 0,"-"
            d['date'] = self.convertdate(d['date'])
            d['namefolder'] = d['name']
            if r['isFolder']:
                d['namefolder'] += '/'
            d['userId'] = "-"
            d['fullpath'] = self.join(listPath,d['name'])
            d['fileName'] = d['name']
            listing[d['fileName']] = d

        return self.clean_listing(folder=listPath,upload=upload_details,files=listing)

class SessionOpenerError(RuntimeError):
    pass

class LoginError(SessionOpenerError):
    pass

class GotCookie(SessionOpenerError):
    pass

class NotFound(SessionOpenerError):
    pass

class URLMoved(SessionOpenerError):
    pass

class SessionOpener(URLopener):

    def __init__(self,version):
        URLopener.__init__(self)
        self.version = version

    def getcookie(self,headers):
        if 'set-cookie' in headers:
            cookie = Cookie.SimpleCookie(headers['Set-Cookie'])
            if "JSESSIONID" in cookie:
                thecookie = cookie["JSESSIONID"].OutputString()
                return thecookie
        return None

    def http_error_302(self, url, fp, errcode, errmsg, headers, data=None):
        jsessionid = self.getcookie(headers)
        if jsessionid:
            raise GotCookie(jsessionid)
        raise LoginError()

    def http_error_403(self, url, fp, errcode, errmsg, headers, data=None):
        raise LoginError()

    def http_error_404(self, url, fp, errcode, errmsg, headers, data=None):
        raise NotFound(url)

    def http_error_301(self, url, fp, errcode, errmsg, headers, data=None):
        raise URLMoved(headers['Location'])

    def http_error_default(self, url, fp, errcode, errmsg, headers, data=None):
        raise IOError("Unhandled HTTP Error: %s (%s)"%(errmsg,errcode))

    def setheader(self,key,value):
        for i in range(len(self.addheaders)-1,-1,-1):
            if self.addheaders[i][0] == key:
                del self.addheaders[i]
        self.addheader(key,value)

#### Exceptions!

class CPTACPortalError(RuntimeError):
    format = "%s"
    def __init__(self,*args):
        super(CPTACPortalError,self).__init__(self.format%args)

class ConnectionErrorExtra(CPTACPortalError):
    format = "Can't connect: %s\n  %s"

class ConnectionError(CPTACPortalError):
    format = "Can't connect: %s"

class ServerError(CPTACPortalError):
    format = "Server error for URL: %s (%s)"

class PasswordRequired(CPTACPortalError):
    format = "Portal password required"

class PermissionDenied(CPTACPortalError):
    format = "Portal permission denied for URL: %s"

class PortalFolderNotFound(CPTACPortalError):
    format = "Portal folder does not exist: %s"

class PortalPathNotFound(CPTACPortalError):
    format = "Portal path does not exist: %s"

class PortalPathAmbiguous(CPTACPortalError):
    format = "Portal path with wildcards resolves to multiple paths: %s"

class LocalFileExists(CPTACPortalError):
    format = "Local file exists: %s"

class PortalPathExists(CPTACPortalError):
    format = "Portal path exists: %s"

class ASCPExecuteError(CPTACPortalError):
    format = "Aspera ascp execution failed, exit code: %s"

class BadCommand(CPTACPortalError):
    format = "Portal command not supported: %s"

class CommandArgumentError(CPTACPortalError):
    pass

class MissingOptionError(CPTACPortalError):
    format = "%s"

class BadJSONListing(CPTACPortalError):
    format = "CPTAC portal JSON listing web-service returned invalid/incomplete JSON data"

class AsperaExecuteError(CPTACPortalError):
    format = "Aspera command failed with exit code: %s"

def cptac_portals():
    for cls in filter(inspect.isclass,list(globals().values())):
        if not hasattr(cls,'portal'):
            continue
        yield cls

def alltags():
    tags = {}
    for cls in cptac_portals():
        name = cls.__name__
        tags[name] = cls.tags
    return tags

def cptac_portal(tag,*args,**kwargs):
    for cls in cptac_portals():
        if tag in cls.tags:
            try:
                return cls(*args,**kwargs)
            except CPTACPortalError as e:
                print(e.args[0])
                sys.exit(1)
    raise BadPortalTag(tag)

class BadPortalTag(CPTACPortalError):
    format = "Bad portal argument: %s" + "\n\nValid Portal Tags:\n   " + "\n   ".join(map(lambda t: "%s: %s"%(t[0],", ".join(t[1])),sorted(alltags().items())))

class MissingPortalTag(CPTACPortalError):
    format = "Portal tag command-line argument missing" + "\n\nValid Portal Tags:\n   " + "\n   ".join(map(lambda t: "%s: %s."%(t[0],", ".join(t[1])),sorted(alltags().items())))


if __name__ == '__main__':

    match = False
    try:
        tag = os.path.split(sys.argv[0])[1].rsplit('.',1)[0]
        cptac_portal(tag,cmdline=True)
        match = True
    except BadPortalTag:
        pass

    if not match:
        try:
            tag = sys.argv.pop(1)
            cptac_portal(tag,cmdline=True)
        except IndexError as e:
            raise MissingPortalTag()
