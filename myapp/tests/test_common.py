from django.test import TestCase
from django.contrib.auth.models import User


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
