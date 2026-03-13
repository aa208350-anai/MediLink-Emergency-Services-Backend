import io
import sys
import logging
from pathlib import Path
from datetime import timedelta

from decouple import config, Csv
import dj_database_url

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# -------------------------------------------------------------------------------
# BASE
# -------------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = config("DJANGO_SECRET_KEY") 
DEBUG      = config("DEBUG", default=False, cast=bool)

# -------------------------------------------------------------------------------
# HOSTS & ORIGINS
# -------------------------------------------------------------------------------

ALLOWED_HOSTS = config(
    "ALLOWED_HOSTS",
    default="localhost,127.0.0.1",
    cast=Csv(),
)

CSRF_TRUSTED_ORIGINS = config(
    "CSRF_TRUSTED_ORIGINS",
    default="http://localhost:3000,http://127.0.0.1:3000",
    cast=Csv(),
)

# -------------------------------------------------------------------------------
# INSTALLED APPS
# -------------------------------------------------------------------------------

INSTALLED_APPS = [
    "daphne",                                   
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "whitenoise.runserver_nostatic",             
    "django.contrib.staticfiles",
    # Third-party
    "nested_admin",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "auditlog",
    "cloudinary_storage",
    "cloudinary",
    "dal",
    "dal_select2",
    "channels",
    "django_filters",                            

    # Local
    "apps.accounts",
    "apps.ambulances",
    "apps.bookings",
    "apps.hospitals",
]

# -------------------------------------------------------------------------------
# MIDDLEWARE
# -------------------------------------------------------------------------------

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",   # Must follow SecurityMiddleware
    "corsheaders.middleware.CorsMiddleware",        # Must precede CommonMiddleware
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF     = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# -------------------------------------------------------------------------------
# SECURITY
# Render terminates SSL at its load balancer and forwards to Django as plain
# HTTP internally — trust the injected header, never redirect from Django.
# -------------------------------------------------------------------------------

SECURE_PROXY_SSL_HEADER         = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT             = False
SESSION_COOKIE_SECURE           = not DEBUG
CSRF_COOKIE_SECURE              = not DEBUG
SECURE_BROWSER_XSS_FILTER       = True
SECURE_CONTENT_TYPE_NOSNIFF     = True
X_FRAME_OPTIONS                 = "DENY"
SECURE_HSTS_SECONDS             = 0 if DEBUG else 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS  = not DEBUG
SECURE_HSTS_PRELOAD             = not DEBUG

# -------------------------------------------------------------------------------
# CORS
# -------------------------------------------------------------------------------

CORS_ALLOW_CREDENTIALS = True

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
]

if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True
else:
    CORS_ALLOW_ALL_ORIGINS = False
    CORS_ALLOWED_ORIGINS   = config(
        "CORS_ALLOWED_ORIGINS",
        default="",
        cast=Csv(),
    )

# -------------------------------------------------------------------------------
# DATABASE
# -------------------------------------------------------------------------------

# DATABASE_URL = config("DATABASE_URL", default=None)
DATABASE_URL = config("DATABASE_URL", default="postgres://postgres:Regina0755447874@localhost:5432/medilink")

if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
            ssl_require=config("DATABASE_SSL_REQUIRE", default=not DEBUG, cast=bool),
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# -------------------------------------------------------------------------------
# TEMPLATES
# -------------------------------------------------------------------------------

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
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

# -------------------------------------------------------------------------------
# AUTHENTICATION
# -------------------------------------------------------------------------------

AUTH_USER_MODEL = "accounts.CustomUser"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# -------------------------------------------------------------------------------
# JWT
# -------------------------------------------------------------------------------

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME":    timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME":   timedelta(days=30),
    "ROTATE_REFRESH_TOKENS":    True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN":        True,
    "AUTH_HEADER_TYPES":        ("Bearer",),
    "ALGORITHM":                "HS256",
    "SIGNING_KEY":              SECRET_KEY,
}

# -------------------------------------------------------------------------------
# REST FRAMEWORK
# -------------------------------------------------------------------------------

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.AllowAny",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 10,
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.ScopedRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "anon":          "100/min",
        "user":          "60/min",
        "login":         "10/min",
        "login_ip":      "20/min",
        "register":      "5/hour",
        "refresh_token": "20/min",
        "logout":        "10/min",
    },
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
    ),
    "DEFAULT_PARSER_CLASSES": (
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.FormParser",
        "rest_framework.parsers.MultiPartParser",
    ),
    "EXCEPTION_HANDLER": "rest_framework.views.exception_handler",
}

# -------------------------------------------------------------------------------
# STATIC & MEDIA FILES
# -------------------------------------------------------------------------------

STATIC_URL  = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"] if (BASE_DIR / "static").exists() else []

MEDIA_URL  = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# -------------------------------------------------------------------------------
# CLOUDINARY
# -------------------------------------------------------------------------------

CLOUDINARY_CLOUD_NAME = config("CLOUDINARY_CLOUD_NAME", default="")
CLOUDINARY_API_KEY    = config("CLOUDINARY_API_KEY",    default="")
CLOUDINARY_API_SECRET = config("CLOUDINARY_API_SECRET", default="")

USE_CLOUDINARY = bool(CLOUDINARY_CLOUD_NAME and CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET)

