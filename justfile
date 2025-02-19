set shell := [ "docker", "compose", "run", "--rm", "web", "bash", "-c" ]

manage *args="":
    ./manage.py {{args}}

venv:
    rm -Rf myproject.egg-info
    rm -Rf .venv
    mkdir -p .venv
    python -m venv .venv
    pip install --upgrade pip
    pip install pip-tools

requirements-install:
    pip install -r requirements.txt
    pip install -r requirements.dev.txt

requirements-generate:
    set -x
    pip-compile pyproject.toml -v
    pip-compile pyproject.toml -v --all-extras -o requirements.dev.txt

init: venv requirements-install
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
    myapp/sprites/all-gen.sh
    # ./manage collectstatic

translate:
    ./manage.py makemessages --all
    ./manage.py compilemessages
