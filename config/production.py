"""Production SQLite trên storage bền vững (TASK 13C). Render dùng config.render."""
from .production_shared import *

if required('DJANGO_DATABASE_ENGINE') != 'sqlite':
    raise ImproperlyConfigured('Hiện chỉ chuẩn bị SQLite; trigger ngân sách chưa chuyển sang engine khác.')
db_path = absolute_path('DJANGO_DATABASE_PATH')
if db_path.is_relative_to(BASE_DIR.resolve()) or not db_path.parent.is_dir():
    raise ImproperlyConfigured('DJANGO_DATABASE_PATH phải ở thư mục riêng đã có, ngoài thư mục mã dự án.')
if required('DJANGO_DATABASE_STORAGE') != 'persistent':
    raise ImproperlyConfigured('Cần khai báo DJANGO_DATABASE_STORAGE=persistent sau khi xác minh storage hosting.')
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': db_path,
                         'OPTIONS': {'timeout': 20}}}

STATIC_URL = '/static/'
STATIC_ROOT = absolute_path('DJANGO_STATIC_ROOT')
INFERENCE_ROOT = absolute_path('DJANGO_INFERENCE_DIR')
if (STATIC_ROOT.is_relative_to(BASE_DIR.resolve()) or INFERENCE_ROOT.is_relative_to(BASE_DIR.resolve())
        or db_path.is_relative_to(STATIC_ROOT)
        or INFERENCE_ROOT.is_relative_to(STATIC_ROOT) or STATIC_ROOT.is_relative_to(INFERENCE_ROOT)):
    raise ImproperlyConfigured('Static/mô hình cần ở ngoài mã; STATIC_ROOT tách khỏi database và gói mô hình riêng tư.')
STORAGES = {'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
            'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'}}
CLASSIFICATION_MODEL_PATH = INFERENCE_ROOT / 'en/model.joblib'
CLASSIFICATION_METADATA_PATH = INFERENCE_ROOT / 'en/metadata.json'
VI_CLASSIFICATION_MODEL_PATH = INFERENCE_ROOT / 'vi/model.joblib'
VI_CLASSIFICATION_METADATA_PATH = INFERENCE_ROOT / 'vi/metadata.json'
VI_CLASSIFICATION_ARTIFACT_MANIFEST_PATH = INFERENCE_ROOT / 'vi/artifact-manifest.json'

WSGI_APPLICATION = 'config.production_wsgi.application'
