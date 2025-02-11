#!/bin/bash
if [ ! -e "$VIRTUAL_ENV/bin" ] || [ ! -e "$VIRTUAL_ENV/bin/python" ]; then
    echo "Creating virtualenv at \"$VIRTUAL_ENV\""
    ls -la $VIRTUAL_ENV
    python -m venv "$VIRTUAL_ENV"
fi

if [ "$INITIAL" = "1" ]; then
    REQUIREMENT_FILE=${$REQUIREMENT_FILE:-"requirements.txt"}
    if [ ! -e $REQUIREMENT_FILE ]; then
        >&2  echo "Please create $REQUIREMENT_FILE"
        exit
    fi

    pip install -r requirements.txt

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
