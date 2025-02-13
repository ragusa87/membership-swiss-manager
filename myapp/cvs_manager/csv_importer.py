import io

from django.db.models import Count
from .format import EXPECTED_HEADERS, EXPECTED_HEADERS_LABELS
from ..models import MemberSubscription, Subscription, Member
import csv
from django.db.models.functions import Concat
from django.db.models import Q


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

    def __extract_members__(self, members: str):
        names = [member.strip() for member in members.split(",")]
        # results = Member.objects.filter(
        #     Q(firstname__concat=Concat('firstname', ', ', 'lastname'))
        #     Q(lastname__concat=Concat(('lastname', ', ', 'firstname'))
        # ).filter(
        #         Q(firstname__concat__in=names) | Q(lastname_concat__in=names)
        #     )

    def do_import(self, csv_file: io.IOBase):
        csv_reader = csv.reader(csv_file)
        headers = next(csv_reader)
        self.__compare_headers__(headers)

        for row in csv_reader:
            self.__extract_members__(row[EXPECTED_HEADERS_LABELS.members])

    def __compare_headers__(self, csv_headers):
        # Convert the CSV headers to a dictionary for easier comparison
        csv_headers_dict = {header: [] for header in csv_headers}

        # Check if the expected headers are present in the CSV
        missing_headers = set(EXPECTED_HEADERS.keys()) - set(csv_headers_dict.keys())
        extra_headers = set(csv_headers_dict.keys()) - set(EXPECTED_HEADERS.keys())

        if missing_headers:
            raise RuntimeError("Missing headers: {}".format(missing_headers))
