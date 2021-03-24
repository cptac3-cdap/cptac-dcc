#!/bin/sh

set -x
TOOL=cptacdcc

OWD=`pwd`
mkdir -p testing.$$
cp $TOOL.ini testing.$$
cd testing.$$

BASE=`dirname $0`/../..
PROG=$BASE/$TOOL
WORKFOLDER=scripttesting
TMPFILE1=temp1
TMPFILE2=temp2
TMPFILE3=temp3

dd bs=1M count=1 < /dev/urandom > $TMPFILE1
dd bs=1M count=1 < /dev/urandom > $TMPFILE2
dd bs=1M count=1 < /dev/urandom > $TMPFILE3
$PROG -v
$PROG /
$PROG mkdir $WORKFOLDER
$PROG $WORKFOLDER
$PROG put $TMPFILE1 $WORKFOLDER
$PROG $WORKFOLDER
$PROG put temp* $WORKFOLDER
$PROG $WORKFOLDER
$PROG put $TMPFILE1 $WORKFOLDER
$PROG $WORKFOLDER
$PROG put temp* $WORKFOLDER
$PROG $WORKFOLDER
$PROG put -f $TMPFILE1 $WORKFOLDER
$PROG $WORKFOLDER
$PROG put -f temp* $WORKFOLDER
$PROG $WORKFOLDER
$PROG put -f "temp*" $WORKFOLDER
$PROG $WORKFOLDER
$PROG get $WORKFOLDER
ls -lR 
$PROG get $WORKFOLDER
ls -lR 
$PROG get -f $WORKFOLDER
ls -lR 
rm -rf $WORKFOLDER
rm -f temp*
$PROG get $WORKFOLDER/$TMPFILE1
ls -lR 
$PROG get "$WORKFOLDER/temp*"
ls -lR 
$PROG get $WORKFOLDER/$TMPFILE1
ls -lR 
$PROG get "$WORKFOLDER/temp*"
ls -lR 
$PROG get -f $WORKFOLDER/$TMPFILE1
ls -lR 
$PROG get -f "$WORKFOLDER/temp*"
ls -lR 
$PROG $WORKFOLDER
$PROG delete $WORKFOLDER/$TMPFILE1
$PROG $WORKFOLDER
$PROG delete "$WORKFOLDER/temp*"
$PROG $WORKFOLDER
$PROG delete $WORKFOLDER
$PROG $WORKFOLDER
$PROG

cd $OWD
\rm -rf testing.*
