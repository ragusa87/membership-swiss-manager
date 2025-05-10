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
