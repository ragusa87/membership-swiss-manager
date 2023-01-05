#!/usr/bin/env bash
set -e
source bin/db-rclone-common.sh

if [ -d $(dirname ${FILENAME}) ]; then
	echo "Directory$(dirname ${FILENAME}) already exists, remove it first";
	exit 1;
fi

mkdir -p db

set -x
rclone mount --vfs-cache-mode minimal membershipmanager:${BUCKET_NAME}/$(dirname ${FILENAME}) $(dirname ${FILENAME})
