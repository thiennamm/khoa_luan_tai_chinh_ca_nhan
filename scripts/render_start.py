"""Startup Free không cần shell/pre-deploy; DB lỗi thì dừng, không fallback."""
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    if os.environ.get('DJANGO_SETTINGS_MODULE') != 'config.render' or os.environ.get('RENDER') != 'true':
        raise RuntimeError('Render environment required')
    import django
    django.setup()
    from django.conf import settings
    from django.db import connection
    from django.core.management import call_command
    if settings.DEBUG or connection.vendor != 'postgresql':
        raise RuntimeError('Production PostgreSQL required')
    call_command('check', deploy=True)
    call_command('check_inference_models')
    # Session-level advisory lock tránh hai lần startup triển khai cùng migrate.
    # Chỉ dùng PostgreSQL đã cấu hình; không đụng SQLite. Không in DSN/lỗi DB.
    lock_id = 73140221
    connection.ensure_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT pg_try_advisory_lock(%s)', [lock_id])
            if not cursor.fetchone()[0]:
                raise RuntimeError('Migration startup lock busy; retry deploy later')
        try:
            call_command('migrate', interactive=False, verbosity=1)
            call_command('migrate', check_unapplied=True, interactive=False, verbosity=0)
            call_command('cleanup_csv_imports')
        finally:
            with connection.cursor() as cursor:
                cursor.execute('SELECT pg_advisory_unlock(%s)', [lock_id])
    finally:
        connection.close()
    from scripts.serve_render import main as serve
    serve()


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        # Không in exception DB/parser vì có thể chứa host/user/DSN.
        print(f'Render startup thất bại ({type(exc).__name__}); kiểm env, PostgreSQL và preflight. Không fallback SQLite.', file=sys.stderr)
        raise SystemExit(1) from None
