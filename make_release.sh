#!/bin/sh
set -x
VER=`python3 cksum.py --version | tr -d -c '0-9.'`
DCCVER="CPTAC-DCC-Tools-v$VER"
./ulbin.sh
./ulsrc.sh
rm -f dist/cptacdcc-$VER.txt
( cd dist; md5sum cptacdcc-$VER.*.tgz > cptacdcc-$VER.md5 ; touch cptacdcc-$VER.txt )
if [ "$1" ]; then 
  for comment in "$@"; do 
    echo "* $comment" >> dist/cptacdcc-$VER.txt
    # echo "* $comment" >> dist/cptacpublic-$VER.txt
  done
fi
gh release delete "$DCCVER" -y
git push --delete origin "refs/tags/$DCCVER"
git tag --delete "$DCCVER"
gh release create "$DCCVER" dist/cptacdcc-$VER.*.tgz dist/cptacdcc-$VER.md5 -F dist/cptacdcc-$VER.txt -t "$DCCVER"
for a in dist/cptacdcc-$VER.*.tgz; do
  a1=`basename $a`
  rclone copyto $a cptac-s3:cptac-cdap.georgetown.edu/$a1
  b1=`echo $a1 | sed "s/-$VER//"`
  aws --profile cptac s3api put-object --bucket cptac-cdap.georgetown.edu --key "$b1" --website-redirect-location "/$a1"
done
