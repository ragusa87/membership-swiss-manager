#!/usr/bin/env bash
set -e
source bin/db-rclone-common.sh

FORCE=0
if [[ "$1" == "-f" ]]; then
 FORCE=1
fi

if [ -f $FILENAME ] && [ $FORCE -eq 0 ]; then
	echo "File $FILENAME already exists";
	exit 1
fi

rclone -v copy membershipmanager:${BUCKET_NAME}/${FILENAME} $(dirname ${FILENAME})

echo ${FILENAME};
