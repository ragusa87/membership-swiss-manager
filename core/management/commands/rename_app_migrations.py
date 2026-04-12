from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Rename app in django_migrations table (for app renames)"

    def add_arguments(self, parser):
        parser.add_argument(
            "old_app",
            type=str,
            help="The old app name",
        )
        parser.add_argument(
            "new_app",
            type=str,
            help="The new app name",
        )
        parser.add_argument(
            "-y",
            "--yes",
            action="store_true",
            dest="force_yes",
            default=False,
            help="Don't ask for confirmation.",
        )

    def handle(self, *args, **options):
        old_app = options["old_app"]
        new_app = options["new_app"]
        force_yes = options["force_yes"]

        with connection.cursor() as cursor:
            # Check how many migrations need to be updated
            cursor.execute(
                "SELECT COUNT(*) FROM django_migrations WHERE app = %s",
                [old_app],
            )
            count = cursor.fetchone()[0]

            if count == 0:
                self.stdout.write(
                    self.style.WARNING(f"No migrations found for app '{old_app}'")
                )
                return

            # Show what will be updated
            cursor.execute(
                "SELECT name FROM django_migrations WHERE app = %s ORDER BY id",
                [old_app],
            )
            migrations = [row[0] for row in cursor.fetchall()]

            self.stdout.write(
                self.style.WARNING(
                    f"\nThis will update {count} migration(s) from app '{old_app}' to '{new_app}':"
                )
            )
            for migration in migrations:
                self.stdout.write(f"  - {migration}")

            # Ask for confirmation
            if not force_yes:
                self.stdout.write(
                    self.style.WARNING("\nDo you want to continue? (y/N) "),
                    ending="",
                )
                try:
                    result = input()
                except KeyboardInterrupt:
                    self.stdout.write("\nAborted.")
                    return

                if result.lower() != "y":
                    self.stdout.write("Aborted.")
                    return

            # Perform the update
            cursor.execute(
                "UPDATE django_migrations SET app = %s WHERE app = %s",
                [new_app, old_app],
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f"\n✓ Successfully updated {count} migration(s) from '{old_app}' to '{new_app}'"
                )
            )
