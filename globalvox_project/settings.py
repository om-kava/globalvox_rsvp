import os
from pathlib import Path
from dotenv import load_dotenv

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file
load_dotenv(BASE_DIR / '.env')

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-gv-rsvp-dev-key-!9x#p2$q@8z1v0k4b7n')

DEBUG = os.getenv('DEBUG', 'True').lower() in ('true', '1', 't')

allowed_hosts_str = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1,testserver,.vercel.app,.railway.app,*')
ALLOWED_HOSTS = [host.strip() for host in allowed_hosts_str.split(',') if host.strip()]
if 'testserver' not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append('testserver')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party apps
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',

    # Local domain apps
    'apps.accounts.apps.AccountsConfig',
    'apps.campaigns.apps.CampaignsConfig',
    'apps.invitees.apps.InviteesConfig',
    'apps.calling.apps.CallingConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'globalvox_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
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

WSGI_APPLICATION = 'globalvox_project.wsgi.application'

# Database Configuration (MySQL with environment-based settings)
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

db_engine = os.getenv('DB_ENGINE')
db_host = (os.getenv('DB_HOST') or os.getenv('MYSQLHOST') or '').strip()

# Check if DB_HOST is invalid or unreachable from serverless environment (e.g. Railway internal host or localhost)
is_unreachable_host = (
    not db_host
    or 'railway.internal' in db_host
    or db_host in ('127.0.0.1', 'localhost')
)

# Detect serverless / linux cloud deployment (Vercel, AWS Lambda, etc.)
is_serverless = bool(
    os.getenv('VERCEL')
    or os.getenv('VERCEL_ENV')
    or os.getenv('AWS_LAMBDA_FUNCTION_NAME')
    or (os.name != 'nt' and os.path.exists('/tmp'))
)

# If no reachable remote host is configured or SQLite is specified, use SQLite safely
if is_unreachable_host or db_engine == 'django.db.backends.sqlite3':
    sqlite_db_name = os.getenv('SQLITE_PATH') or ('/tmp/db.sqlite3' if is_serverless else str(BASE_DIR / 'seed.sqlite3'))
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': sqlite_db_name,
        }
    }
else:
    db_engine = db_engine or 'django.db.backends.mysql'
    db_name = os.getenv('DB_NAME') or os.getenv('MYSQLDATABASE', 'globalvox_rsvp')
    db_user = os.getenv('DB_USER') or os.getenv('MYSQLUSER', 'root')
    db_password = os.getenv('DB_PASSWORD') or os.getenv('MYSQLPASSWORD', '')
    db_port = os.getenv('DB_PORT') or os.getenv('MYSQLPORT', '3306')

    DATABASES = {
        'default': {
            'ENGINE': db_engine,
            'NAME': db_name,
            'USER': db_user,
            'PASSWORD': db_password,
            'HOST': db_host or '127.0.0.1',
            'PORT': db_port,
            'OPTIONS': {
                'charset': 'utf8mb4',
                'connect_timeout': 5,
                'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            } if 'mysql' in db_engine else {},
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'
WHITENOISE_MANIFEST_STRICT = False
WHITENOISE_USE_FINDERS = True

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Django REST Framework Settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'EXCEPTION_HANDLER': 'rest_framework.views.exception_handler',
}

# SimpleJWT Settings
from datetime import timedelta
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}

# Security & Cookie Settings
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False  # Enabled for frontend JavaScript to access the CSRF token header
X_FRAME_OPTIONS = 'DENY'

# CORS Settings
CORS_ALLOWED_ORIGINS = [
    'http://localhost:8000',
    'http://127.0.0.1:8000',
]
CORS_ALLOW_CREDENTIALS = True

# CSRF Trusted Origins for live deployment domains
CSRF_TRUSTED_ORIGINS = [
    'https://*.railway.app',
    'https://*.vercel.app',
    'https://*.up.railway.app',
    'http://localhost:8000',
    'http://127.0.0.1:8000',
]

# Calling Simulation Settings
MOCK_CALL_DELAY_MS = int(os.getenv('MOCK_CALL_DELAY_MS', '20'))
SIMULATION_MODE = os.getenv('SIMULATION_MODE', 'realistic')
