from datetime import timedelta
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('SECRET_KEY')
DEBUG = True

HOST_IP = os.getenv('HOST_IP', 'localhost')

ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    'host.docker.internal',
    '10.0.2.2',   # эмулятор Android
    '10.0.3.2',   # Genymotion
    '172.17.0.1',
    '192.168.0.107',
]

if HOST_IP and HOST_IP != 'localhost':
    ALLOWED_HOSTS.append(HOST_IP)

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_gis',
    'rest_framework_simplejwt.token_blacklist',
    'leaflet',
    'corsheaders',
    'taxi.apps.TaxiConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
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
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': os.getenv('POSTGRES_DB'),
        'USER': os.getenv('POSTGRES_USER'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD'),
        'HOST': 'db',
        'PORT': '5432',
    }
}

INSTALLED_APPS += ['django.contrib.gis']

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,

    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': None,
    'JWK_URL': None,
    'LEEWAY': 0,

    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'USER_AUTHENTICATION_RULE': 'rest_framework_simplejwt.authentication.default_user_authentication_rule',

    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
    'TOKEN_USER_CLASS': 'rest_framework_simplejwt.models.TokenUser',

    'JTI_CLAIM': 'jti',
}

AUTH_USER_MODEL = 'taxi.User'

ACCOUNT_USER_MODEL_EMAIL_FIELD = None
ACCOUNT_EMAIL_REQUIRED = False

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


LANGUAGE_CODE = 'ru'
TIME_ZONE = 'Asia/Almaty'

USE_I18N = True

USE_L10N = True

USE_TZ = True


STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

CORS_ALLOW_ALL_ORIGINS = os.getenv('CORS_ALLOW_ALL_ORIGINS', 'False').lower() == 'true'
HOST_IP = os.getenv('HOST_IP', 'localhost')

CORS_ALLOWED_ORIGINS = [
    'http://localhost:8081',
    'http://localhost:8082',
    'http://localhost:3000',
    'http://localhost:19000',
    'http://localhost:19001',
    'http://localhost:19006',
    'http://127.0.0.1:8081',
    'http://127.0.0.1:8082',
    'http://127.0.0.1:3000',
    'http://127.0.0.1:19000',
    'http://127.0.0.1:19001',
    'http://127.0.0.1:19006',
    'http://10.0.2.2:8081',
    'http://10.0.2.2:3000',
    'http://10.0.3.2:8081',
    'http://10.0.3.2:3000',
    'exp://localhost:8081',
    'exp://localhost:19000',
    'exp://localhost:19001',
    'exp://localhost:19006',
    'exp://127.0.0.1:8081',
    'exp://127.0.0.1:19000',
    'exp://127.0.0.1:19001',
    'exp://127.0.0.1:19006',
    'http://192.168.1.100:8081',
    'http://192.168.1.100:3000',
    'http://192.168.1.100:19000',
    'http://192.168.1.100:19001',
    'http://192.168.1.100:19006',
    'http://192.168.0.108:8000',
    'http://192.168.0.107:8000'
]

if HOST_IP and HOST_IP not in ['localhost', '127.0.0.1']:
    CORS_ALLOWED_ORIGINS.extend([
        f'http://{HOST_IP}:8081',
        f'http://{HOST_IP}:3000',
        f'http://{HOST_IP}:19000',
        f'http://{HOST_IP}:19001',
        f'http://{HOST_IP}:19006',
        f'http://{HOST_IP}:8000',
        f'exp://{HOST_IP}:8081',
        f'exp://{HOST_IP}:19000',
        f'exp://{HOST_IP}:19001',
        f'exp://{HOST_IP}:19006',
    ])

CORS_ALLOW_CREDENTIALS = True

GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
