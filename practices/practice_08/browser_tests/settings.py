import os
from pathlib import Path

from bookshare.settings import *  # noqa: F403

RUNTIME = Path(os.environ["BOOKSHARE_BROWSER_RUNTIME"])
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": RUNTIME / "db.sqlite3",
        "OPTIONS": {"transaction_mode": "IMMEDIATE"},
    },
}
MEDIA_ROOT = RUNTIME / "media"
