"""Chẩn đoán bằng mã và tên biến được phép; không đọc/in giá trị env."""
from django.core.exceptions import ImproperlyConfigured

VARIABLES = frozenset({
    'DJANGO_SETTINGS_MODULE', 'RENDER', 'DJANGO_SECRET_KEY', 'DJANGO_ALLOWED_HOSTS',
    'DJANGO_CSRF_TRUSTED_ORIGINS', 'DATABASE_URL', 'GITHUB_ARTIFACT_TOKEN',
    'DJANGO_MODEL_RELEASE_TAG', 'DJANGO_MODEL_BUNDLE_SHA256',
    'DJANGO_DATABASE_ENGINE', 'DJANGO_DATABASE_PATH', 'DJANGO_DATABASE_STORAGE',
    'DJANGO_STATIC_ROOT', 'DJANGO_INFERENCE_DIR',
})
MESSAGES = {
    'CONFIG_REQUIRED': 'Thiếu cấu hình bắt buộc, để trống hoặc vẫn là placeholder.',
    'SECRET_KEY_INVALID': 'Khóa cần ngẫu nhiên, ít nhất 50 ký tự và không dùng tiền tố django-insecure-.',
    'HOSTS_INVALID': 'Cần host cụ thể, không scheme, port hoặc wildcard.',
    'CSRF_ORIGINS_INVALID': 'Cần HTTPS origin thuộc ALLOWED_HOSTS, port hợp lệ, không path/query/wildcard.',
    'DATABASE_URL_INVALID': 'Cần PostgreSQL URL đầy đủ user, password, host và database; không fallback SQLite.',
    'RENDER_CONTEXT_INVALID': 'Cần môi trường Render và DJANGO_SETTINGS_MODULE=config.render.',
    'ABSOLUTE_PATH_REQUIRED': 'Cần đường dẫn tuyệt đối trên máy triển khai.',
    'CONFIG_INVALID': 'Cấu hình Django chưa hợp lệ; không hiển thị nội dung exception.',
}


def describe_configuration_error(error):
    code = getattr(error, 'configuration_code', None)
    fields = getattr(error, 'configuration_variables', ())
    if (type(code) is not str or code not in MESSAGES or not isinstance(fields, tuple)
            or any(type(name) is not str or name not in VARIABLES for name in fields)):
        return 'CONFIG_INVALID', MESSAGES['CONFIG_INVALID']
    names = ', '.join(fields)
    return code, MESSAGES[code] + (f' Biến cần kiểm tra: {names}.' if names else '')


def configuration_error(code, *variables):
    error = ImproperlyConfigured()
    error.configuration_code = code
    error.configuration_variables = variables
    safe_code, message = describe_configuration_error(error)
    error.args = (f'[{safe_code}] {message}',)
    return error
