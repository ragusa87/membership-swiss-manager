#!/bin/bash
if [ "$INITIAL" = "1" ]; then
    # Wait for the db server to be ready, then run the migrate command
    while ! (echo > /dev/tcp/db/5432) >/dev/null 2>&1; do echo -n '.'; sleep 1; done;
    echo "Running migrations..."
    ./manage.py migrate
    echo "Compiling messages..."
    ./manage.py compilemessages
    echo "Install static assets..."
    ./manage.py collectstatic --no-input
fi

exec "${@}"
