#!/bin/sh
set -x
VER=`python3 cksum.py --version | tr -d -c '0-9.'`
DCCVER="CPTAC-DCC-Tools-v$VER"
PUBVER="CPTAC-Portal-Tools-v$VER"
./ulbin.sh
./ulbin_public.sh
./ulsrc.sh
./ulsrc_public.sh
rm -f dist/cptacdcc-$VER.txt dist/cptacpublic-$VER.txt
( cd dist; md5sum cptacdcc-$VER.*.tgz > cptacdcc-$VER.md5 ; touch cptacdcc-$VER.txt )
( cd dist; md5sum cptacpublic-$VER.*.tgz > cptacpublic-$VER.md5 ; touch cptacpublic-$VER.txt )
if [ "$1" ]; then 
  for comment in "$@"; do 
    echo "* $comment" >> dist/cptacdcc-$VER.txt
    echo "* $comment" >> dist/cptacpublic-$VER.txt
  done
fi
gh release create "$DCCVER" dist/cptacdcc-$VER.*.tgz dist/cptacdcc-$VER.md5 -F dist/cptacdcc-$VER.txt -t "$DCCVER"
gh release create "$PUBVER" dist/cptacpublic-$VER.*.tgz dist/cptacpublic-$VER.md5 -F dist/cptacpublic-$VER.txt -t "$PUBVER"
for a in dist/cptacdcc-$VER.*.tgz dist/cptacpublic-$VER.*.tgz; do
  a1=`basename $a`
  rclone copyto $a cptac-s3:cptac-cdap.georgetown.edu/$a1
  b1=`echo $a1 | sed "s/-$VER//"`
  aws --profile cptac s3api put-object --bucket cptac-cdap.georgetown.edu --key "$b1" --website-redirect-location "/$a1"
done
