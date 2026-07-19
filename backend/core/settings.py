"""
Django settings for EMR project.

EMR Rule Compliance:
- Visit-scoped architecture enforced via middleware
- Payment enforcement via PaymentClearedGuard
- Role-based access control enforced
"""

import os
from pathlib import Path

# Load environment variables from .env file
try:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from load_env import load_env_file

    load_env_file()
except ImportError:
    # If load_env.py doesn't exist, continue without it
    pass

# Build paths inside the project
BACKEND_DIR = Path(__file__).resolve().parent.parent
# Monorepo root when frontend/ exists beside backend/; otherwise backend-only (Docker).
_candidate_repo_root = BACKEND_DIR.parent
BASE_DIR = (
    _candidate_repo_root
    if (_candidate_repo_root / "frontend").is_dir()
    else BACKEND_DIR
)
# Writable runtime paths (static, media, logs, backups) — always under BACKEND_DIR
# so Docker WORKDIR /app matches volume mounts (e.g. media_data:/app/media).
DATA_DIR = Path(os.environ.get("EMR_DATA_DIR", str(BACKEND_DIR)))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get("SECRET_KEY", "django-insecure-change-in-production")
DEBUG = os.environ.get("DEBUG", "False") == "True"

# Rate limiting (off by default in DEBUG so local/Playwright E2E is not blocked at 5 logins/min)
RATE_LIMIT_ENABLED = os.environ.get(
    "RATE_LIMIT_ENABLED", "False" if DEBUG else "True"
) == "True"

# Clinic-grade: refuse to run in production with default/insecure SECRET_KEY
_INSECURE_DEFAULT_KEY = "django-insecure-change-in-production"
if not DEBUG and (
    not SECRET_KEY or SECRET_KEY == _INSECURE_DEFAULT_KEY or len(SECRET_KEY) < 32
):
    raise ValueError(
        "Production requires a strong SECRET_KEY (e.g. openssl rand -hex 32). "
        "Do not use the default or a short key."
    )

ALLOWED_HOSTS = (
    os.environ.get("ALLOWED_HOSTS", "").split(",")
    if os.environ.get("ALLOWED_HOSTS")
    else ["localhost", "127.0.0.1"]
)

# Public self-registration (/api/v1/auth/register/)
PUBLIC_REGISTRATION_ENABLED = os.environ.get(
    "PUBLIC_REGISTRATION_ENABLED", "true"
).lower() in ("true", "1", "yes")
_default_public_registration_roles = (
    "PATIENT"
    if not DEBUG
    else "PATIENT,DOCTOR,NURSE,LAB_TECH,RADIOLOGY_TECH,PHARMACIST,RECEPTIONIST,IVF_SPECIALIST,EMBRYOLOGIST"
)
PUBLIC_REGISTRATION_ALLOWED_ROLES = [
    role.strip().upper()
    for role in os.environ.get(
        "PUBLIC_REGISTRATION_ALLOWED_ROLES", _default_public_registration_roles
    ).split(",")
    if role.strip() and role.strip().upper() != "ADMIN"
]

# OpenAPI / Swagger / ReDoc — disabled in production unless explicitly enabled
API_DOCS_ENABLED = os.environ.get(
    "API_DOCS_ENABLED", "True" if DEBUG else "False"
).lower() in ("true", "1", "yes")

# Detailed health endpoints expose dependency status; keep private in production
HEALTH_DETAILED_PUBLIC = os.environ.get(
    "HEALTH_DETAILED_PUBLIC", "True" if DEBUG else "False"
).lower() in ("true", "1", "yes")

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",  # For token blacklisting on logout
    "corsheaders",  # CORS support for frontend
    "drf_spectacular",  # OpenAPI 3.0 schema generation
    # EMR Apps
    "apps.organizations",
    "apps.users",
    "apps.auth_otp",
    "apps.patients",
    "apps.visits",
    "apps.consultations",
    "apps.laboratory",
    "apps.pharmacy.apps.PharmacyConfig",
    "apps.radiology",
    "apps.billing.apps.BillingConfig",
    "apps.offline",
    "apps.integrations",
    "apps.appointments",
    "apps.reports",
    "apps.backup",
    "apps.notifications",
    "apps.telemedicine",
    "apps.clinical",
    "apps.nursing",
    "apps.documents",
    "apps.referrals",
    "apps.discharges",
    "apps.ai_integration",
    "apps.wallet",
    "apps.ivf",
    "apps.antenatal",
    "apps.guide",
    "core",
]

