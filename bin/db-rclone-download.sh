#!/usr/bin/env bash
set -e
source bin/db-rclone-common.sh

if [ -f $FILENAME ]; then
	echo "File $FILENAME already exists";
	exit 1
fi

rclone -v copy membershipmanager:${BUCKET_NAME}/${FILENAME} $(dirname ${FILENAME})
