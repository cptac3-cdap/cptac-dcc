#!/bin/sh
VER=`python3 cksum.py --version | tr -d -c '0-9.'`
DCCVER="CPTAC-DCC Tools v$VER"
PORVER="CPTAC Portal Tools v$VER"
ulbin.sh
ulbin_public.sh
ulsrc.sh
ulsrc_public.sh
gh release create "$DCCVER" dist/cptacdcc-$VER.*.tgz
gh release create "$PORVER" dist/cptacpublic-$VER.*.tgz