# Custom User Model
AUTH_USER_MODEL = "users.User"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "core.middleware.request_sanitizer.RequestSanitizerMiddleware",  # Reject path traversal / null bytes early
    "corsheaders.middleware.CorsMiddleware",  # CORS middleware (must be early, before CommonMiddleware)
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "core.middleware.organization_middleware.OrganizationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Security headers middleware
    "core.middleware.security_headers.SecurityHeadersMiddleware",
    # EMR-specific middleware (order is critical)
    # 1. VisitLookupMiddleware: Extracts visit_id from URL and attaches Visit to request
    #    Must run AFTER authentication to access request.user if needed
    #    Must run BEFORE PaymentClearedGuard
    "core.middleware.visit_lookup.VisitLookupMiddleware",
    # 2. PaymentClearedGuard: Enforces payment must be cleared for clinical actions
    #    Requires VisitLookupMiddleware to set request.visit
    "core.middleware.payment_guard.PaymentClearedGuard",
    # Add other EMR middleware here if needed (e.g., RoleGuard, AuditMiddleware)
]

# Security Headers
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0  # 1 year in production
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Session Security
SESSION_COOKIE_SECURE = not DEBUG  # HTTPS only in production
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"

# CSRF Security
CSRF_COOKIE_SECURE = not DEBUG  # HTTPS only in production
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"

# SSL/HTTPS (when behind nginx reverse proxy)
SECURE_SSL_REDIRECT = os.environ.get("SECURE_SSL_REDIRECT", "false").lower() == "true"
if os.environ.get("SECURE_PROXY_SSL_HEADER") == "X-Forwarded-Proto":
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Cache Configuration
_redis_url = os.environ.get("REDIS_URL") or os.environ.get("CELERY_BROKER_URL")
if _redis_url and _redis_url.startswith("redis://"):
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": _redis_url,
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "unique-snowflake",
        }
    }

ROOT_URLCONF = "core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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

WSGI_APPLICATION = "core.wsgi.application"

# Database
_db_engine = os.environ.get("DB_ENGINE", "django.db.backends.sqlite3")
_db_options = {}
if "postgresql" in _db_engine:
    _db_options = {
        "connect_timeout": 60,
        "options": "-c statement_timeout=60000",  # 60s query timeout
    }
    if os.environ.get("DB_SSLMODE"):
        _db_options["sslmode"] = os.environ.get(
            "DB_SSLMODE"
        )  # e.g. require, verify-full
else:
    # timeout = SQLite busy wait (seconds); WAL pragmas applied in core/__init__.py
    _db_options = {"timeout": 60}

_db_name = os.environ.get("DB_NAME", BACKEND_DIR / "db.sqlite3")
if "sqlite" in _db_engine:
    _db_path = Path(_db_name)
    if not _db_path.is_absolute():
        _db_path = BACKEND_DIR / _db_path
    _db_name = str(_db_path)

DATABASES = {
    "default": {
        "ENGINE": _db_engine,
        "NAME": _db_name,
        "USER": os.environ.get("DB_USER", ""),
        "PASSWORD": os.environ.get("DB_PASSWORD", ""),
        "HOST": os.environ.get("DB_HOST", ""),
        "PORT": os.environ.get("DB_PORT", ""),
        "OPTIONS": _db_options,
    }
}

