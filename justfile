set shell := [ "docker", "compose", "run", "--rm", "web", "bash", "-c" ]

manage *args="":
    ./manage.py {{args}}

test *args="":
    ./manage.py test {{args}}
venv:
    rm -Rf myproject.egg-info
    rm -Rf .venv
    uv venv .venv

sync:
    uv sync --all-extras

lock:
    uv lock --upgrade

init: venv sync
    rm -f db.sqlite3
    ./manage.py migrate
    ./manage.py createsuperuser --username $(whoami) --email swing+localsetup@liip.ch --no-input
    ./manage.py collectstatic --no-input

changepassword:
    ./manage.py changepassword $(whoami)

start:
    ./manage.py runserver

logs:
    #!/bin/env bash
    docker compose logs -f web

bash:
   bash

lint:
    ruff format
    ruff check --fix

sprites:
    core/sprites/all-gen.sh
    # ./manage collectstatic

translate:
    ./manage.py makemessages --all
    ./manage.py compilemessages

fixturize:
    ./manage.py fixturize
fixtures: fixturize

uv *args="":
    uv {{args}}