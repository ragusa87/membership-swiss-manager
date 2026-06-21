import os
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.test import TestCase

from core.models import (
    CamtImport,
    Invoice,
    InvoiceStatusEnum,
    Member,
    MemberSubscription,
    Subscription,
)
from core.settings import FILE_UPLOAD_MAX_MEMORY_SIZE
from core.tests.test_common import LoggedInTestCase
from core.views_more.camt_import import MAX_RECENT_IMPORTS

FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "camt-demo.xml")
FIXTURE_054_PATH = os.path.join(os.path.dirname(__file__), "camt-054-batch.xml")


def _upload_fixture(client, subscription, path=FIXTURE_PATH):
    with open(path, "rb") as f:
        return client.post(
            "/import-camt",
            data={"camt_file": f, "subscription": subscription.pk},
            follow=True,
        )


class CamtUploadAndProcessTestCase(LoggedInTestCase):
    def setUp(self):
        super().setUp()
        self.subscription = Subscription.objects.create(
            name="2025", price_member=4200, price_supporter=1100
        )

    def test_camt_import(self):
        response = _upload_fixture(self.client, self.subscription)

        self.assertEqual(200, response.status_code)

        self.assertEqual(1, CamtImport.objects.count())
        camt_import = CamtImport.objects.get()
        self.assertEqual(self.subscription, camt_import.subscription)

        final_url = response.redirect_chain[-1][0]
        self.assertEqual(f"/process-camt/{camt_import.pk}/", final_url)

        self.assertContains(response, "ACCOUNT OWNER => PAYER 1")
        self.assertContains(response, "TXID-XXXX-1")
        self.assertContains(response, "Payment details 1")
        self.assertContains(response, "Resolve? 60.00 CHF Bonification PAYER 1")

        self.assertContains(response, "ACCOUNT OWNER => PAYER 2")
        self.assertContains(response, "TXID-XXXX-2")
        self.assertContains(response, "Payment details 2")
        self.assertContains(response, "Resolve? 60.00 CHF Bonification PAYER 2")

    def test_camt_process_persists_across_session_loss(self):
        _upload_fixture(self.client, self.subscription)
        camt_import = CamtImport.objects.get()

        self.client.logout()
        self.client.force_login(self.user)

        response = self.client.get(f"/process-camt/{camt_import.pk}/")
        self.assertEqual(200, response.status_code)
        self.assertContains(response, "TXID-XXXX-1")

    def test_camt_upload_page_lists_recent_imports(self):
        other_subscription = Subscription.objects.create(
            name="2024", price_member=4000, price_supporter=1000
        )
        first = CamtImport.objects.create(
            subscription=self.subscription,
            file=ContentFile(b"<x/>", name="first.xml"),
        )
        second = CamtImport.objects.create(
            subscription=other_subscription,
            file=ContentFile(b"<x/>", name="second.xml"),
        )

        response = self.client.get("/import-camt")

        self.assertEqual(200, response.status_code)
        self.assertContains(response, f"/process-camt/{first.pk}/")
        self.assertContains(response, f"/process-camt/{second.pk}/")
        self.assertContains(response, "2024")
        self.assertContains(response, "2025")


