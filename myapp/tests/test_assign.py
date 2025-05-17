from myapp.models import Subscription, Member, MemberSubscription
from myapp.tests.test_common import LoggedInTestCase
from django.utils.translation import gettext_lazy as _


class PdfsTestCase(LoggedInTestCase):
    def setUp(self):
        self.subscription = Subscription.objects.create(
            name="2025", price_member=4200, price_supporter=1100
        )
        self.member = Member.objects.create(firstname="JohnDoe")
        self.member2 = Member.objects.create(firstname="JanePoe")
        self.member_subscription = MemberSubscription.objects.create(
            subscription=self.subscription, member=self.member, price=1100
        )

    def test_assign(self):
        response = self.client.get(f"/assign/{self.subscription.name}")
        self.assertEqual(200, response.status_code)

        # Spinner class works
        self.assertContains(
            response, '<svg class="icon inline-block text-blue-500 animate-spin"'
        )

        # Assign not linked member
        self.assertContains(response, "Link JanePoe")
        # Can not assign lined member
        self.assertNotContains(response, "Link JohnDoe")

        # JohnDoe is listed as assigned
        self.assertContains(
            response, '<a href="/admin/myapp/member/1/change/">JohnDoe</a>'
        )

    def test_create_member(self):
        data = dict(
            form="create",
            firstname="new user",
            lastname="",
            email="",
            phone="",
            address="",
            address_number="",
            city="",
            zip="",
        )
        response = self.client.post(f"/assign/{self.subscription.name}", data=data)
        self.assertEqual(302, response.status_code)
        self.assertTrue(Member.objects.filter(firstname="new user").exists())

    def test_link_member(self):
        prefix = f"link_member_{self.member2.pk}-"
        data = {
            prefix + "type": "member",
            prefix + "parent": "",
            "form": "link",
        }
        self.assertFalse(
            MemberSubscription.objects.filter(member=self.member2).exists()
        )
        response = self.client.post(f"/assign/{self.subscription.name}", data=data)
        self.assertEqual(302, response.status_code)
        self.assertTrue(MemberSubscription.objects.filter(member=self.member2).exists())
        subscription = MemberSubscription.objects.filter(member=self.member2).first()
        self.assertEqual(subscription.get_type_text(), _("subscription.member"))

    def test_search(self):
        Member.objects.create(firstname="userA")
        Member.objects.create(firstname="userB")
        Member.objects.create(firstname="userC")

        response = self.client.get(f"/assign/{self.subscription.name}?q=userB")
        self.assertContains(response, "userB")
        self.assertNotContains(response, "userA")
        self.assertNotContains(response, "userC")
