"""
Django settings for the sign360 project.

Segueix les mateixes convencions que `avsis-customers-backend`: configuració via
`python-decouple` (fitxer `.env`), PostgreSQL, DRF amb TokenAuthentication i
Celery per a les tasques en segon pla.
"""

import os
from pathlib import Path

from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config("SECRET_KEY", default="Unsafe-default-key")
DEBUG = config("DEBUG", default=True, cast=bool)

MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")
DOMAIN_MEDIA = config("DOMAIN_MEDIA", default="")

# El revers proxy (nginx/traefik) acaba el TLS; sense això Django veu la connexió
# HTTP interna i genera URLs http://
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True

DOCUMENT_MANAGER_BASE_PATH = config("DOCUMENT_MANAGER_PATH", default=BASE_DIR)
DOCUMENT_STORAGE_PATH = os.path.join(DOCUMENT_MANAGER_BASE_PATH, "media", "documents")

allowed_hosts_str = config("ALLOWED_HOSTS", default="*")
ALLOWED_HOSTS = [host.strip() for host in allowed_hosts_str.split(",")]

CSRF_TRUSTED_ORIGINS = config("CSRF_TRUSTED_ORIGINS", default="http://localhost:3000").split(",")

ENV = config("ENV", default="local")
LANGUAGE = config("LANGUAGE", default="ca")

# Mida màxima acceptada en pujar un document (bytes)
DOCUMENT_MAX_UPLOAD_SIZE = config("DOCUMENT_MAX_UPLOAD_SIZE", default=20 * 1024 * 1024, cast=int)

# Certificat PFX per al segellat opcional dels PDF (pyHanko)
PFX_PASS = config("PFX_PASS", default="")
PFX_PATH = config("PFX_PATH", default="")

# API externa de signatura (Aqua360 Sign), mateixa que fa servir avsis-customers
SIGNING_BASE_URL = config("SIGNING_BASE_URL", default="")
SIGNING_API_KEY = config("SIGNING_API_KEY", default="")
SIGNING_CALLBACK_URL = config("SIGNING_CALLBACK_URL", default="")
SIGNING_TIMEOUT = config("SIGNING_TIMEOUT", default=30, cast=int)
# Clau que ha d'enviar el proveïdor a la capçalera X-API-Key del callback.
# Si es deixa buida, el callback no es valida (només recomanable en local).
SIGN_CALLBACK_API_KEY = config("SIGN_CALLBACK_API_KEY", default="")

OWN_APPS = [
    "auth_sign360",
    "documentmanager",
    "integrations",
]

EXTRA_APPS = [
    "rest_framework",
    "rest_framework.authtoken",
    "corsheaders",
    "django_filters",
]

INSTALLED_APPS = (
    [
        "django.contrib.admin",
        "django.contrib.auth",
        "django.contrib.contenttypes",
        "django.contrib.sessions",
        "django.contrib.messages",
        "django.contrib.staticfiles",
        "django_extensions",
    ]
    + EXTRA_APPS
    + OWN_APPS
)

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "sign360.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "sign360.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DATABASE_NAME", default="sign360"),
        "USER": config("DATABASE_USER", default="sign360"),
        "PASSWORD": config("DATABASE_PASSWORD", default="sign360"),
        "HOST": config("DATABASE_HOST", default="localhost"),
        "PORT": config("DATABASE_PORT", default="5432"),
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = LANGUAGE
TIME_ZONE = config("TIME_ZONE", default="Europe/Madrid")
USE_I18N = True
USE_TZ = True

LOCALE_PATHS = [os.path.join(BASE_DIR, "locale")]

STATIC_URL = "static/"
STATIC_ROOT = os.path.join(BASE_DIR, "static")

REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework.authentication.TokenAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
}

CORS_ALLOW_ALL_ORIGINS = config("CORS_ALLOW_ALL_ORIGINS", default=True, cast=bool)
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in config("CORS_ALLOWED_ORIGINS", default="").split(",")
    if origin.strip()
]
CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
    "x-api-key",
]

CELERY_BROKER_URL = config("CELERY_BROKER_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = "django-db"
CELERY_TRACK_STARTED = True
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
INSTALLED_APPS += ["django_celery_results"]

LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {name} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.path.join(LOG_DIR, "sign360.log"),
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 5,
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console", "file"],
        "level": config("LOG_LEVEL", default="INFO"),
    },
}
