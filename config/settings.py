"""Cấu hình phát triển cục bộ, bí mật được lưu ngoài mã nguồn."""
import os
from pathlib import Path
from django.core.management.utils import get_random_secret_key

BASE_DIR = Path(__file__).resolve().parent.parent
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
INSTALLED_APPS = [
    "django.contrib.auth", "django.contrib.contenttypes", "django.contrib.sessions",
    "django.contrib.messages", "django.contrib.staticfiles", "finance",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "config.urls"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "templates"], "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]
WSGI_APPLICATION = "config.wsgi.application"
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LANGUAGE_CODE = "vi"
TIME_ZONE = "Asia/Ho_Chi_Minh"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "finance:dashboard"
LOGOUT_REDIRECT_URL = "login"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
X_FRAME_OPTIONS = "DENY"

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

# Website hiện chỉ có luồng upload CSV; chặn sớm tệp vượt 2 MiB.
FILE_UPLOAD_HANDLERS = [
    'finance.upload_handlers.CsvSizeLimitHandler',
    'django.core.files.uploadhandler.MemoryFileUploadHandler',
    'django.core.files.uploadhandler.TemporaryFileUploadHandler',
]
