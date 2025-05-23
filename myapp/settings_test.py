from . import settings
import tempfile

globals().update({k: v for k, v in vars(settings).items() if k.isupper()})

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
