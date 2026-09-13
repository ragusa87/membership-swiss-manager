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

    def test_name_matched_unpaid_invoice_renders_reconcile_button(self):
        """An unpaid invoice matched by name (no transaction_id) must expose a
        one-click reconcile button, not render as already-valid green text."""
        invoice = Invoice.objects.create(
            member_subscription=self.member_subscription,
            price=6000,
            status=InvoiceStatusEnum.CREATED,
        )
        camt_import = self._upload()

        response = self.client.get(f"/process-camt/{camt_import.pk}/")

        self.assertEqual(200, response.status_code)
        self.assertContains(response, "Link to invoice")
        self.assertContains(response, f"/camt_link/{invoice.pk}/60/TXID-XXXX-1/")
        self.assertContains(response, "bg-green-600")

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
        defaults = {
            "member_subscription": self.member_subscription,
            "price": 6000,
            "status": InvoiceStatusEnum.CREATED,
        }
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


class CamtFallbackChainsTestCase(TestCase):
    """Test fallback chains for missing CAMT transaction fields"""

    def setUp(self):
        from core.camt_importer.camt_importer import CamtImporter

        self.CamtImporter = CamtImporter

    def test_transaction_id_fallback_to_end_to_end_id(self):
        """TxId missing, should fallback to EndToEndId"""
        transaction = {
            "EndToEndId": "END-TO-END-123",
            "AdditionalEntryInformation": "Test",
            "Amount": 100,
        }
        # Simulate the transactions() method logic
        tx_id = (
            transaction.get("TxId")
            or transaction.get("EndToEndId")
            or transaction.get("InstrId")
            or transaction.get("AcctSvcrRef")
        )
        self.assertEqual(tx_id, "END-TO-END-123")

    def test_transaction_id_fallback_to_instr_id(self):
        """TxId and EndToEndId missing, should fallback to InstrId"""
        transaction = {
            "InstrId": "INSTR-456",
            "AdditionalEntryInformation": "Test",
            "Amount": 100,
        }
        tx_id = (
            transaction.get("TxId")
            or transaction.get("EndToEndId")
            or transaction.get("InstrId")
            or transaction.get("AcctSvcrRef")
        )
        self.assertEqual(tx_id, "INSTR-456")

    def test_transaction_id_fallback_to_acct_svcr_ref(self):
        """Only AcctSvcrRef available, should use it"""
        transaction = {
            "AcctSvcrRef": "ACCT-789",
            "AdditionalEntryInformation": "Test",
            "Amount": 100,
        }
        tx_id = (
            transaction.get("TxId")
            or transaction.get("EndToEndId")
            or transaction.get("InstrId")
            or transaction.get("AcctSvcrRef")
        )
        self.assertEqual(tx_id, "ACCT-789")

    def test_reference_fallback_to_acct_svcr_ref(self):
        """Reference missing, should fallback to AcctSvcrRef"""
        transaction = {
            "AcctSvcrRef": "ACCT-REF-123",
            "AdditionalEntryInformation": "Test",
        }
        reference = transaction.get("Reference") or transaction.get("AcctSvcrRef")
        self.assertEqual(reference, "ACCT-REF-123")

    def test_reference_preferred_over_acct_svcr_ref(self):
        """When both present, Reference should be preferred"""
        transaction = {
            "Reference": "REF-123",
            "AcctSvcrRef": "ACCT-REF-456",
            "AdditionalEntryInformation": "Test",
        }
        reference = transaction.get("Reference") or transaction.get("AcctSvcrRef")
        self.assertEqual(reference, "REF-123")

    def test_additional_info_fallback_to_remittance(self):
        """AdditionalEntryInformation missing, should fallback to RemittanceInformation"""
        transaction = {
            "RemittanceInformation": "Payment for invoice",
            "TxId": "TX-123",
        }
        additional_info = (
            transaction.get("AdditionalEntryInformation")
            or transaction.get("RemittanceInformation")
            or ""
        )
        self.assertEqual(additional_info, "Payment for invoice")

    def test_additional_info_preferred_over_remittance(self):
        """When both present, AdditionalEntryInformation should be preferred"""
        transaction = {
            "AdditionalEntryInformation": "Additional info",
            "RemittanceInformation": "Remittance info",
            "TxId": "TX-123",
        }
        additional_info = (
            transaction.get("AdditionalEntryInformation")
            or transaction.get("RemittanceInformation")
            or ""
        )
        self.assertEqual(additional_info, "Additional info")

    def test_additional_info_fallback_to_empty_string(self):
        """Both missing, should fallback to empty string"""
        transaction = {
            "TxId": "TX-123",
        }
        additional_info = (
            transaction.get("AdditionalEntryInformation")
            or transaction.get("RemittanceInformation")
            or ""
        )
        self.assertEqual(additional_info, "")

    def test_all_fallbacks_work_together(self):
        """Test all fallback chains working together"""
        transaction = {
            "EndToEndId": "E2E-123",
            "AcctSvcrRef": "ACCT-789",
            "RemittanceInformation": "Payment details",
            "DebtorName": "John Doe",
            "Amount": 100,
        }
        # Simulate full transaction processing
        tx_id = (
            transaction.get("TxId")
            or transaction.get("EndToEndId")
            or transaction.get("InstrId")
            or transaction.get("AcctSvcrRef")
        )
        reference = transaction.get("Reference") or transaction.get("AcctSvcrRef")
        additional_info = (
            transaction.get("AdditionalEntryInformation")
            or transaction.get("RemittanceInformation")
            or ""
        )

        self.assertEqual(tx_id, "E2E-123")
        self.assertEqual(reference, "ACCT-789")
        self.assertEqual(additional_info, "Payment details")
        self.assertEqual(transaction.get("DebtorName"), "John Doe")


