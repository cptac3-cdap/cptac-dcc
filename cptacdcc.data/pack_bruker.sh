#!/bin/sh

#    Package and compute checksums for Bruker MS data
#    Assumes the following structure:
#
#    01AS/
#       01AS_F1.d/
#          ...
#       01AS_F2.d/
#          ...
#       01AS_F3.d/
#          ...
#    02AS/
#       02AS_F1.d/
#          ...
#       02AS_F2.d/
#          ...
#       02AS_F3.d/
#          ...
#
#    Should be run from the folder with the analytical sample directories (01AS, 02AS)
#

DIR=`dirname $0`
DIR=`readlink -f "$DIR"`

echo "> rm -rf packaged"
rm -rf packaged
echo "> cksum.sh --force */*.d"
$DIR/cksum.sh --force */*.d
echo "> packageraw.sh -r d -d packaged -v"
$DIR/packageraw.sh -r d -d packaged -v
echo "> cksum.sh packaged/*"
$DIR/cksum.sh packaged/*
