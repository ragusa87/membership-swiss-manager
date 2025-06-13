#!/usr/bin/env bash
set -e

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd $SCRIPT_DIR
cd ..

source bin/db-rclone-common.sh


DB_NAME=${DB_NAME:-prod}
DESTINATION_NAME=${DB_ENV}-$(date +%Y%m%d_%H%M%S).sqlite ./bin/db-rclone-upload.sh -f