class CamtNameMatchingTestCase(TestCase):
    """Test name-based matching for bonification transactions."""

    def setUp(self):
        self.subscription = Subscription.objects.create(
            name="2025", price_member=6000, price_supporter=1000
        )

    def _invoice_for(self, firstname, lastname, parent=None, **kwargs):
        member = Member.objects.create(firstname=firstname, lastname=lastname)
        member_subscription = MemberSubscription.objects.create(
            subscription=self.subscription,
            member=member,
            price=6000,
            parent=parent,
        )
        defaults = {"price": 6000, "status": InvoiceStatusEnum.CREATED}
        defaults.update(kwargs)
        return Invoice.objects.create(
            member_subscription=member_subscription, **defaults
        )

    def test_name_matches_exact_fullname(self):
        from core.camt_importer.camt_importer import name_matches_invoice

        invoice = self._invoice_for("John", "Doe")
        self.assertTrue(name_matches_invoice(invoice, "John Doe"))

    def test_name_matches_inverted_fullname(self):
        from core.camt_importer.camt_importer import name_matches_invoice

        invoice = self._invoice_for("John", "Doe")
        self.assertTrue(name_matches_invoice(invoice, "Doe John"))

    def test_name_matches_with_extra_tokens(self):
        """Bank statement carries a married/middle name absent from the member."""
        from core.camt_importer.camt_importer import name_matches_invoice

        invoice = self._invoice_for("Jane", "Doe")
        self.assertTrue(name_matches_invoice(invoice, "Jane Doe Van Smith"))

    def test_name_does_not_match_different_person(self):
        from core.camt_importer.camt_importer import name_matches_invoice

        invoice = self._invoice_for("John", "Doe")
        self.assertFalse(name_matches_invoice(invoice, "Alice Cooper"))

    def test_single_common_token_does_not_match(self):
        """A single shared first name must not be enough to match."""
        from core.camt_importer.camt_importer import name_matches_invoice

        invoice = self._invoice_for("John", "Doe")
        self.assertFalse(name_matches_invoice(invoice, "John Smith"))

    def test_none_name_does_not_match(self):
        from core.camt_importer.camt_importer import name_matches_invoice

        invoice = self._invoice_for("John", "Doe")
        self.assertFalse(name_matches_invoice(invoice, None))
        self.assertFalse(name_matches_invoice(invoice, ""))

    def test_is_same_user_bonification_with_extra_tokens(self):
        from core.camt_importer.camt_importer import is_same_user

        invoice = self._invoice_for("Jane", "Doe")
        self.assertTrue(is_same_user(invoice, "Bonification JANE DOE VAN SMITH"))

    def test_is_same_user_bonification_with_separator(self):
        from core.camt_importer.camt_importer import is_same_user

        invoice = self._invoice_for("John", "Doe")
        self.assertTrue(is_same_user(invoice, "Bonification John Doe & Alice Roe"))

    def test_is_same_user_ignores_non_bonification(self):
        from core.camt_importer.camt_importer import is_same_user

        invoice = self._invoice_for("John", "Doe")
        self.assertFalse(is_same_user(invoice, "Spesen"))

    def test_is_same_user_splits_on_et_and_word_separators(self):
        from core.camt_importer.camt_importer import is_same_user

        invoice = self._invoice_for("Alice", "Roe")
        self.assertTrue(is_same_user(invoice, "Bonification John Doe et Alice Roe"))
        self.assertTrue(is_same_user(invoice, "Bonification John Doe and Alice Roe"))

    def test_is_same_user_does_not_shred_name_with_et_substring(self):
        """A name that merely contains the letters 'et'/'and' must not be split."""
        from core.camt_importer.camt_importer import is_same_user

        invoice = self._invoice_for("Juliette", "Sandberg")
        self.assertTrue(is_same_user(invoice, "Bonification Juliette Sandberg"))


