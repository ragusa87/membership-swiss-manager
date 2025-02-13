import io
from collections.abc import Generator

from django.core.files import File
from django.db.models import Count
from .format import EXPECTED_HEADERS, EXPECTED_HEADERS_LABELS
from ..models import MemberSubscription, Subscription, Member, Invoice
import csv
from django.db.models import Q
from django.db.models import F
from django.db.models import Value
from django.db.models.functions import Concat, Lower, Coalesce, Trim


class Row:
    def __init__(self, row: dict):
        self.row = row

    def str(self):
        return ",".join(self.row.values())

    def expected_members(self) -> list[str]:
        return [
            m.strip()
            for m in self.row[EXPECTED_HEADERS_LABELS.get("members")]
            .replace("&", ",")
            .split(",")
        ]

    def missing_members(self) -> list[str]:
        member_names_lower = [m.lower() for m in self.expected_members()]
        member_names = self.expected_members()
        for m in self.members():
            name = m.get_fullname().lower()
            if name in member_names_lower:
                del member_names_lower[member_names_lower.index(name)]
                del member_names[member_names_lower.index(name)]
            name = m.get_fullname_inverted().lower()
            if name in member_names_lower:
                del member_names_lower[member_names_lower.index(name)]
                del member_names[member_names_lower.index(name)]
        return member_names

    def members(self) -> list[Member]:
        names_lower = [m.lower() for m in self.expected_members()]

        firstname_exp = Lower(Coalesce(F("firstname"), Value("")))
        lastname_exp = Lower(Coalesce(F("lastname"), Value("")))

        results = Member.objects.annotate(
            fullname1=Trim(Concat(firstname_exp, Value(" "), lastname_exp)),
            fullname2=Trim(Concat(lastname_exp, Value(" "), firstname_exp)),
        ).filter(
            Q(fullname1__in=names_lower) | Q(fullname2__in=names_lower),
        )

        return [m for m in results.all()]


class CsvImporter:
    def __init__(self, subscription: Subscription):
        self.subscription = subscription
        self.__member_subscriptions__ = (
            MemberSubscription.objects.filter(subscription=subscription, active=True)
            .select_related("subscription", "member", "parent")
            .annotate(invoice_count=Count("invoices"))
            .annotate(parent_count=Count("children"))
            .prefetch_related("invoices")
            .prefetch_related("children")
            .prefetch_related("children__member")
        )

    def do_import(self, csv_file: File | io.TextIOBase) -> list[Row]:
        csv_reader = csv.DictReader(csv_file, delimiter=",", lineterminator="utf-8")

        try:
            headers = list(csv_reader.fieldnames)
            self.__compare_headers__(headers)
        except StopIteration:
            # Csv is empty
            return []
        result = []
        for row in csv_reader:
            result.append(Row(row))

        return result

    def __compare_headers__(self, csv_headers: list[str]):
        # Check if the expected headers are present in the CSV
        missing_headers = set(EXPECTED_HEADERS) - set(csv_headers)
        extra_headers = set(csv_headers) - set(EXPECTED_HEADERS)

        if missing_headers:
            raise RuntimeError("Missing headers: {}".format(missing_headers))
