#!/bin/sh
VER="$1"
if [ "$VER" != "" ]; then
   VER="-$VER"
fi
DIR=`dirname "$0"`
cd $DIR
URL=https://edwardslab.bmcb.georgetown.edu/software/downloads/CPTAC-DCC
OS=`uname -o`
AR=`uname -m`
case $OS in
  Cygwin) MACH="win32"; EXT=".zip"; EXE=".exe";;
       *) MACH="linux-$AR"; EXT=".tgz"; EXE=".sh";;
esac
if [ -f ./cptacdcc.py ]; then
    MACH="src"; EXT=".tgz"; EXE=".py"
fi
ZIP=cptacdcc$VER.$MACH$EXT
rm -f $ZIP
# Assume wget and unzip/tar are on the path...
wget --no-check-certificate $URL/$ZIP
if [ "$EXT" = ".zip" ]; then
    unzip -o -d .. $ZIP
else
    tar -C .. -xvzf $ZIP
fi
./cptacdcc$EXE --version
rm -f $ZIP
