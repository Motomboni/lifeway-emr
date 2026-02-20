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
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-change-in-production')
DEBUG = os.environ.get('DEBUG', 'False') == 'True'

# Clinic-grade: refuse to run in production with default/insecure SECRET_KEY
_INSECURE_DEFAULT_KEY = 'django-insecure-change-in-production'
if not DEBUG and (not SECRET_KEY or SECRET_KEY == _INSECURE_DEFAULT_KEY or len(SECRET_KEY) < 32):
    raise ValueError(
        "Production requires a strong SECRET_KEY (e.g. openssl rand -hex 32). "
        "Do not use the default or a short key."
    )

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',') if os.environ.get('ALLOWED_HOSTS') else ['localhost', '127.0.0.1']

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',  # For token blacklisting on logout
    'corsheaders',  # CORS support for frontend
    'drf_spectacular',  # OpenAPI 3.0 schema generation
    # EMR Apps
    'apps.users',
    'apps.auth_otp',
    'apps.patients',
    'apps.visits',
    'apps.consultations',
    'apps.laboratory',
    'apps.pharmacy.apps.PharmacyConfig',
    'apps.radiology',
    'apps.billing.apps.BillingConfig',
    'apps.offline',
    'apps.appointments',
    'apps.reports',
    'apps.backup',
    'apps.notifications',
    'apps.telemedicine',
    'apps.clinical',
    'apps.nursing',
    'apps.documents',
    'apps.referrals',
    'apps.discharges',
    'apps.ai_integration',
    'apps.wallet',
    'apps.ivf',
    'apps.antenatal',
    'core',
]

# Custom User Model
AUTH_USER_MODEL = 'users.User'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'core.middleware.request_sanitizer.RequestSanitizerMiddleware',  # Reject path traversal / null bytes early
    'corsheaders.middleware.CorsMiddleware',  # CORS middleware (must be early, before CommonMiddleware)
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    
    # Security headers middleware
    'core.middleware.security_headers.SecurityHeadersMiddleware',
    
    # EMR-specific middleware (order is critical)
    # 1. VisitLookupMiddleware: Extracts visit_id from URL and attaches Visit to request
    #    Must run AFTER authentication to access request.user if needed
    #    Must run BEFORE PaymentClearedGuard
    'core.middleware.visit_lookup.VisitLookupMiddleware',
    
    # 2. PaymentClearedGuard: Enforces payment must be cleared for clinical actions
    #    Requires VisitLookupMiddleware to set request.visit
    'core.middleware.payment_guard.PaymentClearedGuard',
    
    # Add other EMR middleware here if needed (e.g., RoleGuard, AuditMiddleware)
]

# Security Headers
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0  # 1 year in production
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Session Security
SESSION_COOKIE_SECURE = not DEBUG  # HTTPS only in production
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'

# CSRF Security
CSRF_COOKIE_SECURE = not DEBUG  # HTTPS only in production
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'

# SSL/HTTPS (when behind nginx reverse proxy)
SECURE_SSL_REDIRECT = os.environ.get('SECURE_SSL_REDIRECT', 'false').lower() == 'true'
if os.environ.get('SECURE_PROXY_SSL_HEADER') == 'X-Forwarded-Proto':
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Cache Configuration
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}

# In production, use Redis:
# CACHES = {
#     'default': {
#         'BACKEND': 'django.core.cache.backends.redis.RedisCache',
#         'LOCATION': os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/1'),
#     }
# }

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

# Database
_db_engine = os.environ.get('DB_ENGINE', 'django.db.backends.sqlite3')
_db_options = {}
if 'postgresql' in _db_engine:
    _db_options = {
        'connect_timeout': 60,
        'options': '-c statement_timeout=60000',  # 60s query timeout
    }
    if os.environ.get('DB_SSLMODE'):
        _db_options['sslmode'] = os.environ.get('DB_SSLMODE')  # e.g. require, verify-full
