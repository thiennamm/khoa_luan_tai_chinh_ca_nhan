"""Phát triển cục bộ; giữ tương thích config.settings."""
import os
from django.core.management.utils import get_random_secret_key
from .base import *

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    secret_dir = BASE_DIR / "secrets"
    secret_dir.mkdir(exist_ok=True)
    secret_file = secret_dir / "django-secret-key.txt"
    try:
        with secret_file.open("x", encoding="utf-8") as handle:
            handle.write(get_random_secret_key())
    except FileExistsError:
        pass
    SECRET_KEY = secret_file.read_text(encoding="utf-8").strip()
    if not SECRET_KEY:
        raise RuntimeError("Khóa Django cục bộ bị trống.")

DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = ["127.0.0.1", "localhost", "[::1]"]

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}

# Artifact cục bộ đáng tin cậy; không nhận tệp/đường dẫn từ trình duyệt.
CLASSIFICATION_MODEL_PATH = os.environ.get(
    "DJANGO_CLASSIFICATION_MODEL_PATH",
    str(BASE_DIR / "data/experiments/classification/task06b-v1-final/models/char_linearsvc_C_10p0.joblib"),
)
CLASSIFICATION_METADATA_PATH = BASE_DIR / "docs/metadata/classification-experiment-results.json"

# Cấu hình độc lập: không tự chuyển sang mô hình tiếng Anh khi tiếng Việt lỗi.
VI_CLASSIFICATION_MODEL_PATH = os.environ.get(
    'DJANGO_VI_CLASSIFICATION_MODEL_PATH',
    str(BASE_DIR / 'data/experiments/classification-vietnamese/task10b-vi-v1/models/char_linearsvc_C_10.joblib'),
)
VI_CLASSIFICATION_METADATA_PATH = BASE_DIR / 'docs/metadata/vietnamese-classification-experiment-results.json'
VI_CLASSIFICATION_ARTIFACT_MANIFEST_PATH = os.environ.get(
    'DJANGO_VI_CLASSIFICATION_ARTIFACT_MANIFEST_PATH',
    str(BASE_DIR / 'data/experiments/classification-vietnamese/task10b-vi-v1/artifact-manifest.json'),
)
