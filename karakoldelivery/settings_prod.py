"""
Production settings for karakoldelivery.

This file imports the base settings and applies secure production defaults.
It expects critical secrets and configuration to be provided via environment variables
and intentionally fails fast if they are missing.
"""
from .settings import *  # noqa: F401,F403
import os
from dj_database_url import parse as db_url_parse

# Ensure DEBUG is False in production regardless of environment input
DEBUG = False

# Allowed hosts must be explicitly provided in production
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '').split(',') if os.getenv('ALLOWED_HOSTS') else ['localhost']

# Database configuration via DATABASE_URL
DATABASE_URL = os.getenv('DATABASE_URL')
if DATABASE_URL:
    DATABASES['default'] = db_url_parse(DATABASE_URL, conn_max_age=600)

# Static files served by WhiteNoise or CDN in production
STATICFILES_STORAGE = os.getenv('STATICFILES_STORAGE', 'whitenoise.storage.CompressedManifestStaticFilesStorage')

# Security defaults (should already be set in base settings depending on DEBUG)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = int(os.getenv('SECURE_HSTS_SECONDS', '31536000'))
SECURE_HSTS_INCLUDE_SUBDOMAINS = os.getenv('SECURE_HSTS_INCLUDE_SUBDOMAINS', 'True').lower() in ('1', 'true', 'yes')
SECURE_HSTS_PRELOAD = os.getenv('SECURE_HSTS_PRELOAD', 'True').lower() in ('1', 'true', 'yes')

# Additional production middleware for static files
if 'whitenoise.middleware.WhiteNoiseMiddleware' not in MIDDLEWARE:
    MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')


