#!/bin/sh
VER=`${PYTHON:-python} cksum.py --version | tr -d -c '0-9.'`
XX="src"
mkdir -p build dist
${PYTHON:-python} ./tosrc.py build/cptacpublic-${VER}.${XX} cksum.py cptacpublic.py
mv build/cptacpublic-${VER}.${XX}.tgz dist
