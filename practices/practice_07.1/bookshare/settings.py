import os
from pathlib import Path
from urllib.parse import urlsplit

from django.core.exceptions import ImproperlyConfigured
from django.core.management.utils import get_random_secret_key

BASE_DIR = Path(__file__).resolve().parent.parent
DEBUG = os.getenv("BOOKSHARE_DEBUG", "1") == "1"
SECRET_KEY = os.getenv("BOOKSHARE_SECRET_KEY")
PUBLIC_URL = os.getenv("BOOKSHARE_PUBLIC_URL", "http://127.0.0.1:8000").rstrip("/")

if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured("Set BOOKSHARE_SECRET_KEY.")
    secret_path = BASE_DIR / ".local-secret"
    try:
        with secret_path.open("x", encoding="utf-8") as secret_file:
            secret_file.write(get_random_secret_key())
    except FileExistsError:
        pass
    SECRET_KEY = secret_path.read_text(encoding="utf-8")

public_host = urlsplit(PUBLIC_URL).hostname
if not DEBUG and (urlsplit(PUBLIC_URL).scheme != "https" or not public_host):
    raise ImproperlyConfigured("Set BOOKSHARE_PUBLIC_URL to the public HTTPS origin.")

ALLOWED_HOSTS = ["127.0.0.1", "localhost", "[::1]"] if DEBUG else [public_host]
ROOT_URLCONF = "bookshare.urls"
INSTALLED_APPS = [
    "django.contrib.auth", "django.contrib.contenttypes", "django.contrib.sessions",
    "django.contrib.messages", "django.contrib.staticfiles", "books",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]
DATABASES = {"default": {
    "ENGINE": "django.db.backends.sqlite3",
    "NAME": BASE_DIR / "db.sqlite3",
    "OPTIONS": {"transaction_mode": "IMMEDIATE"},
}}
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": f"django.contrib.auth.password_validation.{validator}"}
    for validator in (
        "UserAttributeSimilarityValidator", "MinimumLengthValidator",
        "CommonPasswordValidator", "NumericPasswordValidator",
    )
]
LANGUAGE_CODE = "ru"
TIME_ZONE = "Europe/Moscow"
USE_TZ = True
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "catalog"
LOGOUT_REDIRECT_URL = "catalog"
SESSION_COOKIE_SECURE = CSRF_COOKIE_SECURE = not DEBUG
SECURE_SSL_REDIRECT = not DEBUG
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

EMAIL_BACKEND = (
    "django.core.mail.backends.filebased.EmailBackend" if DEBUG
    else "django.core.mail.backends.smtp.EmailBackend"
)
EMAIL_FILE_PATH = BASE_DIR / "mail"
EMAIL_HOST = os.getenv("BOOKSHARE_SMTP_HOST", "localhost")
EMAIL_PORT = int(os.getenv("BOOKSHARE_SMTP_PORT", "587"))
EMAIL_HOST_USER = os.getenv("BOOKSHARE_SMTP_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("BOOKSHARE_SMTP_PASSWORD", "")
EMAIL_USE_TLS = True
EMAIL_TIMEOUT = 10
DEFAULT_FROM_EMAIL = os.getenv("BOOKSHARE_FROM_EMAIL", "books@localhost")