# Password validation (min 8 characters, complexity)
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {
        "NAME": "core.password_validators.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    },
    {"NAME": "core.password_validators.ComplexityValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = "static/"
STATIC_ROOT = DATA_DIR / "staticfiles"

# Media files (for file uploads)
MEDIA_ROOT = DATA_DIR / "media"
MEDIA_URL = "/media/"

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# REST Framework configuration
# Production: require tenant context on authenticated API calls (disable for Lifeway single-clinic)
# Lifeway single-clinic: default off in DEBUG; set false in production .env
REQUIRE_ORGANIZATION_CONTEXT = os.environ.get(
    "REQUIRE_ORGANIZATION_CONTEXT", "false" if DEBUG else "true"
).lower() in ("true", "1", "yes")

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "core.jwt_auth.RoleAwareJWTAuthentication",
        # Session auth kept for admin panel
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ]
    + (
        ["core.permissions.RequiresOrganization"]
        if REQUIRE_ORGANIZATION_CONTEXT
        else []
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "core.exceptions.emr_exception_handler",
}

# JWT Configuration (per EMR rules: short-lived access tokens, refresh tokens)
from datetime import timedelta

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),  # Short-lived (15 minutes)
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),  # 7 days for refresh
    "ROTATE_REFRESH_TOKENS": True,  # Rotate refresh tokens on use
    "BLACKLIST_AFTER_ROTATION": True,  # Blacklist old refresh tokens
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    "TOKEN_TYPE_CLAIM": "token_type",
}

# EMR-specific settings
APP_VERSION = os.environ.get("APP_VERSION", "2.0.0")

EMR_SETTINGS = {
    # Payment enforcement
    "REQUIRE_PAYMENT_FOR_CONSULTATION": True,
    "REQUIRE_PAYMENT_FOR_LAB": True,
    "REQUIRE_PAYMENT_FOR_RADIOLOGY": True,
    "REQUIRE_PAYMENT_FOR_PRESCRIPTION": True,
    # Visit status enforcement
    "ALLOW_MUTATIONS_ON_CLOSED_VISITS": False,
    # Audit logging
    "ENABLE_AUDIT_LOGGING": True,
    "AUDIT_LOG_RETENTION_DAYS": 2555,  # 7 years for HIPAA compliance
}

# CORS Configuration
# Allow environment variable override for production
if os.environ.get("CORS_ALLOWED_ORIGINS"):
    CORS_ALLOWED_ORIGINS = [
        origin.strip()
        for origin in os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",")
        if origin.strip()
    ]
else:
    # Default to development origins
    CORS_ALLOWED_ORIGINS = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3002",
        "http://127.0.0.1:3002",
        "http://localhost:3004",
        "http://127.0.0.1:3004",
    ]

CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_METHODS = [
    "DELETE",
    "GET",
    "OPTIONS",
    "PATCH",
    "POST",
    "PUT",
]

# drf-spectacular settings for OpenAPI documentation
SPECTACULAR_SETTINGS = {
    "TITLE": "Lifeway EMR API",
    "DESCRIPTION": """
    Electronic Medical Record (EMR) System API
    
    This API provides endpoints for managing patient records, visits, consultations, 
    lab orders, radiology, prescriptions, and more.
    
    ## Authentication
    All endpoints (except `/auth/login/` and `/auth/refresh/`) require JWT authentication.
    Include the token in the Authorization header:
    ```
    Authorization: Bearer <access_token>
    ```
    
    ## EMR Rules
    - **Visit is the Single Source of Clinical Truth**: All clinical actions are visit-scoped
    - **Payment Enforcement**: Payment must be CLEARED before clinical actions
    - **Visit Status**: Visits must be OPEN for modifications (CLOSED visits are immutable)
    - **Role-Based Access Control**: Strict separation of duties by user role
    - **Audit Logging**: All actions are logged for compliance
    
    ## User Roles
    - **DOCTOR**: Create consultations, orders, prescriptions; close visits
    - **RECEPTIONIST**: Register patients, create visits, process payments, manage appointments
    - **LAB_TECH**: View and process lab orders, create lab results
    - **RADIOLOGY_TECH**: View and process radiology orders, create reports
    - **PHARMACIST**: Dispense prescriptions, manage drug catalog, manage inventory
    """,
    "VERSION": APP_VERSION,
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "COMPONENT_NO_READ_ONLY_REQUIRED": True,
    "SCHEMA_PATH_PREFIX": "/api/v1",
    "AUTHENTICATION_WHITELIST": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "TAGS": [
        {
            "name": "Authentication",
            "description": "User authentication and token management",
        },
        {"name": "Patients", "description": "Patient registration and management"},
        {"name": "Visits", "description": "Visit creation and management"},
        {
            "name": "Consultations",
            "description": "Clinical consultations (Doctor only)",
        },
        {"name": "Laboratory", "description": "Lab orders and results"},
        {"name": "Radiology", "description": "Radiology orders and reports"},
        {"name": "Prescriptions", "description": "Prescription management"},
        {"name": "Pharmacy", "description": "Drug catalog and inventory management"},
        {"name": "Billing", "description": "Payment processing"},
        {"name": "Appointments", "description": "Appointment scheduling"},
        {"name": "Reports", "description": "Analytics and reporting"},
        {"name": "Audit Logs", "description": "System audit logs (read-only)"},
    ],
    "SERVERS": [
        {"url": "http://localhost:8000", "description": "Development server"},
    ],
}

