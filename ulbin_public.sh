#!/bin/sh
VER=`python3 cksum.py --version | tr -d -c '0-9.'`
OS=`uname`
AR=`uname -m`
XX="linux-$AR"
mkdir -p build dist
./tobin.py build/cptacpublic-${VER}.${XX} cptacpublic.py cksum.py packageraw.py unpackraw.py
mv build/cptacpublic-${VER}.${XX}.tgz dist