class Camt054BatchTestCase(LoggedInTestCase):
    def setUp(self):
        super().setUp()
        self.subscription = Subscription.objects.create(
            name="2026", price_member=6000, price_supporter=3000
        )

    def test_camt054_batch_entry_renders_each_transaction(self):
        response = _upload_fixture(
            self.client, self.subscription, path=FIXTURE_054_PATH
        )

        self.assertEqual(200, response.status_code)
        camt_import = CamtImport.objects.get()
        self.assertEqual(
            f"/process-camt/{camt_import.pk}/", response.redirect_chain[-1][0]
        )

        for ref in (
            "RF85000000000000000000094",
            "RF47000000000000000000099",
            "RF31000000000000000000096",
        ):
            self.assertContains(response, ref)

        for payer in ("PAYER 054 ONE", "PAYER 054 TWO", "PAYER 054 THREE"):
            self.assertContains(response, f"ACCOUNT OWNER 054 => {payer}")

        for end_to_end in (
            "ANON-E2E-054-1",
            "ANON-E2E-054-2",
            "ANON-E2E-054-3",
        ):
            self.assertContains(response, end_to_end)

        self.assertContains(response, "MEMBRE 2026")
        self.assertContains(response, "membre 2026")

    def test_camt054_matches_invoices_by_reference_and_debtor_name(self):
        member = Member.objects.create(firstname="Ultimate Payer", lastname="Two")
        member_subscription = MemberSubscription.objects.create(
            subscription=self.subscription, member=member, price=6000
        )
        invoice = Invoice.objects.create(
            pk=99,
            member_subscription=member_subscription,
            price=6000,
            status=InvoiceStatusEnum.CREATED,
        )

        response = _upload_fixture(
            self.client, self.subscription, path=FIXTURE_054_PATH
        )

        self.assertEqual(200, response.status_code)
        self.assertContains(response, f"/camt_link/{invoice.pk}/60/ANON-INSTR-2/")
        self.assertContains(response, "bg-green-600")

    def test_camt054_unmatched_gutschrift_shows_resolve_button(self):
        response = _upload_fixture(
            self.client, self.subscription, path=FIXTURE_054_PATH
        )

        self.assertEqual(200, response.status_code)
        self.assertContains(response, "Resolve?", count=3)

    def test_camt054_parser_extracts_distinct_fields_per_transaction(self):
        from core.camt_importer.camt_importer import CamtImporter

        with open(FIXTURE_054_PATH, "rb") as f:
            importer = CamtImporter(f)
            transactions = importer.transactions()

        self.assertEqual(3, len(transactions))

        self.assertEqual(
            [t.Reference for t in transactions],
            [
                "RF85000000000000000000094",
                "RF47000000000000000000099",
                "RF31000000000000000000096",
            ],
        )
        self.assertEqual(
            [t.DebtorName for t in transactions],
            ["PAYER 054 ONE", "PAYER 054 TWO", "PAYER 054 THREE"],
        )
        self.assertEqual(
            [t.TxId for t in transactions],
            ["ANON-INSTR-1", "ANON-INSTR-2", "ANON-INSTR-3"],
        )
        for t in transactions:
            self.assertEqual("ACCOUNT OWNER 054", t.CreditorName)
            self.assertIn(t.RemittanceInformation, ("MEMBRE 2026", "membre 2026"))
            self.assertEqual(6000, t.price)
            self.assertEqual("Gutschrift", t.AdditionalEntryInformation)


class CamtProcessViewTestCase(LoggedInTestCase):
    def setUp(self):
        super().setUp()
        self.subscription = Subscription.objects.create(
            name="2025", price_member=4200, price_supporter=1100
        )
        self.member = Member.objects.create(firstname="PAYER", lastname="1")
        self.member_subscription = MemberSubscription.objects.create(
            subscription=self.subscription, member=self.member, price=6000
        )

    def _upload(self):
        _upload_fixture(self.client, self.subscription)
        return CamtImport.objects.get()

    def test_process_camt_returns_404_for_unknown_pk(self):
        response = self.client.get("/process-camt/9999/")
        self.assertEqual(404, response.status_code)

    def test_valid_invoice_renders_no_link_button(self):
        Invoice.objects.create(
            member_subscription=self.member_subscription,
            price=6000,
            status=InvoiceStatusEnum.PAID,
            transaction_id="TXID-XXXX-1",
        )
        camt_import = self._upload()

        response = self.client.get(f"/process-camt/{camt_import.pk}/")

        self.assertEqual(200, response.status_code)
        self.assertNotContains(response, "Link to invoice")
        self.assertContains(response, "text-green-800")

    def test_price_mismatch_renders_orange_button_and_warning(self):
        invoice = Invoice.objects.create(
            member_subscription=self.member_subscription,
            price=5000,
            status=InvoiceStatusEnum.CREATED,
            transaction_id="TXID-XXXX-1",
        )
        camt_import = self._upload()

        response = self.client.get(f"/process-camt/{camt_import.pk}/")

        self.assertEqual(200, response.status_code)
        self.assertContains(response, f"/camt_link/{invoice.pk}/60/TXID-XXXX-1/")
        self.assertContains(response, "bg-orange-600")
        self.assertContains(response, "Price mismatch")
        self.assertContains(response, "50.00 CHF")

    def test_subscription_mismatch_renders_warning(self):
        other_subscription = Subscription.objects.create(
            name="2024", price_member=4000, price_supporter=1000
        )
        other_member_subscription = MemberSubscription.objects.create(
            subscription=other_subscription, member=self.member, price=6000
        )
        Invoice.objects.create(
            member_subscription=other_member_subscription,
            price=6000,
            status=InvoiceStatusEnum.CREATED,
            transaction_id="TXID-XXXX-1",
        )
        camt_import = self._upload()

        response = self.client.get(f"/process-camt/{camt_import.pk}/")

        self.assertEqual(200, response.status_code)
        self.assertContains(
            response, f"Subscription missmatch ({other_subscription.name})"
        )


