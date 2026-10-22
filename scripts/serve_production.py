"""Waitress trên loopback. Không tự tin header proxy do client gửi."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config.production_wsgi import application


def main():
    profile = os.environ.get('DJANGO_TRANSPORT_PROFILE', 'direct')
    if profile not in ['direct', 'nginx-loopback-tls']:
        raise SystemExit('DJANGO_TRANSPORT_PROFILE không hợp lệ.')
    if profile == 'nginx-loopback-tls' and os.environ.get('DJANGO_PROXY_PROFILE_CONFIRMED') != '1':
        raise SystemExit('Chưa xác minh proxy TLS duy nhất và backend loopback riêng tư; không khởi động profile proxy.')
    try:
        port = int(os.environ.get('DJANGO_WSGI_PORT', '8000'))
        if not 1 <= port <= 65535:
            raise ValueError
    except ValueError:
        raise SystemExit('DJANGO_WSGI_PORT không hợp lệ.') from None
    from waitress import serve
    # Profile proxy chỉ dành cho nginx listen 443 -> backend loopback cùng máy.
    # Scheme cố định, không đọc X-Forwarded-*; profile direct dùng để kiểm redirect.
    serve(application, host='127.0.0.1', port=port, threads=4,
          url_scheme='https' if profile == 'nginx-loopback-tls' else 'http',
          trusted_proxy=None, clear_untrusted_proxy_headers=True,
          max_request_body_size=3 * 1024 * 1024, ident='')


if __name__ == '__main__':
    main()