E2E_OTP_EXPOSE = os.environ.get("E2E_OTP_EXPOSE", "false").lower() in (
    "true",
    "1",
    "yes",
)

# Optional error monitoring (Sentry)
SENTRY_DSN = os.environ.get("SENTRY_DSN", "")
SENTRY_TRACES_SAMPLE_RATE = float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0.1"))

if SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.celery import CeleryIntegration
        from sentry_sdk.integrations.django import DjangoIntegration

        sentry_sdk.init(
            dsn=SENTRY_DSN,
            integrations=[DjangoIntegration(), CeleryIntegration()],
            traces_sample_rate=SENTRY_TRACES_SAMPLE_RATE,
            send_default_pii=False,
            environment="production" if not DEBUG else "development",
            release=APP_VERSION,
        )
    except ImportError:
        pass

# Scheduled backups
SCHEDULED_BACKUP_ENABLED = os.environ.get("SCHEDULED_BACKUP_ENABLED", "true").lower() in (
    "true",
    "1",
    "yes",
)
BACKUP_STORAGE_DIR = os.environ.get("BACKUP_STORAGE_DIR", "")

# Backup settings
BACKUP_DIR = os.path.join(DATA_DIR, "backups")
os.makedirs(BACKUP_DIR, exist_ok=True)

# Default backup retention (days)
BACKUP_RETENTION_DAYS = 30

# Email Configuration
EMAIL_BACKEND = os.environ.get(
    "EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend",  # Console backend for development
)

# For production, use SMTP:
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
# EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
# EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True') == 'True'
# EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
# EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
# DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@emr.example.com')

DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "noreply@emr.local")
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# SMS Configuration
SMS_ENABLED = os.environ.get("SMS_ENABLED", "False") == "True"
SMS_PROVIDER = os.environ.get(
    "SMS_PROVIDER", "console"
)  # 'console' | 'twilio' | 'termii'

# Twilio Configuration (if using Twilio)
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
TWILIO_PHONE_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER", "")

# Termii Configuration (if using Termii - Nigeria-focused SMS)
# Base URL is per-account; find yours at https://accounts.termii.com
TERMII_API_KEY = os.environ.get("TERMII_API_KEY", "")
TERMII_SENDER_ID = os.environ.get(
    "TERMII_SENDER_ID", ""
)  # Alphanumeric 3-11 chars (e.g. ClinicName)
TERMII_BASE_URL = os.environ.get("TERMII_BASE_URL", "https://api.termii.com")

# Twilio Video Configuration (for Telemedicine)
TWILIO_API_KEY = os.environ.get("TWILIO_API_KEY", "")
TWILIO_API_SECRET = os.environ.get("TWILIO_API_SECRET", "")
TWILIO_RECORDING_ENABLED = os.environ.get("TWILIO_RECORDING_ENABLED", "False") == "True"
# Production telemedicine video: twilio | livekit (self-hosted / LiveKit Cloud)
TELEMEDICINE_VIDEO_PROVIDER = os.environ.get("TELEMEDICINE_VIDEO_PROVIDER", "twilio").lower().strip()
# Service catalog code used when ending a session with add_billing=true
TELEMEDICINE_BILLING_SERVICE_CODE = os.environ.get(
    "TELEMEDICINE_BILLING_SERVICE_CODE", "TELEMED-001"
).strip()
# LiveKit (when TELEMEDICINE_VIDEO_PROVIDER=livekit)
LIVEKIT_URL = os.environ.get("LIVEKIT_URL", "")
LIVEKIT_API_KEY = os.environ.get("LIVEKIT_API_KEY", "")
LIVEKIT_API_SECRET = os.environ.get("LIVEKIT_API_SECRET", "")

