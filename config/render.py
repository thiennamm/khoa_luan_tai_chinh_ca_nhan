"""Render Free: PostgreSQL bắt buộc, static và model là build artifacts."""
import dj_database_url
from .production_shared import *

if os.environ.get('RENDER') != 'true':
    raise ImproperlyConfigured('config.render chỉ dành cho môi trường Render được xác định.')

try:
    database_url = required('DATABASE_URL')
    parsed_db = urlsplit(database_url)
    if (parsed_db.scheme not in ('postgres', 'postgresql') or not parsed_db.hostname
            or not parsed_db.username or not parsed_db.password or not parsed_db.path.strip('/')):
        raise ValueError
    database = dj_database_url.parse(database_url, conn_max_age=0, conn_health_checks=True)
    if database['ENGINE'] != 'django.db.backends.postgresql':
        raise ValueError
except Exception:
    # Không in DATABASE_URL hoặc exception của parser (có thể chứa mật khẩu).
    raise ImproperlyConfigured('DATABASE_URL bắt buộc là kết nối PostgreSQL đầy đủ, không có fallback SQLite.') from None
database['OPTIONS'] = {**database.get('OPTIONS', {}), 'connect_timeout': 10, 'sslmode': 'require'}
DATABASES = {'default': database}
del database_url, parsed_db, database

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / '.render-static'
# Nằm trong build artifact để có sẵn khi chạy; luôn bị Git ignore, không phải storage dữ liệu.
INFERENCE_ROOT = BASE_DIR / '.render-private/inference'
MIDDLEWARE = MIDDLEWARE.copy()
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
STORAGES = {'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
            'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'}}
WHITENOISE_AUTOREFRESH = False
WHITENOISE_USE_FINDERS = False
WHITENOISE_KEEP_ONLY_HASHED_FILES = True
CLASSIFICATION_MODEL_PATH = INFERENCE_ROOT / 'en/model.joblib'
CLASSIFICATION_METADATA_PATH = INFERENCE_ROOT / 'en/metadata.json'
VI_CLASSIFICATION_MODEL_PATH = INFERENCE_ROOT / 'vi/model.joblib'
VI_CLASSIFICATION_METADATA_PATH = INFERENCE_ROOT / 'vi/metadata.json'
VI_CLASSIFICATION_ARTIFACT_MANIFEST_PATH = INFERENCE_ROOT / 'vi/artifact-manifest.json'
WSGI_APPLICATION = 'config.render_wsgi.application'
# Render public HTTP được edge redirect sang HTTPS, backend port không public.
# Waitress Render profile gán wsgi.url_scheme=https; không tin header tùy ý.
SECURE_PROXY_SSL_HEADER = None
USE_X_FORWARDED_HOST = False
