#!/bin/sh

set -x
TOOL="cptacpublic.sh --accept"

OWD=`pwd`
mkdir -p testing.$$
cp cptacpublic.ini testing.$$
cd testing.$$

BASE=`dirname $0`/../..
PROG=$BASE/$TOOL
TEST="Phase_I_Data/Study1/XCT@90/LCMS_XCT+_1B_315.mzML"
TEST1="Phase_I_Data/Study1/XCT@90/*.mzML"

$PROG -v
$PROG /
$PROG get $TEST
ls -l
$PROG get $TEST
ls -l
$PROG get -f $TEST
ls -l
$PROG get -f "$TEST1"
ls -l

cd $OWD
\rm -rf testing.*