# Auto-transcribe telemedicine recordings when a transcription provider is configured
TELEMEDICINE_AUTO_TRANSCRIPTION = os.environ.get(
    "TELEMEDICINE_AUTO_TRANSCRIPTION", "True"
).lower() in ("true", "1", "yes")
# Provider: openai (Whisper API) | faster-whisper (local, no API key)
TRANSCRIPTION_PROVIDER = os.environ.get("TRANSCRIPTION_PROVIDER", "openai").lower().strip()
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
TRANSCRIPTION_API_KEY = os.environ.get("TRANSCRIPTION_API_KEY", "")
# faster-whisper (local STT) — used when TRANSCRIPTION_PROVIDER=faster-whisper
FASTER_WHISPER_MODEL = os.environ.get("FASTER_WHISPER_MODEL", "base")
FASTER_WHISPER_DEVICE = os.environ.get("FASTER_WHISPER_DEVICE", "cpu")
FASTER_WHISPER_COMPUTE_TYPE = os.environ.get("FASTER_WHISPER_COMPUTE_TYPE", "")
FASTER_WHISPER_LANGUAGE = os.environ.get("FASTER_WHISPER_LANGUAGE", "")

# Paystack Configuration (visit billing — Nigeria)
PAYSTACK_SECRET_KEY = os.environ.get("PAYSTACK_SECRET_KEY", "")
PAYSTACK_PUBLIC_KEY = os.environ.get("PAYSTACK_PUBLIC_KEY", "")
# When true (or DEBUG with placeholder keys), wallet top-ups use a local mock gateway
PAYSTACK_MOCK = os.environ.get("PAYSTACK_MOCK", "")
PAYSTACK_CALLBACK_URL = os.environ.get(
    "PAYSTACK_CALLBACK_URL", "http://localhost:3001/wallet/callback"
)

# National Health ID / NIN verification (stub | http)
NHID_VERIFICATION_MODE = os.environ.get("NHID_VERIFICATION_MODE", "stub")
NHID_API_URL = os.environ.get("NHID_API_URL", "")
NHID_API_KEY = os.environ.get("NHID_API_KEY", "")

# Flutterwave Configuration (optional visit payments — Nigeria)
FLUTTERWAVE_SECRET_KEY = os.environ.get("FLUTTERWAVE_SECRET_KEY", "")
FLUTTERWAVE_PUBLIC_KEY = os.environ.get("FLUTTERWAVE_PUBLIC_KEY", "")

# Plan caps on patients/staff — off for Lifeway single-clinic
ENFORCE_PLAN_LIMITS = os.environ.get("ENFORCE_PLAN_LIMITS", "false").lower() in (
    "true",
    "1",
    "yes",
)

# Subdomain tenant routing (disabled for single-clinic; optional for future use)
TENANT_SUBDOMAIN_ENABLED = os.environ.get(
    "TENANT_SUBDOMAIN_ENABLED", "false"
).lower() in ("true", "1", "yes")
TENANT_BASE_DOMAIN = os.environ.get("TENANT_BASE_DOMAIN", "localhost")

# Public SPA origin for email links, telemedicine redirects, patient portal URLs (no /api path)
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:3000')

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
    "x-organization-id",
    "x-organization-slug",
]

# Clinic Information for Invoices and Receipts
CLINIC_NAME = os.environ.get("CLINIC_NAME", "Lifeway Medical Centre Ltd")
CLINIC_ADDRESS = os.environ.get(
    "CLINIC_ADDRESS", "Plot 1593, ZONE E, APO RESETTLEMENT, ABUJA"
)
CLINIC_PHONE = os.environ.get("CLINIC_PHONE", "07058893439, 08033145080, 08033114417")
CLINIC_EMAIL = os.environ.get("CLINIC_EMAIL", "info@clinic.com")

# Clinic Logo Path — monorepo default; override with CLINIC_LOGO_PATH in Docker/prod.
_default_logo = BASE_DIR / "frontend" / "public" / "LMC logo1.png"
CLINIC_LOGO_PATH = os.environ.get(
    "CLINIC_LOGO_PATH",
    str(_default_logo) if _default_logo.is_file() else "",
)

