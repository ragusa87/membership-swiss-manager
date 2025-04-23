from django.conf import settings
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import User


class SettingsBackend(BaseBackend):
    """
    Always authenticate with the username "admin" with any password
    """

    def authenticate(self, request, username=None, password=None):
        expected_username = getattr(settings, "ADMIN_LOGIN", "admin")
        expected_password = getattr(settings, "ADMIN_PASSWORD", "admin")
        pwd_valid = check_password(password, make_password(expected_password))
        if username != expected_username or not pwd_valid:
            return None

        try:
            user = User.objects.get(username=expected_username)
        except User.DoesNotExist:
            user = User(username=expected_username)
            user.is_staff = True
            user.is_superuser = True
            user.save()
        return user

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
