# Subscription manager

Based on [symfony-docker](https://github.com/dunglas/symfony-docker/)

Goal is just to have a modern PHP/Symfony/Docker playground.

The database is sqlite. But you can use something else as Doctrine is used.

# Entities
- Subscription (Like 2022,2023 etc)
- Member (Like John Doe)
  - Member have hierarchy (children/parent), so only a single "Family" must pay the subscription.
- MemberSubscription (Like John Doe is subscribed to 2023 as a full member)
- Invoice (Linked to MemberSubscription, so a member need to pay the subscription)
  - The invoice's creditor is injected as environment variable.
  - The invoice's debitor is based on the member information.
  - The invoice's id is used as the QRCode reference.

## Features

What is implemented:
- CRUD For Subscriptions
- CRUD For Members
- CRUD For MemberSubscription
- Dashboard to review the MemberSubscription and Invoices for a given year
- Action to generate all invoices for a given subscription
- Action to batch export invoices as PDF
- Tests & Pipeline
- Import member list from xlsx via cli

### Roadmap

- Be able to sync the data with the bank account to know who did not pay by uploading a csv file.
- Better translations
- Test invoice generation (Create invoice and reminders automatically)
- UX to import member list via Xlsx (only available in cli currently)


## Getting Started

1. If not already done, [install Docker Compose](https://docs.docker.com/compose/install/) (v2.10+)
2. Run `mkdir -p var db`
2. Run `docker compose build --pull --no-cache` to build fresh images
3. Choose the configuration you need:
    - For traefik `cp docker-compose.override.traefik.yml docker-compose.override.yml`
    - For localhost `cp docker-compose.override.linux.yml docker-compose.override.yml`
3. Run `docker compose up` (the logs will be displayed in the current shell)
4. Create the database `docker-compose exec php bin/console doctrine:database:create`
4. Create the schema `docker-compose exec php bin/console doctrine:migration:migrate`
5. Import the fixtures `docker-compose exec php bin/console doctrine:fixtures:load`
5. Open <https://vanil.docker.test> (traefik) or <https://localhost:44333> (localhost) in your favorite web browser and [accept the auto-generated TLS certificate](https://stackoverflow.com/a/15076602/1352334)

## Fixtures

Load fixtures:
> docker-compose exec php bin/console doctrine:fixtures:load --env=test

## Code style & checks
> docker-compose exec php composer run-script phpcs

> docker-compose exec php composer run-script phpstan

## Database backup
If you install `rcopy`, you can sync the .sqllite file to S3.
There is some helper script in the `bin` directory.

For example:
> bin/db-rclone-download.sh

Be sure to set ACCESS_KEY_ID and SECRET_ACCESS_KEY in your .env.local

