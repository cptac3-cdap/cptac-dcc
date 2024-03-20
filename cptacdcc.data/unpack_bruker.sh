#!/bin/sh

#    Check checksums and unpack Bruker MS data
#    Assumes the following structure:
#
#    01AS/
#       01AS_F1.d.zip
#       01AS_F2.d.zip
#       01AS_F3.d.zip
#    01AS.cksum
#    02AS/
#       02AS_F1.d.zip
#       02AS_F2.d.zip
#       02AS_F3.d.zip
#    02AS.cksum
#
#    Should be run from the folder with the analytical sample directories (01AS, 02AS)
#

DIR=`dirname $0`
DIR=`readlink -f "$DIR"`

echo "> cksum.sh -q -V *.cksum"
$DIR/cksum.sh -q -V *.cksum
if [ $? -ne 0 ]; then
  echo "Bad checksums! Will not unpack Bruker files" 1>&2
  exit 1
fi
echo "> unpackraw.sh -r d -R -v"
$DIR/unpackraw.sh -r d -R -v
