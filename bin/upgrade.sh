#!/bin/bash
set -e

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd $SCRIPT_DIR
cd ..

git pull
docker compose pull
docker compose up -d --build
docker compose exec web python3 manage.py migrate

source .env.local
UPGRADE_MOUNTED_VOLUME=${UPGRADE_MOUNTED_VOLUME:-0}

echo $APP_DEBUG
if [ "$UPGRADE_MOUNTED_VOLUME" = "true" ] || [ "$UPGRADE_MOUNTED_VOLUME" = "1" ]; then
  echo "Running upgrades for mounted volume"
  docker compose exec web python3 manage.py compilemessages
  docker compose exec web python3 manage.py collectstatic --noinput
  docker compose up -d
fi