else:
    _db_options = {
        'timeout': 60,
        'init_command': 'PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL;',
    }

DATABASES = {
    'default': {
        'ENGINE': _db_engine,
        'NAME': os.environ.get('DB_NAME', BASE_DIR / 'db.sqlite3'),
        'USER': os.environ.get('DB_USER', ''),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST': os.environ.get('DB_HOST', ''),
        'PORT': os.environ.get('DB_PORT', ''),
        'OPTIONS': _db_options,
    }
}

# Password validation (clinic-grade: length 12, complexity)
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'core.password_validators.MinimumLengthValidator', 'OPTIONS': {'min_length': 12}},
    {'NAME': 'core.password_validators.ComplexityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files (for file uploads)
MEDIA_ROOT = BASE_DIR / 'media'
MEDIA_URL = '/media/'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# REST Framework configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        # Session auth kept for admin panel
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# JWT Configuration (per EMR rules: short-lived access tokens, refresh tokens)
from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),  # Short-lived (15 minutes)
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),  # 7 days for refresh
    'ROTATE_REFRESH_TOKENS': True,  # Rotate refresh tokens on use
    'BLACKLIST_AFTER_ROTATION': True,  # Blacklist old refresh tokens
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
}

# EMR-specific settings
EMR_SETTINGS = {
    # Payment enforcement
    'REQUIRE_PAYMENT_FOR_CONSULTATION': True,
    'REQUIRE_PAYMENT_FOR_LAB': True,
    'REQUIRE_PAYMENT_FOR_RADIOLOGY': True,
    'REQUIRE_PAYMENT_FOR_PRESCRIPTION': True,
    
    # Visit status enforcement
    'ALLOW_MUTATIONS_ON_CLOSED_VISITS': False,
    
    # Audit logging
    'ENABLE_AUDIT_LOGGING': True,
    'AUDIT_LOG_RETENTION_DAYS': 2555,  # 7 years for HIPAA compliance
}

# CORS Configuration
# Allow environment variable override for production
if os.environ.get('CORS_ALLOWED_ORIGINS'):
    CORS_ALLOWED_ORIGINS = [
        origin.strip() 
        for origin in os.environ.get('CORS_ALLOWED_ORIGINS', '').split(',')
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
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

# drf-spectacular settings for OpenAPI documentation
SPECTACULAR_SETTINGS = {
    'TITLE': 'Modern EMR API',
    'DESCRIPTION': '''
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
    ''',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'COMPONENT_NO_READ_ONLY_REQUIRED': True,
    'SCHEMA_PATH_PREFIX': '/api/v1',
    'AUTHENTICATION_WHITELIST': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'TAGS': [
        {'name': 'Authentication', 'description': 'User authentication and token management'},
        {'name': 'Patients', 'description': 'Patient registration and management'},
        {'name': 'Visits', 'description': 'Visit creation and management'},
        {'name': 'Consultations', 'description': 'Clinical consultations (Doctor only)'},
        {'name': 'Laboratory', 'description': 'Lab orders and results'},
        {'name': 'Radiology', 'description': 'Radiology orders and reports'},
        {'name': 'Prescriptions', 'description': 'Prescription management'},
        {'name': 'Pharmacy', 'description': 'Drug catalog and inventory management'},
        {'name': 'Billing', 'description': 'Payment processing'},
        {'name': 'Appointments', 'description': 'Appointment scheduling'},
        {'name': 'Reports', 'description': 'Analytics and reporting'},
        {'name': 'Audit Logs', 'description': 'System audit logs (read-only)'},
    ],
    'SERVERS': [
        {'url': 'http://localhost:8000', 'description': 'Development server'},
    ],
}

# Backup settings
BACKUP_DIR = os.path.join(BASE_DIR, 'backups')
os.makedirs(BACKUP_DIR, exist_ok=True)

# Default backup retention (days)
BACKUP_RETENTION_DAYS = 30

# Email Configuration
EMAIL_BACKEND = os.environ.get(
    'EMAIL_BACKEND',
    'django.core.mail.backends.console.EmailBackend'  # Console backend for development
)

# For production, use SMTP:
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
# EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
# EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True') == 'True'
# EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
# EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
# DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@emr.example.com')

DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@emr.local')
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# SMS Configuration
SMS_ENABLED = os.environ.get('SMS_ENABLED', 'False') == 'True'
SMS_PROVIDER = os.environ.get('SMS_PROVIDER', 'console')  # 'console' for development, 'twilio' for production

# Twilio Configuration (if using Twilio)
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID', '')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN', '')
TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER', '')