if USE_CLOUDINARY:
    import cloudinary
    cloudinary.config(
        cloud_name=CLOUDINARY_CLOUD_NAME,
        api_key=CLOUDINARY_API_KEY,
        api_secret=CLOUDINARY_API_SECRET,
        secure=True,
    )
    CLOUDINARY_STORAGE = {
        "CLOUD_NAME": CLOUDINARY_CLOUD_NAME,
        "API_KEY":    CLOUDINARY_API_KEY,
        "API_SECRET": CLOUDINARY_API_SECRET,
        "SECURE":     True,
        "TYPE":       "upload",
        "INVALIDATE": True,
    }
    _default_storage = "cloudinary_storage.storage.MediaCloudinaryStorage"
else:
    _default_storage = "django.core.files.storage.FileSystemStorage"

STORAGES = {
    "default":    {"BACKEND": _default_storage},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}

# -------------------------------------------------------------------------------
# EMAIL
# -------------------------------------------------------------------------------

RESEND_API_KEY     = config("RESEND_API_KEY", default="")
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="Medilink <onboarding@resend.dev>")
SERVER_EMAIL       = DEFAULT_FROM_EMAIL   # used for error emails to ADMINS
FRONTEND_URL       = config("FRONTEND_URL", default="http://localhost:3000")

# Switch backends per environment so local dev never hits Resend.
# Set EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend in .env
# for local, leave unset in production and this default takes over.
EMAIL_BACKEND = config(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.smtp.EmailBackend",
)

EMAIL_HOST          = "smtp.resend.com"
EMAIL_PORT          = 587
EMAIL_USE_TLS       = True
EMAIL_HOST_USER     = "resend"          # Resend requires the literal string "resend"
EMAIL_HOST_PASSWORD = RESEND_API_KEY
EMAIL_TIMEOUT       = 10               # seconds — avoids hanging requests on SMTP failure

# -------------------------------------------------------------------------------
# REDIS  (single URL drives both Channels and Celery)
#   Local:      redis://127.0.0.1:6379/0
#   Docker:     redis://redis:6379/0
#   Production: rediss://default:password@host:port  (Upstash / Redis Cloud)
# -------------------------------------------------------------------------------

REDIS_URL = config("REDIS_URL", default="redis://127.0.0.1:6379/0")

#  Django Channels 

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG":  {"hosts": [REDIS_URL]},
    },
}

#  Celery 

CELERY_BROKER_URL                 = REDIS_URL
CELERY_RESULT_BACKEND             = REDIS_URL
CELERY_ACCEPT_CONTENT             = ["json"]
CELERY_TASK_SERIALIZER            = "json"
CELERY_RESULT_SERIALIZER          = "json"
CELERY_TIMEZONE                   = config("TIME_ZONE", default="Africa/Kampala")
CELERY_TASK_TRACK_STARTED         = True
CELERY_TASK_TIME_LIMIT            = 30 * 60   # hard kill after 30 min
CELERY_TASK_SOFT_TIME_LIMIT       = 25 * 60   # raises SoftTimeLimitExceeded at 25 min
CELERY_WORKER_PREFETCH_MULTIPLIER = 1         # prevents one worker hoarding long tasks
CELERY_TASK_ACKS_LATE             = True      # re-queue task if worker crashes mid-run
CELERY_RESULT_EXPIRES             = 60 * 60   # clean up results after 1 hour

# -------------------------------------------------------------------------------
# LOGGING
# -------------------------------------------------------------------------------

(BASE_DIR / "logs").mkdir(exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {name} {module}:{lineno} {message}",
            "style": "{",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "simple": {"format": "{levelname} {message}", "style": "{"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
            "level": "DEBUG" if DEBUG else "INFO",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": BASE_DIR / "logs" / "django.log",
            "maxBytes": 1024 * 1024 * 5,   # 5 MB
            "backupCount": 5,
            "formatter": "verbose",
            "level": "INFO",
        },
    },
    "loggers": {
        "django":         {"handlers": ["console"],          "level": "INFO",                      "propagate": False},
        "django.request": {
            "handlers": ["console", "file"],  
            "level": "ERROR",                   
            "propagate": False
        },
        "apps":           {"handlers": ["console", "file"],  "level": "DEBUG" if DEBUG else "INFO", "propagate": False},
        "channels":       {"handlers": ["console"],          "level": "DEBUG" if DEBUG else "INFO", "propagate": False},
        "daphne":         {"handlers": ["console"],          "level": "INFO",                      "propagate": False},
    },
    "root": {"handlers": ["console"], "level": "DEBUG" if DEBUG else "INFO"},
}

# -------------------------------------------------------------------------------
# INTERNATIONALISATION & MISC
# -------------------------------------------------------------------------------

LANGUAGE_CODE      = "en-us"
TIME_ZONE          = config("TIME_ZONE", default="Africa/Kampala")
USE_I18N           = True
USE_TZ             = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# -------------------------------------------------------------------------------
# DEV DIAGNOSTICS
# -------------------------------------------------------------------------------

if DEBUG:
    print(f"\n{'='*50}")
    print(f"🔧 Mode:       DEVELOPMENT")
    print(f"🗄️  Database:   {'PostgreSQL' if DATABASE_URL else 'SQLite'}")
    print(f"☁️  Cloudinary: {'Enabled' if USE_CLOUDINARY else 'Disabled'}")
    print(f"📧 From email: {DEFAULT_FROM_EMAIL}")
    print(f"🌐 Frontend:   {FRONTEND_URL}")
    print(f"{'='*50}\n")