class CamtLinkInvoiceTestCase(LoggedInTestCase):
    def setUp(self):
        super().setUp()
        self.subscription = Subscription.objects.create(
            name="2025", price_member=4200, price_supporter=1100
        )
        self.member = Member.objects.create(firstname="Jane", lastname="Doe")
        self.member_subscription = MemberSubscription.objects.create(
            subscription=self.subscription, member=self.member, price=6000
        )

    def _make_invoice(self, **overrides):
        defaults = dict(
            member_subscription=self.member_subscription,
            price=6000,
            status=InvoiceStatusEnum.CREATED,
        )
        defaults.update(overrides)
        return Invoice.objects.create(**defaults)

    def test_returns_404_for_unknown_invoice(self):
        response = self.client.get("/camt_link/9999/60.00/TX-NEW/")
        self.assertEqual(404, response.status_code)

    def test_marks_invoice_paid_and_renders_partial(self):
        invoice = self._make_invoice()

        response = self.client.get(f"/camt_link/{invoice.pk}/60.00/TX-NEW/")

        self.assertEqual(200, response.status_code)
        invoice.refresh_from_db()
        self.assertEqual(InvoiceStatusEnum.PAID, invoice.status)
        self.assertEqual("TX-NEW", invoice.transaction_id)
        self.assertEqual(6000, invoice.price)
        self.assertContains(response, "Jane")
        self.assertEqual(1, Invoice.objects.count())

    def test_underpayment_creates_leftover_created_invoice(self):
        invoice = self._make_invoice(price=6000)

        response = self.client.get(f"/camt_link/{invoice.pk}/40.00/TX-UNDER/")

        self.assertEqual(200, response.status_code)
        invoice.refresh_from_db()
        self.assertEqual(InvoiceStatusEnum.PAID, invoice.status)
        self.assertEqual(4000, invoice.price)
        self.assertEqual("TX-UNDER", invoice.transaction_id)

        leftover = Invoice.objects.exclude(pk=invoice.pk).get()
        self.assertEqual(InvoiceStatusEnum.CREATED, leftover.status)
        self.assertEqual(2000, leftover.price)
        self.assertIsNone(leftover.transaction_id)

    def test_overpayment_creates_leftover_paid_invoice(self):
        invoice = self._make_invoice(price=6000)

        response = self.client.get(f"/camt_link/{invoice.pk}/80.00/TX-OVER/")

        self.assertEqual(200, response.status_code)
        invoice.refresh_from_db()
        self.assertEqual(InvoiceStatusEnum.PAID, invoice.status)
        self.assertEqual(8000, invoice.price)
        self.assertEqual("TX-OVER", invoice.transaction_id)

        leftover = Invoice.objects.exclude(pk=invoice.pk).get()
        self.assertEqual(InvoiceStatusEnum.PAID, leftover.status)
        self.assertEqual(2000, leftover.price)
        self.assertEqual("TX-OVER", leftover.transaction_id)

    def test_already_paid_invoice_creates_sibling(self):
        invoice = self._make_invoice(
            status=InvoiceStatusEnum.PAID, transaction_id="TX-ORIG"
        )
        original_price = invoice.price

        response = self.client.get(f"/camt_link/{invoice.pk}/60.00/TX-SECOND/")

        self.assertEqual(200, response.status_code)
        invoice.refresh_from_db()
        self.assertEqual(InvoiceStatusEnum.PAID, invoice.status)
        self.assertEqual("TX-ORIG", invoice.transaction_id)
        self.assertEqual(original_price, invoice.price)

        sibling = Invoice.objects.exclude(pk=invoice.pk).get()
        self.assertEqual(InvoiceStatusEnum.PAID, sibling.status)
        self.assertEqual(6000, sibling.price)
        self.assertEqual("TX-SECOND", sibling.transaction_id)

    def test_different_transaction_id_creates_sibling(self):
        invoice = self._make_invoice(
            status=InvoiceStatusEnum.CREATED, transaction_id="TX-ORIG"
        )

        response = self.client.get(f"/camt_link/{invoice.pk}/60.00/TX-OTHER/")

        self.assertEqual(200, response.status_code)
        invoice.refresh_from_db()
        self.assertEqual("TX-ORIG", invoice.transaction_id)
        self.assertEqual(InvoiceStatusEnum.CREATED, invoice.status)

        sibling = Invoice.objects.exclude(pk=invoice.pk).get()
        self.assertEqual(InvoiceStatusEnum.PAID, sibling.status)
        self.assertEqual("TX-OTHER", sibling.transaction_id)


