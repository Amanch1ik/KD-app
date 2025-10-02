from .settings import *

# Development overrides: lightweight cache and test-friendly defaults
DEBUG = True
ALLOWED_HOSTS = ['*']
SECRET_KEY = 'dev-key-for-tests-001'

# Simple in-memory cache to avoid Redis in tests
try:
    from django.core.cache.backends.locmem import LocMemCache  # type: ignore
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    }
except Exception:
    pass

# Disable strict security features for local development
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_HSTS_SECONDS = 0

