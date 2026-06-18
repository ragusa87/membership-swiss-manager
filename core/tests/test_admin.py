from core.models import Invoice, Member, MemberSubscription, Subscription
from core.tests.test_common import LoggedInTestCase


class AdminChangelistSmokeTest(LoggedInTestCase):
    def setUp(self):
        super().setUp()
        self.subscription = Subscription.objects.create(
            name="2025", price_member=4200, price_supporter=1100
        )
        self.member = Member.objects.create(
            firstname="John",
            lastname="Doe",
            email="john@example.com",
            phone="+41791234567",
            address="Rue de l'Exemple",
            address_number="42",
            zip="1000",
            city="Lausanne",
        )
        self.member_subscription = MemberSubscription.objects.create(
            subscription=self.subscription, member=self.member, price=4200
        )
        self.invoice = Invoice.objects.create(
            member_subscription=self.member_subscription, price=4200
        )

    def test_member_changelist(self):
        response = self.client.get("/admin/core/member/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Rue de l&#x27;Exemple 42 1000 Lausanne")

    def test_member_changelist_filtered_by_id(self):
        response = self.client.get(f"/admin/core/member/?id={self.member.pk}")
        self.assertEqual(response.status_code, 200)

    def test_membersubscription_changelist(self):
        response = self.client.get("/admin/core/membersubscription/")
        self.assertEqual(response.status_code, 200)

    def test_subscription_changelist(self):
        response = self.client.get("/admin/core/subscription/")
        self.assertEqual(response.status_code, 200)

    def test_invoice_changelist(self):
        response = self.client.get("/admin/core/invoice/")
        self.assertEqual(response.status_code, 200)
