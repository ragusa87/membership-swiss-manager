from django.contrib.auth.backends import RemoteUserBackend
from django.contrib.auth.middleware import RemoteUserMiddleware


class AuthcrunchRemoteUserMiddleware(RemoteUserMiddleware):
    """
    Middleware that authenticates users based on a custom header set by proxy
    See https://docs.authcrunch.com/docs/authorize/headers#pass-jwt-token-claims-in-http-request-headers
    """

    header = "HTTP_X_TOKEN_USER_NAME"


class AuthcrunchRemoteUserBackend(RemoteUserBackend):
    role_header = "HTTP_X_TOKEN_USER_ROLES"
    admin_role = "authp/admin"

    def configure_user(self, request, user, created=True):
        user = super().configure_user(request, user, created)

        user.is_staff = True
        user.is_active = True

        roles = request.META.get(self.role_header, "").split(" ")

        if self.admin_role in roles:
            user.is_superuser = True

        return user
