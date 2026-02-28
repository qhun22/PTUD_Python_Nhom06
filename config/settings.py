"""
Cấu hình Django cho dự án QHUN22
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file if exists
load_dotenv()

# Đường dẫn gốc của dự án
BASE_DIR = Path(__file__).resolve().parent.parent

# Bảo mật
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-qhun22-mobile-shop-2024')
DEBUG = os.getenv('DEBUG', 'True').lower() in ('true', '1', 'yes')
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '127.0.0.1,localhost').split(',')

# Ứng dụng đã cài đặt
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'django.contrib.humanize',
    # Third party apps
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    # Apps tùy chỉnh
    'store',
]

# Site ID cho django-allauth
SITE_ID = 1

# Middleware
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# Cấu hình URL
ROOT_URLCONF = 'config.urls'

# Templates
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
                'store.context_processors.qhun22_context',
            ],
        },
    },
]

# WSGI
WSGI_APPLICATION = 'config.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Xác thực
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Ngôn ngữ và múi giờ
LANGUAGE_CODE = 'vi'
TIME_ZONE = 'Asia/Ho_Chi_Minh'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files (Upload)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Login URLs - Sử dụng URL tùy chỉnh của store
LOGIN_URL = 'store:login'
LOGIN_REDIRECT_URL = 'store:home'
LOGOUT_REDIRECT_URL = 'store:home'
ACCOUNT_LOGOUT_ON_GET = True  # Skip logout confirmation

# Authentication Backends
AUTHENTICATION_BACKENDS = [
    'store.backends.EmailBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

# Django-allauth settings
ACCOUNT_AUTHENTICATION_METHOD = 'email'
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_EMAIL_VERIFICATION = 'none'

# Auto signup khi Google OAuth
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_EMAIL_VERIFICATION = 'none'
SOCIALACCOUNT_QUERY_EMAIL = True  # Query email từ provider
SOCIALACCOUNT_LOGIN_ON_GET = True  # Skip intermediate confirmation page
ACCOUNT_LOGIN_ON_SUCCESS = True  # Redirect to LOGIN_REDIRECT_URL after successful login

# Cloudflare Turnstile Settings
CLOUDFLARE_TURNSTILE_SITE_KEY = os.getenv('CLOUDFLARE_TURNSTILE_SITE_KEY', '')
CLOUDFLARE_TURNSTILE_SECRET_KEY = os.getenv('CLOUDFLARE_TURNSTILE_SECRET_KEY', '')

# Google OAuth2 Settings
GOOGLE_OAUTH2_CLIENT_ID = os.getenv('GOOGLE_OAUTH2_CLIENT_ID', '')
GOOGLE_OAUTH2_CLIENT_SECRET = os.getenv('GOOGLE_OAUTH2_CLIENT_SECRET', '')

# Custom User Model
AUTH_USER_MODEL = 'store.CustomUser'

# Allauth Adapters
ACCOUNT_ADAPTER = 'store.allauth_adapter.AccountAdapter'
SOCIALACCOUNT_ADAPTER = 'store.allauth_adapter.SocialAccountAdapter'

# Messages Framework
MESSAGE_TAGS = {
    'success': 'success',
    'error': 'error',
}

# ==================== VNPAY PAYMENT GATEWAY CONFIG ====================
VNPAY_CONFIG = {
    'vnp_TmnCode': os.getenv('VNPAY_TMN_CODE', '981P6A3M'),
    'vnp_HashSecret': os.getenv('VNPAY_HASH_SECRET', '3MNKGRKED41AFWF4KJH88GCWH9KS73N5'),
    'vnp_Url': os.getenv('VNPAY_URL', 'https://sandbox.vnpayment.vn/paymentv2/vpcpay.html'),
    'vnp_ReturnUrl': os.getenv('VNPAY_RETURN_URL', 'http://localhost:8000/vnpay/return/'),
    'vnp_IpnUrl': os.getenv('VNPAY_IPN_URL', 'http://localhost:8000/vnpay/ipn/'),
    'vnp_OrderType': 'billpayment',
    'vnp_Version': '2.1.0',
    'vnp_Command': 'pay',
}
