#!/usr/bin/env bash
set -e
source bin/db-rclone-common.sh

FORCE=0

if [ "$1" == "-f" ]; then
	FORCE=1
fi

if [ ! -f $FILENAME ]; then
	echo "File $FILENAME doesn't exists";
	exit 1
fi

set -x
exists=$(rclone -v lsf membershipmanager:${BUCKET_NAME}/${FILENAME})
echo $exists
if [ ! "$exists" = "" ] && [ $FORCE -eq 0 ]; then
 echo "file already exists, use -f"
 exit 1
fi
rclone -v copy $FILENAME membershipmanager:${BUCKET_NAME}/$(dirname $FILENAME)