# Twilio Video Configuration (for Telemedicine)
TWILIO_API_KEY = os.environ.get('TWILIO_API_KEY', '')
TWILIO_API_SECRET = os.environ.get('TWILIO_API_SECRET', '')
TWILIO_RECORDING_ENABLED = os.environ.get('TWILIO_RECORDING_ENABLED', 'False') == 'True'

# Paystack Configuration
PAYSTACK_SECRET_KEY = os.environ.get('PAYSTACK_SECRET_KEY', '')
PAYSTACK_PUBLIC_KEY = os.environ.get('PAYSTACK_PUBLIC_KEY', '')
PAYSTACK_CALLBACK_URL = os.environ.get('PAYSTACK_CALLBACK_URL', 'http://localhost:3001/wallet/callback')

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# Clinic Information for Invoices and Receipts
CLINIC_NAME = os.environ.get('CLINIC_NAME', 'Lifeway Medical Centre Ltd')
CLINIC_ADDRESS = os.environ.get('CLINIC_ADDRESS', 'Plot 1593, ZONE E, APO RESETTLEMENT, ABUJA')
CLINIC_PHONE = os.environ.get('CLINIC_PHONE', '07058893439, 08033145080, 08033114417')
CLINIC_EMAIL = os.environ.get('CLINIC_EMAIL', 'info@clinic.com')

# Clinic Logo Path (absolute or relative to BASE_DIR)
# Place your logo file in: frontend/public/LMC logo1.png
# Then set this to the absolute path or relative path from BASE_DIR
# Example: CLINIC_LOGO_PATH = os.path.join(BASE_DIR, 'frontend', 'public', 'LMC logo1.png')
# BASE_DIR is the project root (3 levels up from this file: backend/core/settings.py)
CLINIC_LOGO_PATH = os.environ.get('CLINIC_LOGO_PATH', str(BASE_DIR / 'frontend' / 'public' / 'LMC logo1.png'))

# PACS-lite Configuration
# OHIF Viewer URL (recommended) or None for lightweight viewer
OHIF_VIEWER_URL = os.environ.get('OHIF_VIEWER_URL', None)
# Enable signed URLs for access control
RADIOLOGY_SIGNED_URLS = os.environ.get('RADIOLOGY_SIGNED_URLS', 'True') == 'True'
# Custom storage backend for radiology images (optional)
# Options: 'storages.backends.s3boto3.S3Boto3Storage' for S3/MinIO
#          None for default filesystem storage
RADIOLOGY_STORAGE = os.environ.get('RADIOLOGY_STORAGE', None)

# Logging Configuration
LOGS_DIR = os.path.join(BASE_DIR, 'logs')
os.makedirs(LOGS_DIR, exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOGS_DIR, 'django.log'),
            'maxBytes': 1024 * 1024 * 15,  # 15MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOGS_DIR, 'django_errors.log'),
            'maxBytes': 1024 * 1024 * 15,  # 15MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'console': {
            'level': 'DEBUG' if DEBUG else 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'error_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['error_file'],
            'level': 'ERROR',
            'propagate': False,
        },
        'apps': {
            'handlers': ['file', 'error_file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
