"""Kiểm cấu hình bằng process riêng; không mở database dự án."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from django.test import SimpleTestCase

ROOT = Path(__file__).resolve().parents[1]


class ProductionSettingsTests(SimpleTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='django-production-settings-')
        self.addCleanup(self.temp.cleanup)
        self.env = {k: v for k, v in os.environ.items() if not k.startswith('DJANGO_')}
        self.env.update({
            'DJANGO_SETTINGS_MODULE': 'config.production',
            'DJANGO_SECRET_KEY': 'configuration-test-only-' + 'aB3!xZ9?' * 8,
            'DJANGO_ALLOWED_HOSTS': 'deployment.invalid',
            'DJANGO_CSRF_TRUSTED_ORIGINS': 'https://deployment.invalid',
            'DJANGO_DATABASE_ENGINE': 'sqlite',
            'DJANGO_DATABASE_PATH': str(Path(self.temp.name) / 'qa.sqlite3'),
            'DJANGO_DATABASE_STORAGE': 'persistent',
            'DJANGO_STATIC_ROOT': str(Path(self.temp.name) / 'static'),
            'DJANGO_INFERENCE_DIR': str(Path(self.temp.name) / 'inference'),
        })

    def run_import(self, code='import config.production'):
        return subprocess.run([sys.executable, '-X', 'utf8', '-c', code], cwd=ROOT,
                              env=self.env, text=True, capture_output=True)

    def test_production_explicit_secure_settings_without_local_side_effect(self):
        self.env['DJANGO_DEBUG'] = '1'
        result = self.run_import('import config.production as s; import json; '
                                 'print(json.dumps([s.DEBUG,s.SESSION_COOKIE_SECURE,s.CSRF_COOKIE_SECURE,'
                                 's.SECURE_SSL_REDIRECT,s.SECURE_PROXY_SSL_HEADER,s.USE_X_FORWARDED_HOST,'
                                 'str(s.DATABASES["default"]["NAME"]),"config.local" in __import__("sys").modules]))')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), [False, True, True, True, None, False,
                                                     self.env['DJANGO_DATABASE_PATH'], False])
        self.assertFalse(Path(self.env['DJANGO_DATABASE_PATH']).exists())

    def test_every_required_value_missing_fails_without_secret_disclosure(self):
        for name in list(self.env):
            if name.startswith('DJANGO_') and name != 'DJANGO_SETTINGS_MODULE':
                value = self.env.pop(name)
                result = self.run_import()
                self.env[name] = value
                with self.subTest(name=name):
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(name, result.stderr)
                    self.assertNotIn(self.env['DJANGO_SECRET_KEY'], result.stderr)

    def test_unsafe_values_are_rejected(self):
        cases = [
            ('DJANGO_SECRET_KEY', 'django-insecure-' + 'x' * 60),
            ('DJANGO_ALLOWED_HOSTS', '*'),
            ('DJANGO_ALLOWED_HOSTS', 'https://deployment.invalid'),
            ('DJANGO_CSRF_TRUSTED_ORIGINS', 'http://deployment.invalid'),
            ('DJANGO_CSRF_TRUSTED_ORIGINS', 'https://other.invalid'),
            ('DJANGO_CSRF_TRUSTED_ORIGINS', 'https://['),
            ('DJANGO_CSRF_TRUSTED_ORIGINS', 'https://deployment.invalid:abc'),
            ('DJANGO_DATABASE_ENGINE', 'postgresql'),
            ('DJANGO_DATABASE_PATH', 'relative.sqlite3'),
            ('DJANGO_DATABASE_PATH', str(ROOT / 'db.sqlite3')),
            ('DJANGO_DATABASE_STORAGE', 'ephemeral'),
            ('DJANGO_STATIC_ROOT', str(ROOT / 'static-output')),
            ('DJANGO_STATIC_ROOT', self.temp.name),
            ('DJANGO_INFERENCE_DIR', self.env['DJANGO_STATIC_ROOT']),
            ('DJANGO_INFERENCE_DIR', str(ROOT / 'data')),
        ]
        for name, value in cases:
            old = self.env[name]
            self.env[name] = value
            result = self.run_import()
            self.env[name] = old
            with self.subTest(name=name, value=value):
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('ImproperlyConfigured', result.stderr)
                self.assertNotIn(self.env['DJANGO_SECRET_KEY'], result.stderr)

    def test_production_entrypoint_rejects_local_settings(self):
        self.env['DJANGO_SETTINGS_MODULE'] = 'config.settings'
        result = self.run_import('import config.production_wsgi')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('yêu cầu DJANGO_SETTINGS_MODULE=config.production', result.stderr)

    def test_proxy_profile_requires_explicit_confirmation(self):
        self.env['DJANGO_TRANSPORT_PROFILE'] = 'nginx-loopback-tls'
        result = self.run_import('from scripts.serve_production import main; main()')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Chưa xác minh proxy TLS', result.stderr)
