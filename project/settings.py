from cryptography.fernet import Fernet

from project.local import DEBUG, SIGNATURE, SMTP

ALLOWED_HOSTS = []
AUTH_PASSWORD_VALIDATORS = []
INSTALLED_APPS = ["app", "django_extensions"]
MIDDLEWARE = []
PASSWORD_HASHERS = []
STORAGES = {}
TEMPLATES = []
STATICFILES_FINDERS = []
FILE_UPLOAD_HANDLERS = []

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

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

FERNET = Fernet(SIGNATURE.encode())
MAX_AGE = 3600 * 24 * 365

DEBUG = DEBUG
SMTP = SMTP
