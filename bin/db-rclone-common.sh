#!/usr/bin/env bash
set -e

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd $SCRIPT_DIR
cd ..


if [ -f .env.local ]; then
	source .env.local
fi

if [ -z $ACCESS_KEY_ID ]; then
	echo "Please set ACCESS_KEY_ID"
	exit 1
fi
if [ -z $SECRET_ACCESS_KEY ]; then
	echo "Please set SECRET_ACCESS_KEY"
	exit 1
fi

if [ "$#" -ne 0 ] && ( [ "$1" == 'dev' ] ||  [ "$1" == 'prod' ] ) ; then
	DB_ENV=$1
	shift
fi

export RCLONE_CONFIG_MEMBERSHIPMANAGER_TYPE=${RCLONE_CONFIG_MEMBERSHIPMANAGER_TYPE:-s3}
export RCLONE_CONFIG_MEMBERSHIPMANAGER_ENDPOINT=${RCLONE_CONFIG_MEMBERSHIPMANAGER_ENDPOINT:-sos-ch-gva-2.exo.io}
export RCLONE_CONFIG_MEMBERSHIPMANAGER_PROVIDER=${RCLONE_CONFIG_MEMBERSHIPMANAGER_PROVIDER:-Other}
export RCLONE_CONFIG_MEMBERSHIPMANAGER_REGION=${RCLONE_CONFIG_MEMBERSHIPMANAGER_REGION:-ch-gva-2}
export RCLONE_CONFIG_MEMBERSHIPMANAGER_ACL=${RCLONE_CONFIG_MEMBERSHIPMANAGER_ACL:-private}
export RCLONE_CONFIG_MEMBERSHIPMANAGER_ACCESS_KEY_ID=$ACCESS_KEY_ID
export RCLONE_CONFIG_MEMBERSHIPMANAGER_SECRET_ACCESS_KEY=$SECRET_ACCESS_KEY
export BUCKET_NAME=${BUCKET_NAME:-vanil-association}
export DB_ENV=${DB_ENV:-dev}
export FILENAME=${FILENAME:-db/${DB_ENV}.sqlite}

echo "Using env ${DB_ENV}, accepted: prod/dev"