# PACS-lite / Orthanc / MinIO Configuration
# OHIF viewer path or URL — use /ohif/viewer when Orthanc OHIF plugin is proxied same-origin
OHIF_VIEWER_URL = os.environ.get("OHIF_VIEWER_URL", None)
# Enable signed URLs for access control
RADIOLOGY_SIGNED_URLS = os.environ.get("RADIOLOGY_SIGNED_URLS", "True") == "True"
# Custom storage backend for radiology images (optional)
# Options: 'storages.backends.s3boto3.S3Boto3Storage' for S3/MinIO
#          None for default filesystem storage
RADIOLOGY_STORAGE = os.environ.get("RADIOLOGY_STORAGE", None)

# Orthanc PACS (DICOMweb + STOW on ingest)
ORTHANC_URL = os.environ.get("ORTHANC_URL", "").rstrip("/") or None
ORTHANC_USERNAME = os.environ.get("ORTHANC_USERNAME", "")
ORTHANC_PASSWORD = os.environ.get("ORTHANC_PASSWORD", "")

# MinIO / S3-compatible object storage (optional; used when RADIOLOGY_STORAGE is S3Boto3Storage)
MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "")
MINIO_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY", "")
MINIO_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY", "")
MINIO_BUCKET = os.environ.get("MINIO_BUCKET", "emr-radiology")

if os.environ.get("AWS_S3_ENDPOINT_URL") and not RADIOLOGY_STORAGE:
    RADIOLOGY_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"

if RADIOLOGY_STORAGE and "s3boto3" in RADIOLOGY_STORAGE:
    try:
        import storages  # noqa: F401
    except ImportError:
        RADIOLOGY_STORAGE = None
    else:
        if "storages" not in INSTALLED_APPS:
            INSTALLED_APPS.append("storages")

if RADIOLOGY_STORAGE and "s3boto3" in RADIOLOGY_STORAGE:
    AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID", MINIO_ACCESS_KEY)
    AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY", MINIO_SECRET_KEY)
    AWS_STORAGE_BUCKET_NAME = os.environ.get("AWS_STORAGE_BUCKET_NAME", MINIO_BUCKET)
    AWS_S3_ENDPOINT_URL = os.environ.get("AWS_S3_ENDPOINT_URL", MINIO_ENDPOINT or None)
    AWS_S3_USE_SSL = os.environ.get("AWS_S3_USE_SSL", "false").lower() == "true"
    AWS_S3_ADDRESSING_STYLE = os.environ.get("AWS_S3_ADDRESSING_STYLE", "path")
    AWS_S3_SIGNATURE_VERSION = os.environ.get("AWS_S3_SIGNATURE_VERSION", "s3v4")
    AWS_DEFAULT_ACL = None
    AWS_QUERYSTRING_AUTH = True

# Logging Configuration
LOGS_DIR = os.path.join(DATA_DIR, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

def _build_file_log_handler(filename: str, level: str = 'INFO') -> dict:
    """Use plain FileHandler on Windows/dev to avoid log rotation file-lock errors."""
    path = os.path.join(LOGS_DIR, filename)
    if DEBUG or os.name == 'nt':
        return {
            'level': level,
            'class': 'logging.FileHandler',
            'filename': path,
            'formatter': 'verbose',
        }
    return {
        'level': level,
        'class': 'logging.handlers.RotatingFileHandler',
        'filename': path,
        'maxBytes': 1024 * 1024 * 15,
        'backupCount': 10,
        'formatter': 'verbose',
    }

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "filters": {
        "require_debug_false": {
            "()": "django.utils.log.RequireDebugFalse",
        },
    },
    "handlers": {
        "file": _build_file_log_handler("django.log"),
        "error_file": _build_file_log_handler("django_errors.log", "ERROR"),
        "console": {
            "level": "DEBUG" if DEBUG else "INFO",
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "root": {
        "handlers": ["console", "file"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["file", "error_file"],
            "level": "INFO",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["error_file"],
            "level": "ERROR",
            "propagate": False,
        },
        "apps": {
            "handlers": ["file", "error_file"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# Celery Configuration (Asynchronous Task Queue)
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://127.0.0.1:6379/0")
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://127.0.0.1:6379/0")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