class CamtReconciliationTestCase(LoggedInTestCase):
    def setUp(self):
        super().setUp()
        self.subscription = Subscription.objects.create(
            name="2025", price_member=4200, price_supporter=1100
        )
        self.member = Member.objects.create(firstname="JohnDoe")
        self.member_subscription = MemberSubscription.objects.create(
            subscription=self.subscription, member=self.member, price=4200
        )
        self.camt_import = CamtImport.objects.create(
            subscription=self.subscription,
            file=ContentFile(b"<x/>", name="recon.xml"),
        )

    def test_reconciliation_get_uses_import_id(self):
        response = self.client.get(
            f"/process-camt/{self.camt_import.pk}/reconciliation/",
            {
                "transaction_id": "TX",
                "amount": "60",
                "label": "foo",
            },
        )

        self.assertEqual(200, response.status_code)
        self.assertContains(response, "JohnDoe")

    def test_reconciliation_returns_404_for_unknown_import_id(self):
        response = self.client.get(
            "/process-camt/9999/reconciliation/",
            {"transaction_id": "TX", "amount": "60", "label": "foo"},
        )

        self.assertEqual(404, response.status_code)

    def test_reconciliation_creates_new_invoice(self):
        self.assertEqual(0, Invoice.objects.count())

        response = self.client.post(
            f"/process-camt/{self.camt_import.pk}/reconciliation/",
            data={
                "new_invoice_for_subscription": self.member_subscription.pk,
                "transaction_id": "TX",
                "amount": "60",
            },
        )

        self.assertEqual(200, response.status_code)
        self.assertEqual(1, Invoice.objects.count())
        invoice = Invoice.objects.get()
        self.assertEqual(InvoiceStatusEnum.PAID, invoice.status)
        self.assertEqual(6000, invoice.price)


