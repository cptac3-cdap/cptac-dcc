#!/bin/sh
VER=`python3 cksum.py --version | tr -d -c '0-9.'`
OS=`uname`
AR=`uname -m`
XX="linux-$AR"
mkdir -p build dist
./tobin.py build/cptacdcc-${VER}.${XX} cptacdcc.py cksum.py cptacpublic.py cptactransfer.py cptacportal.py
mv build/cptacdcc-${VER}.${XX}.tgz dist

