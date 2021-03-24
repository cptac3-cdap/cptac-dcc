#!/bin/sh
DIR=`dirname $0`
RCLONE="$DIR/rclone/rclone"
CONFIGFILE=".rclone.conf"
REMOTE="$1"
FULLPATH="$2"
CONFIG="$3"

if [ "$CONFIG" = "" ]; then
  for d in . .. ./cptac-galaxy ../cptac-galaxy $HOME /home/galaxy /home/ubuntu/cptac-galaxy; do
    if [ -f "$d/$CONFIGFILE" ]; then
      CONFIG="$d/$CONFIGFILE"
      break
    fi
  done
fi

if [ "$CONFIG" = "" ]; then
  echo "Can't find rclone configuration" 1>&2 
  exit 1;
fi

TMPFILE=`mktemp --tmpdir=. .rclone.XXXXXXXXXX` || exit 1
cp -f "$CONFIG" "$TMPFILE"

# Execute rclone with this configuration
$RCLONE --config "$TMPFILE" copy "$REMOTE:$FULLPATH" .

if [ -f "$TMPFILE" ]; then
  rm -f "$TMPFILE"
fi
