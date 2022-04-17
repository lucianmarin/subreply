from cryptography.fernet import Fernet

from project.local import DEBUG, SECRET_KEY, SIGNATURE, SMTP

ALLOWED_HOSTS = []
AUTH_PASSWORD_VALIDATORS = []
INSTALLED_APPS = ["app", "django_extensions"]
MIDDLEWARE = []
TEMPLATES = []

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

DEBUG = DEBUG
SECRET_KEY = SECRET_KEY
SMTP = SMTP

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "NAME": "subreply",
        "USER": "postgres",
        "PASSWORD": "postgres",
        "HOST": "",
        "PORT": "6432",
    }
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = False
USE_L10N = False
USE_TZ = False

# cookies
FERNET = Fernet(SIGNATURE.encode())
MAX_AGE = 3600 * 24 * 365

# registration
INVALID = [
    "about",
    "account",
    "api",
    "delete",
    "discover",
    "edit",
    "emoji",
    "feed",
    "followers",
    "following",
    "invites",
    "lm",
    "lobby",
    "login",
    "logout",
    "luc",
    "lucianmarin",
    "media",
    "mention",
    "mentioned",
    "mentions",
    "options",
    "news",
    "password",
    "people",
    "policy",
    "privacy",
    "profile",
    "re",
    "request",
    "reply",
    "replying",
    "reset",
    "save",
    "saved",
    "saves",
    "search",
    "settings",
    "social",
    "static",
    "sub",
    "subcafe",
    "sublevel",
    "terms",
    "timeline",
    "trending",
    "unlock"
]
