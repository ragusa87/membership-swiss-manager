import os

from core.models import Subscription
from core.tests.test_common import LoggedInTestCase


class PdfsTestCase(LoggedInTestCase):
    def test_camt_import(self):
        self.subscription = Subscription.objects.create(
            name="2025", price_member=4200, price_supporter=1100
        )
        file_path = os.path.join(os.path.dirname(__file__), "camt-demo.xml")
        with open(file_path, "rb") as f:
            response = self.client.post(
                "/import-camt",
                data={
                    "camt_file": f,
                    "subscription": self.subscription.pk,
                },
                follow=True,
            )

        self.assertEqual(200, response.status_code)

        self.assertContains(response, "ACCOUNT OWNER => PAYER 1")
        self.assertContains(response, "TXID-XXXX-1")
        self.assertContains(response, "Payment details 1")
        self.assertContains(response, "Resolve? 60.00 CHF Bonification PAYER 1")

        self.assertContains(response, "ACCOUNT OWNER => PAYER 2")
        self.assertContains(response, "TXID-XXXX-2")
        self.assertContains(response, "Payment details 2")
        self.assertContains(response, "Resolve? 60.00 CHF Bonification PAYER 2")
