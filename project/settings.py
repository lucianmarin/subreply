from cryptography.fernet import Fernet
from project.local import DEBUG, SIGNATURE, SECRET_KEY

ALLOWED_HOSTS = []
INSTALLED_APPS = ["app", "django_extensions"]
MIDDLEWARE = []
TEMPLATES = []

DATABASES = {
    'default': {
        'ENGINE': "django.db.backends.postgresql_psycopg2",
        'NAME': "subreply",
        'USER': "postgres",
        'PASSWORD': "postgres",
        'HOST': "",
        'PORT': "6432"
    }
}
AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = False
USE_L10N = False
USE_TZ = False

F = Fernet(SIGNATURE.encode())
MAX_AGE = 3600 * 24 * 365
INVALID = [
    "register", "login", "logout", "feed", "following", "followers",
    "dubfi", "newsfi", "api", "local", "search", "settings",
    "profile", "erase", "password", "delete", "timeline",
    "about", "static", "media", "terms", "privacy", "policy",
    "links", "mentions", "pins", "saves",
    "linked", "mentioned", "pinned", "saved",
    "link", "mention", "pin", "save"
]
