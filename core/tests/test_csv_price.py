import csv
import io

from django.test import TestCase

from core.cvs_manager.csv_exporter import CsvExporter
from core.cvs_manager.csv_importer import CsvImporter
from core.models import (
    Invoice,
    InvoiceStatusEnum,
    Member,
    MemberSubscription,
    Subscription,
)


class CsvPriceTest(TestCase):
    def setUp(self):
        self.subscription = Subscription.objects.create(
            name="2025", price_member=4250, price_supporter=1100
        )
        self.member = Member.objects.create(firstname="John", lastname="Doe")
        self.member_subscription = MemberSubscription.objects.create(
            subscription=self.subscription, member=self.member, price=4250
        )

    def _export_rows(self):
        output = CsvExporter(self.subscription).export("csv")
        reader = csv.DictReader(io.StringIO(output.read().decode("utf-8")))
        return list(reader)

    def test_export_prix_in_chf_with_cents(self):
        rows = self._export_rows()
        self.assertEqual(rows[0]["prix"], "42.5")

    def test_export_due_amount_in_chf(self):
        rows = self._export_rows()
        # Nothing paid yet → full price is due, in CHF
        self.assertEqual(rows[0]["Montant Dû"], "42.5")

    def test_export_due_amount_after_partial_payment(self):
        Invoice.objects.create(
            member_subscription=self.member_subscription,
            price=2000,
            status=InvoiceStatusEnum.PAID,
        )
        rows = self._export_rows()
        # 4250 - 2000 = 2250 centimes → 22.5 CHF
        self.assertEqual(rows[0]["Montant Dû"], "22.5")

    def test_import_prix_stored_as_centimes(self):
        csv_content = (
            "id,membres,type d'inscription,prix,Montant Dû\n1,John Doe,member,42.50,0\n"
        )
        export = CsvImporter(self.subscription).do_import(
            self.subscription, io.StringIO(csv_content)
        )
        ms = export.rows[0].as_member_subscription()
        self.assertEqual(ms.price, 4250)

    def test_export_import_roundtrip_preserves_price(self):
        csv_bytes = CsvExporter(self.subscription).export("csv").read()
        export = CsvImporter(self.subscription).do_import(
            self.subscription, io.StringIO(csv_bytes.decode("utf-8"))
        )
        ms = export.rows[0].as_member_subscription()
        self.assertEqual(ms.price, self.member_subscription.price)
