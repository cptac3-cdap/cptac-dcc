#!/bin/sh
DIR=`dirname $0`
DIR=`readlink -f "$DIR"`
PROG=`basename $0 .sh`
if [ -f "$DIR/$PROG.py" ]; then
  exec python3 "$DIR/$PROG.py" "$@"
else
  LD_LIBRARY_PATH=":${LD_LIBRARY_PATH}:$DIR/lib64:$DIR/lib32"
  export LD_LIBRARY_PATH
  exec "$DIR/$PROG" "$@"
fi
