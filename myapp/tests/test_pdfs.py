import io

from myapp.models import Subscription, Invoice, Member, MemberSubscription
from myapp.tests.test_common import LoggedInTestCase
from PyPDF2 import PdfReader


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

        self.assertIn("Prix conseillé: 11.0 CHF", text)
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

        self.assertIn("Montant\nCHF 11.00", text)
        self.assertIn("JohnDoe", text)
        self.assertIn("CH93 0076 2011 6238 5295 7", text)
