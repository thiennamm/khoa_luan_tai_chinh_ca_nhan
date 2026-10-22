"""Bảo mật chung cho production riêng tư và Render; không import local."""
import os
import re
from pathlib import Path
from urllib.parse import urlsplit
from django.core.exceptions import ImproperlyConfigured
from .base import *
from .configuration_errors import configuration_error


def required(name):
    value = os.environ.get(name, '').strip()
    if not value or value.startswith(('REPLACE_', '<')):
        raise configuration_error('CONFIG_REQUIRED', name)
    return value


def absolute_path(name):
    path = Path(required(name)).expanduser()
    if not path.is_absolute():
        raise configuration_error('ABSOLUTE_PATH_REQUIRED', name)
    return path.resolve()


DEBUG = False
SECRET_KEY = required('DJANGO_SECRET_KEY')
if len(SECRET_KEY) < 50 or len(set(SECRET_KEY)) < 5 or SECRET_KEY.startswith('django-insecure-'):
    raise configuration_error('SECRET_KEY_INVALID', 'DJANGO_SECRET_KEY')
ALLOWED_HOSTS = [s.strip().lower() for s in required('DJANGO_ALLOWED_HOSTS').split(',')]
if any(not h or not re.fullmatch(r'(?:[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?|\[::1\])', h)
       or '..' in h for h in ALLOWED_HOSTS):
    raise configuration_error('HOSTS_INVALID', 'DJANGO_ALLOWED_HOSTS')
CSRF_TRUSTED_ORIGINS = []
for origin in required('DJANGO_CSRF_TRUSTED_ORIGINS').split(','):
    try:
        parsed = urlsplit(origin.strip())
        port = parsed.port
    except ValueError:
        raise configuration_error('CSRF_ORIGINS_INVALID', 'DJANGO_CSRF_TRUSTED_ORIGINS') from None
    host = f'[{parsed.hostname}]' if parsed.hostname and ':' in parsed.hostname else parsed.hostname
    if (parsed.scheme != 'https' or host not in ALLOWED_HOSTS or parsed.username or parsed.password
            or parsed.path not in ['', '/'] or parsed.query or parsed.fragment):
        raise configuration_error('CSRF_ORIGINS_INVALID', 'DJANGO_CSRF_TRUSTED_ORIGINS', 'DJANGO_ALLOWED_HOSTS')
    CSRF_TRUSTED_ORIGINS.append(origin.strip().rstrip('/'))

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 3600
# Chưa biết quyền sở hữu/TLS tất cả subdomain: giữ warning để vận hành quyết định.
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'
SECURE_PROXY_SSL_HEADER = None
USE_X_FORWARDED_HOST = False
DATA_UPLOAD_MAX_MEMORY_SIZE = 3 * 1024 * 1024
FILE_UPLOAD_PERMISSIONS = 0o600
