from django.contrib.auth.models import User
from django.test import TestCase
from bs4 import BeautifulSoup
from myapp.models import Subscription


class LoggedInTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            password="password",
            is_staff=True,
            is_superuser=True,
            is_active=True,
        )
        # Log in the user (assuming you have a user with username 'testuser')
        self.client.force_login(self.user)


class DashboardTestCase(LoggedInTestCase):
    def test_index_redirect(self):
        self.subscription = Subscription.objects.create(name="2025")

        response = self.client.get("/")
        self.assertRedirects(response, "/dashboard/2025", fetch_redirect_response=False)

    def test_index_redirect_no_subscription(self):
        response = self.client.get("/")
        self.assertRedirects(response, "/admin", fetch_redirect_response=False)

    def test_dashboard_content(self):
        self.subscription = Subscription.objects.create(name="2025")
        response = self.client.get("/dashboard/2025")
        assert response.status_code == 200

        parser = BeautifulSoup(response.content.decode("utf-8"), features="html.parser")
        growth = parser.select_one('[data-test="subscription_growth"]')
        assert growth is not None
        assert growth.string == "100%"
