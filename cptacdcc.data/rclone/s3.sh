#!/bin/sh
DIR=`dirname $0`
RCLONE="$DIR/rclone/rclone"
CONFIG=`mktemp .rclone.XXXXXXXXXX` || exit 1
CONFIGFILE1=".galaxy.ini"
CONFIGFILE2=".aws/config"
FULLPATH="$1"
AWSCONFIG="$2"

if [ "$AWSCONFIG" = "" ]; then
  for d in ./cptac-galaxy ../cptac-galaxy; do
    if [ -f "$d/$CONFIGFILE1" ]; then
      AWSCONFIG="$d/$CONFIGFILE1"
      break
    fi
  done
fi

if [ "$AWSCONFIG" = "" ]; then
  for d in . .. $HOME /home/galaxy $HOME; do
    if [ -f "$d/$CONFIGFILE2" ]; then
      AWSCONFIG="$d/$CONFIGFILE2"
      break
    fi
  done
fi

if [ "$AWSCONFIG" = "" ]; then
  echo "Can't find AWS configuration" 1>&2 
  exit 1;
fi

ACCESS_KEY=`egrep '^ *(aws_access_key_id|aws_access_key) *=' $AWSCONFIG | sed -e 's/^[^=]*=//' -e 's/^  *//' -e 's/  *$//'`
SECRET_KEY=`egrep '^ *(aws_secret_access_key|aws_secret_key) *=' $AWSCONFIG | sed -e 's/^[^=]*=//' -e 's/^  *//' -e 's/  *$//'`

# ACCESS_KEY=`awk -v K="aws_access_key_id" '$1 == K {print $3}' $AWSCONFIG | head -n 1`
# SECRET_KEY=`awk -v K="aws_secret_access_key" '$1 == K {print $3}' $AWSCONFIG | head -n 1`

# Create the config file
cat >>"$CONFIG" <<EOF
[s3]
type = s3
env_auth = false
access_key_id = $ACCESS_KEY
secret_access_key = $SECRET_KEY
region = 
endpoint = 
location_constraint = 
server_side_encryption =
EOF

# Execute rclone with this configuration
$RCLONE --config "$CONFIG" copy "s3:$FULLPATH" .

if [ -f "$CONFIG" ]; then
    rm -f "$CONFIG"
fi
