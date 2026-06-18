import io

from core.models import (
    Subscription,
    Invoice,
    InvoiceStatusEnum,
    Member,
    MemberSubscription,
)
from core.tests.test_common import LoggedInTestCase
from pypdf import PdfReader


class PdfsTestCase(LoggedInTestCase):
    def test_blank(self):
        self.subscription = Subscription.objects.create(
            name="2025", price_member=4200, price_supporter=1100
        )

        response = self.client.get(f"/invoices/{self.subscription.pk}/pdf-blank/")
        self.assertEqual(200, response.status_code)

        pdf_file = io.BytesIO(response.content)
        reader = PdfReader(pdf_file)
        text = "".join(page.extract_text() for page in reader.pages)

        self.assertIn("Suggested price: 11.0 CHF", text)
        self.assertIn("CH93 0076 2011 6238 5295 7", text)

    def test_invoice_membership(self):
        self.subscription = Subscription.objects.create(
            name="2025", price_member=4200, price_supporter=1100
        )
        self.member = Member.objects.create(firstname="JohnDoe")
        self.member_subscription = MemberSubscription.objects.create(
            subscription=self.subscription, member=self.member, price=1100
        )
        self.invoice = Invoice.objects.create(
            member_subscription=self.member_subscription, price=1100
        )

        response = self.client.get(
            f"/invoices/{self.subscription.pk}/pdf/?status=created"
        )
        self.assertEqual(200, response.status_code)

        pdf_file = io.BytesIO(response.content)
        reader = PdfReader(pdf_file)
        text = "".join(page.extract_text() for page in reader.pages)

        self.assertIn("Amount\nCHF 11.00", text)
        self.assertIn("JohnDoe", text)
        self.assertIn("CH93 0076 2011 6238 5295 7", text)


class PdfInvoiceGuardsTestCase(LoggedInTestCase):
    def setUp(self):
        super().setUp()
        self.subscription = Subscription.objects.create(
            name="2025", price_member=4200, price_supporter=1100
        )
        self.member = Member.objects.create(firstname="JaneDoe")
        self.ms = MemberSubscription.objects.create(
            subscription=self.subscription, member=self.member, price=1100
        )

    def test_negative_price_returns_400(self):
        invoice = Invoice.objects.create(
            member_subscription=self.ms,
            price=-500,
            status=InvoiceStatusEnum.PAID,
        )
        response = self.client.get(f"/invoice/{invoice.pk}/pdf/")
        self.assertEqual(400, response.status_code)

    def test_zero_price_returns_400(self):
        invoice = Invoice.objects.create(member_subscription=self.ms, price=0)
        response = self.client.get(f"/invoice/{invoice.pk}/pdf/")
        self.assertEqual(400, response.status_code)


class SplitAndPayTestCase(LoggedInTestCase):
    def setUp(self):
        super().setUp()
        self.subscription = Subscription.objects.create(
            name="2025", price_member=6000, price_supporter=1000
        )
        self.member = Member.objects.create(firstname="Split")
        self.ms = MemberSubscription.objects.create(
            subscription=self.subscription, member=self.member, price=6000
        )

    def _new_invoice(self, **kwargs):
        return Invoice.objects.create(
            member_subscription=self.ms,
            price=kwargs.pop("price", 6000),
            status=kwargs.pop("status", InvoiceStatusEnum.PENDING),
            **kwargs,
        )

    def test_underpayment_creates_remainder_invoice(self):
        invoice = self._new_invoice(price=6000)
        leftover = invoice.split_and_pay(price=5500, transaction_id="TX-1")

        invoice.refresh_from_db()
        self.assertEqual(InvoiceStatusEnum.PAID, invoice.status)
        self.assertEqual(5500, invoice.price)
        self.assertEqual("TX-1", invoice.transaction_id)

        self.assertEqual(InvoiceStatusEnum.CREATED, leftover.status)
        self.assertEqual(500, leftover.price)
        self.assertIsNone(leftover.transaction_id)
        self.assertEqual(self.ms, leftover.member_subscription)

    def test_overpayment_creates_credit_invoice(self):
        invoice = self._new_invoice(price=6000)
        credit = invoice.split_and_pay(price=6500, transaction_id="TX-2")

        invoice.refresh_from_db()
        self.assertEqual(InvoiceStatusEnum.PAID, invoice.status)
        self.assertEqual(6500, invoice.price)
        self.assertEqual("TX-2", invoice.transaction_id)

        self.assertEqual(InvoiceStatusEnum.PAID, credit.status)
        self.assertEqual(500, credit.price)
        self.assertEqual("TX-2", credit.transaction_id)

    def test_exact_payment_to_already_paid_creates_new_paid_invoice(self):
        invoice = self._new_invoice(
            price=6000,
            status=InvoiceStatusEnum.PAID,
            transaction_id="TX-OLD",
        )
        new = invoice.split_and_pay(price=6000, transaction_id="TX-NEW")

        invoice.refresh_from_db()
        self.assertEqual(InvoiceStatusEnum.PAID, invoice.status)
        self.assertEqual(6000, invoice.price)
        self.assertEqual("TX-OLD", invoice.transaction_id)

        self.assertEqual(InvoiceStatusEnum.PAID, new.status)
        self.assertEqual(6000, new.price)
        self.assertEqual("TX-NEW", new.transaction_id)
        self.assertNotEqual(invoice.pk, new.pk)