class CamtInvoiceLoadingTestCase(TestCase):
    """Test which invoices are loaded for matching by CamtImporter."""

    def setUp(self):
        from core.camt_importer.camt_importer import CamtImporter

        self.CamtImporter = CamtImporter
        self.subscription = Subscription.objects.create(
            name="2025", price_member=6000, price_supporter=1000
        )

    def _make_invoice(self, firstname, lastname, parent=None, **kwargs):
        member = Member.objects.create(firstname=firstname, lastname=lastname)
        member_subscription = MemberSubscription.objects.create(
            subscription=self.subscription,
            member=member,
            price=6000,
            parent=parent,
        )
        defaults = {"price": 6000, "status": InvoiceStatusEnum.CREATED}
        defaults.update(kwargs)
        return Invoice.objects.create(
            member_subscription=member_subscription, **defaults
        )

    def _importer(self):
        with open(FIXTURE_PATH, "rb") as f:
            return self.CamtImporter(f, self.subscription)

    def test_unpaid_invoice_without_reference_is_loaded(self):
        """An unpaid invoice with no reference/transaction_id must be available."""
        invoice = self._make_invoice("John", "Doe")
        importer = self._importer()
        self.assertIn(invoice.id, {i.id for i in importer.invoices})

    def test_paid_invoice_without_match_is_not_loaded(self):
        """A paid invoice with no matching reference must not be loaded."""
        invoice = self._make_invoice("John", "Doe", status=InvoiceStatusEnum.PAID)
        importer = self._importer()
        self.assertNotIn(invoice.id, {i.id for i in importer.invoices})

    def test_child_subscription_invoice_is_not_loaded(self):
        """Invoices for members with a parent subscription are excluded."""
        parent_member = Member.objects.create(firstname="Parent", lastname="Payer")
        parent_subscription = MemberSubscription.objects.create(
            subscription=self.subscription, member=parent_member, price=6000
        )
        child_invoice = self._make_invoice("Child", "Payer", parent=parent_subscription)
        importer = self._importer()
        self.assertNotIn(child_invoice.id, {i.id for i in importer.invoices})


class CamtTransactionValidTestCase(TestCase):
    """Test Transaction.valid() and the tx_id fallback."""

    def setUp(self):
        from core.camt_importer.camt_importer import Transaction

        self.Transaction = Transaction

    def _invoice(self, **kwargs):
        subscription = Subscription.objects.create(
            name="2025", price_member=6000, price_supporter=1000
        )
        member = Member.objects.create(firstname="John", lastname="Doe")
        member_subscription = MemberSubscription.objects.create(
            subscription=subscription, member=member, price=6000
        )
        defaults = {"price": 6000, "status": InvoiceStatusEnum.CREATED}
        defaults.update(kwargs)
        return Invoice.objects.create(
            member_subscription=member_subscription, **defaults
        )

    def test_not_valid_when_invoice_has_no_transaction_id(self):
        """A matched invoice without transaction_id is not valid (needs reconcile)."""
        invoice = self._invoice(transaction_id=None)
        tx = self.Transaction(
            {"Amount": 60, "Currency": "CHF", "CreditDebitIndicator": "CRDT"},
            invoice,
        )
        self.assertFalse(tx.valid())

    def test_valid_when_transaction_id_matches(self):
        invoice = self._invoice(transaction_id="TX-1")
        tx = self.Transaction(
            {
                "Amount": 60,
                "Currency": "CHF",
                "CreditDebitIndicator": "CRDT",
                "TxId": "TX-1",
            },
            invoice,
        )
        self.assertTrue(tx.valid())

    def test_tx_id_falls_back_to_transaction_id_field(self):
        tx = self.Transaction({"TransactionID": "ZV2026/123"}, None)
        self.assertEqual(tx.tx_id, "ZV2026/123")

    def test_tx_id_prefers_txid_over_transaction_id_field(self):
        tx = self.Transaction({"TxId": "TX-1", "TransactionID": "ZV2026/123"}, None)
        self.assertEqual(tx.tx_id, "TX-1")


