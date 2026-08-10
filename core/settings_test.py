import tempfile

from . import settings

globals().update({k: v for k, v in vars(settings).items() if k.isupper()})

# debug_toolbar refuses to run under tests (DEBUG is forced to False by the test
# runner). settings.py may have added it to INSTALLED_APPS/MIDDLEWARE when
# APP_DEBUG=1, so strip it back out here regardless of the environment.
ENABLE_DEBUG_TOOLBAR = False
INSTALLED_APPS = [app for app in settings.INSTALLED_APPS if app != "debug_toolbar"]
MIDDLEWARE = [
    mw
    for mw in settings.MIDDLEWARE
    if mw != "debug_toolbar.middleware.DebugToolbarMiddleware"
]

SECURE_SSL_REDIRECT = False
SECRET_KEY = "test-secret-key"
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

MEDIA_ROOT = tempfile.mkdtemp()
DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"
INVOICE_IBAN = "CH93 0076 2011 6238 5295 7"
INVOICE_LANGUAGE = "en"
