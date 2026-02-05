import io

from django.core.files import File
from .format import EXPECTED_HEADERS, EXPECTED_HEADERS_LABELS
from ..models import (
    MemberSubscription,
    Subscription,
    Member,
)
import csv
from django.db.models import Q
from django.db.models import F
from django.db.models import Value
from django.db.models.functions import Concat, Lower, Coalesce, Trim

from ..models.enum import SubscriptionTypeEnum


class Row:
    def __init__(self, row: dict, subscription: Subscription):
        self.row = row
        self.subscription = subscription

    def str(self):
        return ",".join(list(self.row.values()))

    def __repr__(self):
        return ",".join(list(self.row.values()))

    def expected_members(self) -> list[str]:
        return [
            m.strip()
            for m in self.row[EXPECTED_HEADERS_LABELS.get("members")]
            .replace("&", ",")
            .split(",")
        ]

    def as_member_subscription(self) -> MemberSubscription:
        object = MemberSubscription()
        object.subscription = self.subscription
        object.type = self.__as_type__(
            self.row[EXPECTED_HEADERS_LABELS.get("subscription_type")]
        )
        object.price = int(self.row[EXPECTED_HEADERS_LABELS.get("price")])
        members = self.members()
        if len(members) > 0:
            object.member = members.pop(0)

        return object

    def as_child_subscriptions(
        self, parent: MemberSubscription | None = None
    ) -> list[MemberSubscription]:
        members = self.members()
        if len(members) < 2:
            return []

        members.pop(0)
        result = []
        for member in members:
            child_subscription = MemberSubscription()
            child_subscription.subscription = self.subscription
            child_subscription.type = self.__as_type__(
                self.row[EXPECTED_HEADERS_LABELS.get("subscription_type")]
            )
            child_subscription.parent = parent
            child_subscription.member = member
            child_subscription.price = 0
            result.append(child_subscription)
        return result

    def missing_members(self) -> list[str]:
        member_names_lower = [m.lower() for m in self.expected_members()]
        member_names = [m for m in self.expected_members()]
        for m in self.members():
            for name in [m.get_fullname(), m.get_fullname_inverted()]:
                if name.lower() in member_names_lower:
                    index = member_names_lower.index(name.lower())
                    del member_names_lower[index]
                    del member_names[index]
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

    @staticmethod
    def __as_type__(param: str):
        match str(param):
            case SubscriptionTypeEnum.MEMBER | "member":
                return SubscriptionTypeEnum.MEMBER
            case SubscriptionTypeEnum.OTHER | "other" | "supporter" | "supporter?":
                return SubscriptionTypeEnum.OTHER
            case _:
                return SubscriptionTypeEnum.MEMBER


class Export:
    def __init__(self, rows: list[Row], subscription: Subscription):
        self.rows = rows
        self.subscription = subscription
        self.__has_missing_users_result__ = self.__process_missing_users__()

    def has_missing_users(self) -> bool:
        return self.__has_missing_users_result__

    def existing_member_subscriptions_count(self) -> int:
        return self.subscription.subscriptions.count()

    def has_existing_member_subscriptions(self) -> bool:
        return self.existing_member_subscriptions_count() > 0

    def __process_missing_users__(self) -> bool:
        for row in self.rows:
            if len(row.missing_members()) > 0:
                return True
        return False


class CsvImporter:
    def __init__(self, subscription: Subscription):
        self.subscription = subscription

    def do_import(
        self, subscription: Subscription, csv_file: File | io.TextIOBase
    ) -> Export:
        csv_reader = csv.DictReader(csv_file, delimiter=",", lineterminator="utf-8")

        try:
            headers = list(csv_reader.fieldnames)
            self.__compare_headers__(headers)
        except StopIteration:
            # Csv is empty
            return Export([], subscription)

        result = []
        for row in csv_reader:
            result.append(Row(row, subscription))

        return Export(result, subscription)

    def __compare_headers__(self, csv_headers: list[str]):
        # Check if the expected headers are present in the CSV
        missing_headers = set(EXPECTED_HEADERS) - set(csv_headers)

        if missing_headers:
            raise RuntimeError("Missing headers: {}".format(missing_headers))
