"""Bảo mật chung cho production riêng tư và Render; không import local."""
import os
import re
from pathlib import Path
from urllib.parse import urlsplit
from django.core.exceptions import ImproperlyConfigured
from .base import *


def required(name):
    value = os.environ.get(name, '').strip()
    if not value or value.startswith(('REPLACE_', '<')):
        raise ImproperlyConfigured(f'Thiếu cấu hình production bắt buộc: {name}.')
    return value


def absolute_path(name):
    path = Path(required(name)).expanduser()
    if not path.is_absolute():
        raise ImproperlyConfigured(f'{name} phải là đường dẫn tuyệt đối theo máy triển khai.')
    return path.resolve()


DEBUG = False
SECRET_KEY = required('DJANGO_SECRET_KEY')
if len(SECRET_KEY) < 50 or len(set(SECRET_KEY)) < 5 or SECRET_KEY.startswith('django-insecure-'):
    raise ImproperlyConfigured('DJANGO_SECRET_KEY phải là khóa ngẫu nhiên mạnh, riêng cho production.')
ALLOWED_HOSTS = [s.strip().lower() for s in required('DJANGO_ALLOWED_HOSTS').split(',')]
if any(not h or not re.fullmatch(r'(?:[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?|\[::1\])', h)
       or '..' in h for h in ALLOWED_HOSTS):
    raise ImproperlyConfigured('DJANGO_ALLOWED_HOSTS cần tên host rõ ràng, không wildcard, scheme hoặc port.')
CSRF_TRUSTED_ORIGINS = []
for origin in required('DJANGO_CSRF_TRUSTED_ORIGINS').split(','):
    try:
        parsed = urlsplit(origin.strip())
        port = parsed.port
    except ValueError:
        raise ImproperlyConfigured('DJANGO_CSRF_TRUSTED_ORIGINS có origin không hợp lệ.') from None
    host = f'[{parsed.hostname}]' if parsed.hostname and ':' in parsed.hostname else parsed.hostname
    if (parsed.scheme != 'https' or host not in ALLOWED_HOSTS or parsed.username or parsed.password
            or parsed.path not in ['', '/'] or parsed.query or parsed.fragment):
        raise ImproperlyConfigured('CSRF trusted origins cần HTTPS origin thuộc ALLOWED_HOSTS, không wildcard/path.')
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
