#!/bin/sh
VER=`${PYTHON:-python} cksum.py --version | tr -d -c '0-9.'`
XX="src"
mkdir -p build dist
${PYTHON:-python} ./tosrc.py build/cptacdcc-${VER}.${XX} cptacdcc.py cksum.py cptacpublic.py cptactransfer.py cptacportal.py
mv build/cptacdcc-${VER}.${XX}.tgz dist
