from cryptography.fernet import Fernet

from project.local import DEBUG, SECRET_KEY, SIGNATURE, SMTP

ALLOWED_HOSTS = []
AUTH_PASSWORD_VALIDATORS = []
INSTALLED_APPS = ["app", "django_extensions"]
MIDDLEWARE = []
TEMPLATES = []

DATABASES = {
    'default': {
        'ENGINE': "django.db.backends.postgresql_psycopg2",
        'NAME': "old_sub" if DEBUG else "subreply",
        'USER': "postgres",
        'PASSWORD': "postgres",
        'HOST': "",
        'PORT': "6432"
    }
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = False
USE_L10N = False
USE_TZ = False

# cookies
F = Fernet(SIGNATURE.encode())
MAX_AGE = 3600 * 24 * 365

SLURS = ["nigger", "fuck", "cunt", "stupid", "whore", "hitler"]

# registration
INVALID = [
    "register", "login", "logout", "feed", "following", "followers",
    "sub", "subcafe", "sublevel", "luc", "lm", "lucianmarin",
    "re", "reply", "api", "local", "search", "settings",
    "profile", "reset", "password", "delete", "timeline",
    "about", "static", "media", "terms", "privacy", "policy",
    "requests", "invitations", "people", "trends", "trending",
    "links", "mentions", "pins", "saves",
    "linked", "mentioned", "pinned", "saved",
    "link", "mention", "pin", "save"
]
