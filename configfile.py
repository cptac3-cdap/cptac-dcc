
import os, os.path, sys

try:
    from configparser import SafeConfigParser
except ImportError:
    from ConfigParser import SafeConfigParser

def readconfig(prog, verbose=False):
  d,p = os.path.split(prog)
  d = os.path.realpath(os.path.abspath(d))
  name = p.rsplit('.',1)[0]
  iniFileName = name+'.ini'
  siteIniFileName = name+'-local.ini'
  cfg = SafeConfigParser()
  cfg.optionxform = str
  iniFile = open(os.path.join(d,iniFileName))
  cfg.readfp(iniFile)
  iniFile.close()
  readfiles = [ os.path.join(d,iniFileName) ]
  readfiles.extend(
      cfg.read([iniFileName,                            # current working directory
                os.path.join(d,siteIniFileName),        # install dir (site ini)
                os.path.expanduser('~'+os.sep+iniFileName),     # home dir
                os.path.expanduser('~'+os.sep+'.'+iniFileName), # home dir (dotfile)
               ]))
  if verbose:
     print("  " + "\n  ".join(map(os.path.realpath,list(map(os.path.abspath,readfiles)))))
  return cfg

def get(cfg, section, key, default=None):
   if cfg.has_section(section) and cfg.has_option(section, key):
       return cfg.get(section,key)
   return default

def getboolean(cfg, section, key, default=None):
   if cfg.has_section(section) and cfg.has_option(section, key):
       return cfg.getboolean(section,key)
   return default
