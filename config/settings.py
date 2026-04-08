from pathlib import Path

import mongoengine
from decouple import Config, RepositoryEnv, AutoConfig, Csv

BASE_DIR = Path(__file__).resolve().parent.parent

_env_file = BASE_DIR / '.env.local'
config: Config = Config(RepositoryEnv(str(_env_file))) if _env_file.exists() else AutoConfig()

SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())

INSTALLED_APPS = [
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'drf_spectacular',
    'users',
    'products',
    'orders',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {}

MONGODB_URI = config('MONGODB_URI')
MONGODB_NAME = config('MONGODB_NAME', default='backend-python-api')

mongoengine.connect(
    db=MONGODB_NAME,
    host=MONGODB_URI,
)

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Manila'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'users.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'EXCEPTION_HANDLER': 'config.exceptions.custom_exception_handler',
    'UNAUTHENTICATED_USER': None,
}

JWT_SECRET_KEY = SECRET_KEY
JWT_ACCESS_TOKEN_LIFETIME_MINUTES = config('JWT_ACCESS_TOKEN_LIFETIME_MINUTES', default=60, cast=int)
JWT_REFRESH_TOKEN_LIFETIME_DAYS = config('JWT_REFRESH_TOKEN_LIFETIME_DAYS', default=7, cast=int)
JWT_ALGORITHM = 'HS256'

CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', default='http://localhost:3000,http://localhost:8080', cast=Csv())
CORS_ALLOW_CREDENTIALS = True

API_VERSION = 'v1'

SPECTACULAR_SETTINGS = {
    'TITLE': 'Backend API',
    'DESCRIPTION': 'Django REST Framework API with MongoDB — Experimentation Project',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'SCHEMA_PATH_PREFIX': f'/api/{API_VERSION}/',
    'TAGS': [
        {'name': 'users', 'description': 'Registration, authentication, and profile management'},
        {'name': 'products', 'description': 'Product catalog — listing, creation, and image uploads'},
        {'name': 'orders', 'description': 'Order creation, status transitions, and receipt uploads'},
    ],
    'SECURITY': [{'BearerAuth': []}],
    'APPEND_COMPONENTS': {
        'securitySchemes': {
            'BearerAuth': {
                'type': 'http',
                'scheme': 'bearer',
                'bearerFormat': 'JWT',
            }
        }
    },
}

# =============================================================================
# EMAIL (Optional — for notifications)
# =============================================================================

EMAIL_HOST = config('EMAIL_HOST', default='')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USER = config('EMAIL_USER', default='')
EMAIL_PASS = config('EMAIL_PASS', default='')
EMAIL_FROM = config('EMAIL_FROM', default='')

# =============================================================================
# AWS S3
# =============================================================================

AWS_REGION = config('AWS_REGION', default='ap-southeast-1')
AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID', default='')
AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY', default='')
AWS_S3_BUCKET_NAME = config('AWS_S3_BUCKET_NAME', default='')
