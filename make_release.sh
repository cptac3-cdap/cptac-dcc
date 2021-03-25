#!/bin/sh
set -x
VER=`python3 cksum.py --version | tr -d -c '0-9.'`
DCCVER="CPTAC-DCC-Tools-v$VER"
PUBVER="CPTAC-Portal-Tools-v$VER"
./ulbin.sh
./ulbin_public.sh
./ulsrc.sh
./ulsrc_public.sh
( cd dist; md5sum cptacdcc-$VER.*.tgz > cptacdcc-$VER.md5 )
( cd dist; md5sum cptacpublic-$VER.*.tgz > cptacpublic-$VER.md5 )
gh release create -F dist/cptacdcc-$VER.txt "$DCCVER" dist/cptacdcc-$VER.*.tgz dist/cptacdcc-$VER.md5
gh release create -F dist/cptacpublic-$VER.txt "$PUBVER" dist/cptacpublic-$VER.*.tgz dist/cptacpublic-$VER.md5
