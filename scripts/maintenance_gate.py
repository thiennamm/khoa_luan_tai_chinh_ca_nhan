"""Temporary Render WSGI maintenance gate; runs before Django or database access."""
import hmac
import os
import re

HEADER = 'HTTP_X_SOTHUCHI_MAINTENANCE_KEY'
HEALTH_PATH = '/tai-khoan/dang-nhap/'
BODY = '''<!doctype html><html lang="vi"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sổ Thu Chi · Bảo trì</title><style>
body{font:18px/1.6 system-ui,sans-serif;background:#f3f7f5;color:#153d33;margin:0;padding:24px}
main{max-width:640px;margin:12vh auto}h1{font-size:30px}</style>
<main><p>SỔ THU CHI</p><h1>Hệ thống đang bảo trì</h1>
<p>Tạm ngừng thao tác để cập nhật hệ thống. Vui lòng quay lại sau.</p>
<p>Không gửi lại biểu mẫu trong thời gian này.</p></main></html>'''.encode('utf-8')


def maintenance_options(environment=None):
    environment = os.environ if environment is None else environment
    mode = environment.get('DJANGO_MAINTENANCE_MODE', '0').strip()
    if mode not in ('0', '1'):
        raise RuntimeError('DJANGO_MAINTENANCE_MODE phải là 0 hoặc 1.')
    if mode == '0':
        return False, ''
    key = environment.get('DJANGO_MAINTENANCE_BYPASS_TOKEN', '')
    if not re.fullmatch(r'[A-Za-z0-9_-]{32,128}', key) or key.startswith(('REPLACE_', 'CHANGE_')):
        raise RuntimeError('DJANGO_MAINTENANCE_BYPASS_TOKEN thiếu hoặc không hợp lệ.')
    return True, key


def require_maintenance_start(environment=None):
    enabled, _ = maintenance_options(environment)
    if not enabled:
        raise RuntimeError('Start bảo trì yêu cầu DJANGO_MAINTENANCE_MODE=1.')


class MaintenanceGate:
    def __init__(self, application, key):
        self.application = application
        self.key = key.encode('ascii')

    def __call__(self, environ, start_response):
        # Consume the operator header before Django can put it in META/error logs.
        candidate = environ.pop(HEADER, '')
        allowed = False
        if isinstance(candidate, str) and len(candidate) <= 128:
            try:
                allowed = hmac.compare_digest(candidate.encode('ascii'), self.key)
            except UnicodeEncodeError:
                pass
        if allowed:
            return self.application(environ, start_response)
        method = environ.get('REQUEST_METHOD', 'GET').upper()
        health = method in ('GET', 'HEAD') and environ.get('PATH_INFO') == HEALTH_PATH
        # Render's existing health GET remains 200, showing only this static page.
        # POST to that path is blocked too; no request reaches Django without a key.
        status = '200 OK' if health else '503 Service Unavailable'
        headers = [('Content-Type', 'text/html; charset=utf-8'), ('Content-Length', str(len(BODY))),
                   ('Cache-Control', 'no-store, private, max-age=0'), ('Pragma', 'no-cache'),
                   ('Retry-After', '120'), ('X-Content-Type-Options', 'nosniff'),
                   ('X-Frame-Options', 'DENY'), ('Referrer-Policy', 'no-referrer'),
                   ('Content-Security-Policy', "default-src 'none'; style-src 'unsafe-inline'; frame-ancestors 'none'; base-uri 'none'")]
        start_response(status, headers)
        return [] if method == 'HEAD' else [BODY]


def wrap_application(application, environment=None):
    enabled, key = maintenance_options(environment)
    return MaintenanceGate(application, key) if enabled else application
