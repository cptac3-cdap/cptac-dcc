#!/bin/sh
set -x
VER=`python3 cksum.py --version | tr -d -c '0-9.'`
DCCVER="CPTAC-DCC-Tools-v$VER"
PORVER="CPTAC Portal Tools v$VER"
./ulbin.sh
./ulbin_public.sh
./ulsrc.sh
./ulsrc_public.sh
md5sum dist/cptacdcc-$VER.*.tgz > dist/cptacdcc-$VER.md5
md5sum dist/cptacpublic-$VER.*.tgz > dist/cptacpublic-$VER.md5
gh release create -F dist/cptacdcc-$VER.txt "$DCCVER" dist/cptacdcc-$VER.*.tgz dist/cptacdcc-$VER.md5
gh release create -F dist/cptacpublic-$VER.txt "$DCCVER" dist/cptacpublic-$VER.*.tgz dist/cptacpublic-$VER.md5
