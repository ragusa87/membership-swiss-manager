from django.contrib.auth.middleware import RemoteUserMiddleware


class AuthcrunchRemoteUserMiddleware(RemoteUserMiddleware):
    """
    Middleware that authenticates users based on a custom header set by proxy
    See https://docs.authcrunch.com/docs/authorize/headers#pass-jwt-token-claims-in-http-request-headers
    """

    header = "X-Token-User-Email"
