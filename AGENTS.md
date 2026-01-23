# Project: django-membership

A Django membership management application.

## Purpose

Originally built for a community vegetable garden to manage plot participation fees. One person pays the subscription for a plot, and other users of the same plot are linked via a parent-child relationship (not billed). This is a technical grouping mechanism, not a family relationship - it simply means one subscription is the "parent" that gets billed, while others are "children" with zero cost. Users arrange among themselves to split costs outside the system.

## Tech Stack

- Python 3.13+
- Django 6.0
- PostgreSQL (via Docker)
- uv for dependency management

## Development Setup

### Docker-based development

Commands run inside Docker via the justfile shell configuration:

```bash
just venv      # Create virtual environment with uv
just sync      # Install all dependencies (including dev) with uv sync --all-extras
just lock      # Update uv.lock file
just init      # Full setup: venv + sync + migrate + create superuser + collectstatic
```

### Local commands

```bash
just manage <args>   # Run manage.py commands
just test <args>     # Run tests
just start           # Run development server
just lint            # Format and lint with ruff
just translate       # Generate and compile translations
```

## Docker

- `compose.yaml` - Production-like config
- `compose.dev.yaml` - Development overrides
- `compose.override.yaml` - Local overrides (gitignored)

### Dockerfile stages

- `base` - Common setup with uv, locales, and system dependencies
- `prod` - Production: `uv sync --frozen --no-dev`
- `dev` - Development: `uv sync --frozen --all-extras`

## Project Structure

```
myapp/           # Main Django application
templates/       # Django templates
locale/          # Translation files
assets/          # Static assets
db/              # SQLite database (mounted in Docker)
```

## Authentication

Configurable via `CUSTOM_AUTHENTICATION_BACKEND` environment variable:
- `demo` - Uses SettingsBackend for demo/testing
- `authcrunch` - Uses AuthcrunchRemoteUserBackend with middleware

## Dependencies

Production dependencies include:
- gunicorn (WSGI server)
- qrbill, cairosvg, pypdf (PDF/QR generation)
- pandas, xlsxwriter (Excel export)
- pycamt (banking/CAMT files)
- django-phonenumber-field

Dev dependencies:
- ruff (linting/formatting)
- rust-just (task runner)
- pytest, beautifulsoup4 (testing)

## Models

All models are in `myapp/models/`.

### Member

A person in the organization. Fields: `firstname`, `lastname`, `email`, `phone`, `address`, `city`, `zip`.

### Subscription

A subscription period (e.g., "2024", "2025"). Has `price_member` and `price_supporter` (in centimes).

### MemberSubscription

Links a Member to a Subscription. Core fields:
- `member` - ForeignKey to Member
- `subscription` - ForeignKey to Subscription
- `type` - `member` or `other` (affects price)
- `active` - Whether subscription is active
- `price` - Calculated price (auto-set on save)
- `parent` - ForeignKey to self (for family/group subscriptions)

**Family/Group subscriptions**: Multiple members can share a subscription. The parent MemberSubscription pays the full price, while children (linked via `parent` field) get the subscription for free (price = 0). This allows families or groups to subscribe together under one payment.

### Invoice

A payment request for a MemberSubscription. Core fields:
- `member_subscription` - ForeignKey to MemberSubscription
- `reference` - Unique invoice number
- `status` - `created`, `pending`, `paid`, `canceled`
- `price` - Amount in centimes
- `reminder` - Reminder count (0-3)

Supports reminders (up to 3) and partial payment splitting.

## Key Views

### Dashboard (`/dashboard/<subscription_name>`)

Displays statistics for a subscription period (defaults to current year):
- Total subscriptions count and growth vs previous year
- Due amounts (created/pending invoices) and expected total
- Paid amounts and collection rate (paid / expected)
- Lists all active member subscriptions with their invoice status

### CAMT Import (`/camt/`)

CAMT is a Swiss banking standard (ISO 20022) for account statements in XML format. This feature reconciles bank payments with invoices.

**Workflow:**
1. **Upload** (`/camt/upload`) - Upload a CAMT XML file and select the subscription period
2. **Process** (`/camt/process`) - View parsed transactions and their matched invoices
3. **Reconciliation** - Manually match unmatched transactions to invoices

**Automatic matching** tries to find invoices by:
1. Transaction ID (exact match with `invoice.transaction_id`)
2. Reference number (RF creditor reference) + name similarity >= 90%

**Actions:**
- Mark invoice as paid (links transaction_id, sets status to paid)
- Split payment - if amount differs or invoice already paid, creates a new invoice for the difference
- Create new invoice for a subscription and mark it paid

### Assign Members (`/assign/<subscription_name>`)

Allows assigning existing members to a subscription period.

- Shows candidates: members not yet assigned to this subscription
- Search by firstname, lastname, or email
- For each candidate, select subscription type (member/other) and optionally link to a parent (for family subscriptions)
- Also displays currently assigned members with their children
