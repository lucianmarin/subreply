from cryptography.fernet import Fernet

from project.local import DEBUG, SECRET_KEY, SIGNATURE, SMTP

ALLOWED_HOSTS = []
AUTH_PASSWORD_VALIDATORS = []
INSTALLED_APPS = ["app", "django_extensions"]
MIDDLEWARE = []
TEMPLATES = []

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

# if DEBUG:
#     DATABASES = {
#         'default': {
#             'ENGINE': 'django.db.backends.sqlite3',
#             'NAME': 'local.db',
#         }
#     }

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = False
USE_L10N = False
USE_TZ = False

# cookies
FERNET = Fernet(SIGNATURE.encode())
MAX_AGE = 3600 * 24 * 365

SLURS = ["nigger", "fuck", "cunt", "stupid", "whore", "hitler"]

# registration
INVALID = [
    "about",
    "account",
    "api",
    "change",
    "delete",
    "discover",
    "edit",
    "emoji",
    "feed",
    "followers",
    "following",
    "invitations",
    "joined",
    "link",
    "linked",
    "links",
    "lm",
    "local",
    "login",
    "logout",
    "luc",
    "lucianmarin",
    "media",
    "mention",
    "mentioned",
    "mentions",
    "options",
    "password",
    "people",
    "pin",
    "pinned",
    "pins",
    "policy",
    "privacy",
    "profile",
    "re",
    "register",
    "reply",
    "replying",
    "requests",
    "reset",
    "save",
    "saved",
    "saves",
    "search",
    "seen",
    "set",
    "settings",
    "social",
    "static",
    "sub",
    "subcafe",
    "sublevel",
    "terms",
    "timeline",
    "trending",
    "trends",
    "unlock"
]
