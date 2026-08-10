export BACKEND_CONTAINER := "web"

set positional-arguments

default:
    just --list

# Run bash in the backend container
bash:
    docker compose exec {{ BACKEND_CONTAINER }} bash

alias django := manage
alias dj := manage
# Run a Django manage.py command
manage *args:
    docker compose exec {{ BACKEND_CONTAINER }} ./manage.py "$@"

alias t := test
# Run the tests suite
test *args:
    docker compose exec {{ BACKEND_CONTAINER }} ./manage.py test "$@"

# Create the virtual environment with uv
venv:
    docker compose run --rm {{ BACKEND_CONTAINER }} rm -Rf myproject.egg-info
    docker compose run --rm {{ BACKEND_CONTAINER }} rm -Rf .venv
    docker compose run --rm {{ BACKEND_CONTAINER }} uv venv .venv

# Install all dependencies (including dev extras) with uv
sync:
    docker compose run --rm {{ BACKEND_CONTAINER }} uv sync --all-extras

# Update the uv.lock file
lock:
    docker compose run --rm {{ BACKEND_CONTAINER }} uv lock --upgrade

# Full setup: venv + sync + migrate + superuser + collectstatic
init: venv sync
    docker compose run --rm {{ BACKEND_CONTAINER }} rm -f db.sqlite3
    docker compose run --rm {{ BACKEND_CONTAINER }} ./manage.py migrate
    docker compose run --rm {{ BACKEND_CONTAINER }} bash -c './manage.py createsuperuser --username $(whoami) --email swing+localsetup@liip.ch --no-input'
    docker compose run --rm {{ BACKEND_CONTAINER }} ./manage.py collectstatic --no-input

# Change the superuser password
changepassword:
    docker compose exec {{ BACKEND_CONTAINER }} bash -c './manage.py changepassword $(whoami)'

# Run the development server
start *args:
    docker compose up "$@"

# Follow the backend container logs
logs:
    docker compose logs -f {{ BACKEND_CONTAINER }}

alias validate := lint
alias l := lint
# Format and lint the code
lint:
    docker compose exec {{ BACKEND_CONTAINER }} ruff format
    docker compose exec {{ BACKEND_CONTAINER }} ruff check --fix

alias format := fix
# Fix styling offenses
fix *args:
    docker compose exec {{ BACKEND_CONTAINER }} ruff format "$@"
    docker compose exec {{ BACKEND_CONTAINER }} ruff check --fix "$@"

# Generate the sprites
sprites:
    docker compose exec {{ BACKEND_CONTAINER }} core/sprites/all-gen.sh

alias messages := translate
# Make messages and compile them
translate:
    docker compose exec {{ BACKEND_CONTAINER }} ./manage.py makemessages --all
    docker compose exec {{ BACKEND_CONTAINER }} ./manage.py compilemessages

alias f := fixturize
alias fixtures := fixturize
# Reset the database and load the fixtures
fixturize *args:
    docker compose exec {{ BACKEND_CONTAINER }} ./manage.py fixturize "$@"

# Run a uv command
uv *args:
    docker compose exec {{ BACKEND_CONTAINER }} uv "$@"