class CamtImportDeleteTestCase(LoggedInTestCase):
    def setUp(self):
        super().setUp()
        self.subscription = Subscription.objects.create(
            name="2025", price_member=4200, price_supporter=1100
        )
        self.camt_import = CamtImport.objects.create(
            subscription=self.subscription,
            file=ContentFile(b"<x/>", name="to-delete.xml"),
        )
        self.stored_name = self.camt_import.file.name

    def test_get_renders_confirmation_without_deleting(self):
        response = self.client.get(f"/process-camt/{self.camt_import.pk}/delete/")

        self.assertEqual(200, response.status_code)
        self.assertContains(response, "to-delete.xml")
        self.assertContains(response, self.subscription.name)
        self.assertContains(response, "csrfmiddlewaretoken")
        self.assertTrue(CamtImport.objects.filter(pk=self.camt_import.pk).exists())
        self.assertTrue(default_storage.exists(self.stored_name))

    def test_post_deletes_row_and_file(self):
        self.assertTrue(default_storage.exists(self.stored_name))

        response = self.client.post(f"/process-camt/{self.camt_import.pk}/delete/")

        self.assertEqual(302, response.status_code)
        self.assertEqual("/import-camt", response.url)
        self.assertFalse(CamtImport.objects.filter(pk=self.camt_import.pk).exists())
        self.assertFalse(default_storage.exists(self.stored_name))

    def test_missing_pk_returns_404_on_get(self):
        response = self.client.get("/process-camt/9999/delete/")
        self.assertEqual(404, response.status_code)

    def test_missing_pk_returns_404_on_post(self):
        response = self.client.post("/process-camt/9999/delete/")
        self.assertEqual(404, response.status_code)


class CamtImportDeleteAuthTestCase(TestCase):
    def setUp(self):
        self.subscription = Subscription.objects.create(
            name="2025", price_member=4200, price_supporter=1100
        )
        self.camt_import = CamtImport.objects.create(
            subscription=self.subscription,
            file=ContentFile(b"<x/>", name="protected.xml"),
        )

    def test_anonymous_get_redirects_to_login(self):
        response = self.client.get(f"/process-camt/{self.camt_import.pk}/delete/")

        self.assertEqual(302, response.status_code)
        self.assertIn("/admin/login/", response.url)

    def test_anonymous_post_redirects_to_login_without_deleting(self):
        response = self.client.post(f"/process-camt/{self.camt_import.pk}/delete/")

        self.assertEqual(302, response.status_code)
        self.assertIn("/admin/login/", response.url)
        self.assertTrue(CamtImport.objects.filter(pk=self.camt_import.pk).exists())


class CamtAnonymousAccessTestCase(TestCase):
    def setUp(self):
        self.subscription = Subscription.objects.create(
            name="2025", price_member=4200, price_supporter=1100
        )
        self.member = Member.objects.create(firstname="JohnDoe")
        self.member_subscription = MemberSubscription.objects.create(
            subscription=self.subscription, member=self.member, price=4200
        )
        self.invoice = Invoice.objects.create(
            member_subscription=self.member_subscription,
            price=6000,
            status=InvoiceStatusEnum.CREATED,
        )
        self.camt_import = CamtImport.objects.create(
            subscription=self.subscription,
            file=ContentFile(b"<x/>", name="protected.xml"),
        )

    def test_anonymous_camt_link_does_not_pay_invoice(self):
        response = self.client.get(f"/camt_link/{self.invoice.pk}/60.00/TX-EVIL/")

        self.assertEqual(302, response.status_code)
        self.assertIn("/admin/login/", response.url)

        self.invoice.refresh_from_db()
        self.assertEqual(InvoiceStatusEnum.CREATED, self.invoice.status)
        self.assertIsNone(self.invoice.transaction_id)

    def test_anonymous_camt_reconciliation_redirects_to_login(self):
        response = self.client.get(
            f"/process-camt/{self.camt_import.pk}/reconciliation/",
            {
                "transaction_id": "TX",
                "amount": "60",
                "label": "foo",
            },
        )

        self.assertEqual(302, response.status_code)
        self.assertIn("/admin/login/", response.url)

    def test_anonymous_camt_reconciliation_post_does_not_pay_invoice(self):
        response = self.client.post(
            f"/process-camt/{self.camt_import.pk}/reconciliation/",
            data={
                "invoice_id": self.invoice.pk,
                "transaction_id": "TX-EVIL",
                "amount": "60",
            },
        )

        self.assertEqual(302, response.status_code)
        self.assertIn("/admin/login/", response.url)

        self.invoice.refresh_from_db()
        self.assertEqual(InvoiceStatusEnum.CREATED, self.invoice.status)
        self.assertIsNone(self.invoice.transaction_id)

    def test_anonymous_camt_process_redirects_to_login(self):
        response = self.client.get(f"/process-camt/{self.camt_import.pk}/")

        self.assertEqual(302, response.status_code)
        self.assertIn("/admin/login/", response.url)

    def test_anonymous_camt_upload_get_redirects_to_login(self):
        response = self.client.get("/import-camt")

        self.assertEqual(302, response.status_code)
        self.assertIn("/admin/login/", response.url)

    def test_anonymous_camt_upload_post_does_not_create_import(self):
        existing_pks = set(CamtImport.objects.values_list("pk", flat=True))

        response = _upload_fixture(self.client, self.subscription)

        self.assertEqual(200, response.status_code)
        self.assertIn("/admin/login/", response.redirect_chain[-1][0])
        self.assertEqual(
            existing_pks, set(CamtImport.objects.values_list("pk", flat=True))
        )


