"""Một process Waitress, hai thread; chỉ dùng sau preflight/start trên Render."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    if os.environ.get('RENDER') != 'true' or os.environ.get('DJANGO_SETTINGS_MODULE') != 'config.render':
        raise SystemExit('Chỉ chạy server này với Render/config.render.')
    try:
        port = int(os.environ['PORT'])
        if not 1 <= port <= 65535 or port in (18012, 18013, 19099):
            raise ValueError
    except (KeyError, ValueError):
        raise SystemExit('PORT của Render thiếu hoặc không hợp lệ.') from None
    from config.render_wsgi import application
    from waitress import serve
    # Render tự redirect HTTP ngoài Internet và kết thúc TLS, port này không public.
    # Không wildcard trusted_proxy, không dùng X-Forwarded-For/Host/Proto từ client.
    serve(application, host='0.0.0.0', port=port, threads=2, connection_limit=32,
          url_scheme='https', trusted_proxy=None, clear_untrusted_proxy_headers=True,
          max_request_body_size=3 * 1024 * 1024, ident='')


if __name__ == '__main__':
    main()
