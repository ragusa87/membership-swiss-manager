import os

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


def _upload_fixture(client, subscription):
    with open(FIXTURE_PATH, "rb") as f:
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
