# Subscription manager

Based on [symfony-docker](https://github.com/dunglas/symfony-docker/)

Goal is just to have a modern PHP/Symfony/Docker playground.

What is implemented:
- CRUD For Subscriptions
- CRUD For Members
- You can assign members to subscriptions

## Roadmap
- Tests & Pipeline
- Generate Bill for each subscription (with a reference)
- Generate a PDF for billing using `camt` and a `qrcode`
- Be able to sync the data with the bank account to know who did not pay by uploading a csv file.
- Dashboard about each payment status and due payment
- Action to generate a bill reminder (New Facture)
- Group of user (parent), so one user pay the subscription and the "children" don't have to.

## Getting Started

1. If not already done, [install Docker Compose](https://docs.docker.com/compose/install/) (v2.10+)
2. Run `docker compose build --pull --no-cache` to build fresh images
3. Choose the configuration you need:
    - For traefik `cp docker-compose.override.traefik.yml docker-compose.override.yml`
    - For localhost `cp docker-compose.override.linux.yml docker-compose.override.yml`
3. Run `docker compose up` (the logs will be displayed in the current shell)
4. Create the database `docker-compose exec php bin/console doctrine:schema:create`
5. Import the fixtues `docker-compose exec php bin/console doctrine:fixtures:load`
5. Open <https://vanil.docker.test> (traefik) or <https://localhost:44333> (localhost) in your favorite web browser and [accept the auto-generated TLS certificate](https://stackoverflow.com/a/15076602/1352334)
6. Run `docker compose down --remove-orphans` to stop the Docker containers.

## Fixtures

Load fixtures:
> docker-compose exec php bin/console doctrine:fixtures:load -n

## Code style
> docker-compose exec php composer run-script phpcs
