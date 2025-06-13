#!/usr/bin/env bash
set -e


SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd $SCRIPT_DIR
cd ..

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

DB_DIR=$(dirname $FILENAME)
TEMP_FILE=$(basename $FILENAME)
DESTINATION_NAME=${DESTINATION_NAME:-${TEMP_FILE}}
set -xv
rclone -v copyto $FILENAME membershipmanager:${BUCKET_NAME}/${DB_DIR}/${DESTINATION_NAME}