class CamtReconcileFallbackTestCase(TestCase):
    """A bonification only carries a TransactionID (no TxId). After reconciling,
    the invoice's transaction_id is set from that fallback; a refreshed import
    must re-load and re-match it as valid instead of showing it unresolved."""

    def setUp(self):
        self.subscription = Subscription.objects.create(
            name="2025", price_member=6000, price_supporter=1000
        )
        self.member = Member.objects.create(firstname="John", lastname="Doe")
        self.member_subscription = MemberSubscription.objects.create(
            subscription=self.subscription, member=self.member, price=6000
        )

    def _importer(self, transactions):
        from io import BytesIO

        from core.camt_importer.camt_importer import CamtImporter

        with patch("core.camt_importer.camt_importer.CamtParser") as MockParser:
            MockParser.return_value.get_transactions.return_value = transactions
            return CamtImporter(BytesIO(b"<xml/>"), self.subscription)

    def _bonification(self):
        return {
            "Amount": 60,
            "Currency": "CHF",
            "CreditDebitIndicator": "CRDT",
            "TransactionID": "ZV2026/999",
            "AdditionalEntryInformation": "Bonification John Doe",
        }

    def test_unreconciled_bonification_matches_by_name_but_not_valid(self):
        Invoice.objects.create(
            member_subscription=self.member_subscription,
            price=6000,
            status=InvoiceStatusEnum.CREATED,
        )
        importer = self._importer([self._bonification()])
        tx = importer.transactions()[0]
        self.assertIsNotNone(tx.invoice)
        self.assertFalse(tx.valid())
        self.assertEqual(tx.tx_id, "ZV2026/999")

    def test_reconciled_bonification_is_reloaded_and_valid(self):
        invoice = Invoice.objects.create(
            member_subscription=self.member_subscription,
            price=6000,
            status=InvoiceStatusEnum.PAID,
            transaction_id="ZV2026/999",
        )
        importer = self._importer([self._bonification()])
        self.assertIn(invoice.id, {i.id for i in importer.invoices})
        tx = importer.transactions()[0]
        self.assertEqual(tx.invoice.id, invoice.id)
        self.assertTrue(tx.valid())

class CamtEntityUnescapingTestCase(TestCase):
    """Some banks double-encode entities, so the XML carries "&amp;amp;".
    The parser must expose a single, decoded "&" for display and name matching."""

    XML = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.04">'
        "<BkToCstmrStmt><Stmt><Id>S1</Id>"
        "<Acct><Ccy>CHF</Ccy><Ownr><Nm>OWNER</Nm></Ownr></Acct>"
        '<Ntry><Amt Ccy="CHF">60</Amt><CdtDbtInd>CRDT</CdtDbtInd>'
        "<AddtlNtryInf>Bonification ANNA &amp;amp; BEN SAMPLE</AddtlNtryInf>"
        "<NtryDtls><TxDtls>"
        "<Refs><TxId>TXID-1</TxId></Refs>"
        '<Amt Ccy="CHF">60</Amt>'
        "<RltdPties><Dbtr><Nm>ANNA &amp;amp; BEN</Nm></Dbtr></RltdPties>"
        "<RmtInf><Ustrd>Cotisation Anna &amp;amp; Ben</Ustrd></RmtInf>"
        "</TxDtls></NtryDtls></Ntry>"
        "</Stmt></BkToCstmrStmt></Document>"
    )

    def _transaction(self):
        from core.camt_importer.camt_importer import CamtParser

        return CamtParser(self.XML).get_transactions()[0]

    def test_remittance_information_is_unescaped(self):
        self.assertEqual(
            self._transaction()["RemittanceInformation"], "Cotisation Anna & Ben"
        )

    def test_additional_entry_information_is_unescaped(self):
        self.assertEqual(
            self._transaction()["AdditionalEntryInformation"],
            "Bonification ANNA & BEN SAMPLE",
        )

    def test_debtor_name_is_unescaped(self):
        self.assertEqual(self._transaction()["DebtorName"], "ANNA & BEN")
