from contextlib import contextmanager
from pathlib import Path

from django.core.management import call_command
from django.db import connection
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


User = get_user_model()


class Command(BaseCommand):
    help = "Reset the database and load test data"

    @staticmethod
    def reset_db():
        """
        Reset the database to a blank state by removing all the tables and recreating them.
        """
        if connection.settings_dict["ENGINE"] != "django.db.backends.sqlite3":
            raise ValueError("Only sqlite is supported at the moment")

        with connection.cursor() as cursor:
            cursor.execute("PRAGMA foreign_keys = OFF;")
            table_names = connection.introspection.table_names()
            for table in table_names:
                cursor.execute(f'DROP TABLE IF EXISTS "{table}"')
            cursor.execute("PRAGMA foreign_keys = ON;")

        call_command("migrate", "--noinput")

    def add_arguments(self, parser):
        parser.add_argument(
            "-y",
            "--yes",
            action="store_true",
            dest="force_yes",
            default=False,
            help="Don't ask for confirmation.",
        )
        parser.add_argument(
            "--db",
            type=str,
            dest="db_env",
            default=None,
            help="Override DB Env",
        )

    @contextmanager
    def print_step(self, message):
        self.stdout.write(message, ending=" ")
        self.stdout.flush()
        yield
        self.stdout.write(self.style.SUCCESS("OK"))

    def confirm(self, message):
        self.stdout.write(
            self.style.WARNING("WARNING")
            + "\n"
            + message
            + "\n"
            + "Do you want to continue? (y/N) ",
            ending="",
        )

        try:
            result = input()
        except KeyboardInterrupt:
            return False

        return result.lower() == "y"

    def handle(self, *args, **options):
        # Do not send emails when performing fake tasks
        settings.EMAIL_BACKEND = "django.core.mail.backends.dummy.EmailBackend"

        if options["db_env"] is not None:
            self.override_database_name(options["db_env"])

        db_name = connection.settings_dict["NAME"]
        if not options["force_yes"]:
            if not self.confirm(
                f"This will REMOVE ALL EXISTING DATA from the database {db_name}."
            ):
                return

        with self.print_step(f"Resetting the database {db_name}..."):
            self.reset_db()

        path = Path(settings.BASE_DIR / "core" / "fixtures")
        fixtures = [f for f in path.glob("*.json")]
        fixtures.sort()
        if len(fixtures) == 0:
            self.stdout.write(f"No fixtures found in {path}.")
        for fixture_file in fixtures:
            with self.print_step(f"Loading fixture {fixture_file}..."):
                call_command("loaddata", str(fixture_file))

    def override_database_name(self, new_name):
        if connection.settings_dict["ENGINE"] != "django.db.backends.sqlite3":
            raise ValueError("Only sqlite is supported at the moment")

        path = Path(connection.settings_dict["NAME"])
        new_path = path.with_name(f"{new_name}.sqlite")
        connection.settings_dict["NAME"] = str(new_path)