class CamtImportModelValidationTestCase(TestCase):
    def setUp(self):
        self.subscription = Subscription.objects.create(
            name="2025", price_member=4200, price_supporter=1100
        )

    def test_full_clean_rejects_non_xml_extension(self):
        camt_import = CamtImport(
            subscription=self.subscription,
            file=ContentFile(b"<x/>", name="evil.exe"),
        )
        with self.assertRaises(ValidationError) as ctx:
            camt_import.full_clean()
        self.assertIn("file", ctx.exception.message_dict)

    def test_full_clean_accepts_xml_extension(self):
        camt_import = CamtImport(
            subscription=self.subscription,
            file=ContentFile(b"<x/>", name="ok.xml"),
        )
        camt_import.full_clean()

    def test_delete_succeeds_when_storage_raises(self):
        camt_import = CamtImport.objects.create(
            subscription=self.subscription,
            file=ContentFile(b"<x/>", name="gone.xml"),
        )
        pk = camt_import.pk

        with patch.object(default_storage, "delete", side_effect=FileNotFoundError):
            camt_import.delete()

        self.assertFalse(CamtImport.objects.filter(pk=pk).exists())

    def test_full_clean_rejects_oversized_file(self):
        oversized = b"<x/>" + b"a" * FILE_UPLOAD_MAX_MEMORY_SIZE
        camt_import = CamtImport(
            subscription=self.subscription,
            file=ContentFile(oversized, name="big.xml"),
        )
        with self.assertRaises(ValidationError) as ctx:
            camt_import.full_clean()
        self.assertIn("file", ctx.exception.message_dict)


class CamtUploadPruningTestCase(LoggedInTestCase):
    def setUp(self):
        super().setUp()
        self.subscription = Subscription.objects.create(
            name="2025", price_member=4200, price_supporter=1100
        )

    def test_upload_prunes_old_imports(self):
        pre_existing = []
        for i in range(MAX_RECENT_IMPORTS):
            pre_existing.append(
                CamtImport.objects.create(
                    subscription=self.subscription,
                    file=ContentFile(b"<x/>", name=f"old-{i}.xml"),
                )
            )

        oldest = pre_existing[0]
        oldest_file_name = oldest.file.name
        self.assertTrue(default_storage.exists(oldest_file_name))

        _upload_fixture(self.client, self.subscription)

        self.assertEqual(MAX_RECENT_IMPORTS, CamtImport.objects.count())
        self.assertFalse(CamtImport.objects.filter(pk=oldest.pk).exists())
        self.assertFalse(default_storage.exists(oldest_file_name))
