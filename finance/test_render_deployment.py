"""Kiểm chuẩn bị Render offline; không giả định đã có PostgreSQL hoặc Render."""
import hashlib
import importlib
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import Mock, patch
from unittest import skipUnless
import zipfile
from django.test import SimpleTestCase, override_settings
from scripts import download_inference_bundle as bundle

ROOT = Path(__file__).resolve().parents[1]


@skipUnless(all(importlib.util.find_spec(name) is not None
                for name in ('dj_database_url', 'psycopg', 'whitenoise', 'waitress')),
            'Nhóm runtime Render cần venv riêng có requirements-render.txt; local không bắt buộc cài.')
class RenderConfigurationTests(SimpleTestCase):
    def setUp(self):
        self.env = {k: v for k, v in os.environ.items() if not k.startswith(('DJANGO_', 'DATABASE_URL', 'RENDER'))}
        self.env.update({
            'DJANGO_SETTINGS_MODULE': 'config.render', 'RENDER': 'true',
            'DJANGO_SECRET_KEY': 'test-configuration-only-' + 'aB4!zK7?' * 8,
            'DJANGO_ALLOWED_HOSTS': 'qa.onrender.com',
            'DJANGO_CSRF_TRUSTED_ORIGINS': 'https://qa.onrender.com',
            'DATABASE_URL': 'postgresql://qa:placeholder-only@localhost:1/qa',
        })

    def run_code(self, code):
        return subprocess.run([sys.executable, '-X', 'utf8', '-c', code], cwd=ROOT,
                              env=self.env, capture_output=True, text=True)

    def test_render_requires_postgresql_and_never_falls_back(self):
        for value in ['', 'sqlite:///db.sqlite3', 'https://example.com', 'postgresql://user@localhost/db',
                      'postgresql://user:private-test-password@[broken/db']:
            with self.subTest(value=value):
                self.env['DATABASE_URL'] = value
                result = self.run_code('import config.render')
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('DATABASE_URL', result.stderr)
                self.assertNotIn('private-test-password', result.stderr)
                self.assertNotIn(self.env['DJANGO_SECRET_KEY'], result.stderr)

    def test_configuration_import_does_not_connect_and_ignores_local_paths(self):
        self.env['DJANGO_DATABASE_PATH'] = str(ROOT / 'db.sqlite3')
        self.env['DJANGO_DEBUG'] = '1'
        result = self.run_code('''from unittest.mock import patch
with patch('psycopg.connect', side_effect=AssertionError('must not connect')):
 import config.render as s
 assert not s.DEBUG
 assert s.DATABASES['default']['ENGINE']=='django.db.backends.postgresql'
 assert s.DATABASES['default']['CONN_MAX_AGE']==0
 assert s.DATABASES['default']['OPTIONS']['sslmode']=='require'
 assert s.SECURE_PROXY_SSL_HEADER is None and not s.USE_X_FORWARDED_HOST
 assert s.MIDDLEWARE[1]=='whitenoise.middleware.WhiteNoiseMiddleware'
 assert s.STORAGES['staticfiles']['BACKEND'].endswith('CompressedManifestStaticFilesStorage')
 assert s.INFERENCE_ROOT != s.STATIC_ROOT and not s.INFERENCE_ROOT.is_relative_to(s.STATIC_ROOT)
 assert 'config.local' not in __import__('sys').modules
 print('ok')
''')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), 'ok')

    def test_render_gate_and_wsgi_reject_local_context(self):
        self.env.pop('RENDER')
        result = self.run_code('import config.render')
        self.assertNotEqual(result.returncode, 0)
        self.env['DJANGO_SETTINGS_MODULE'] = 'config.settings'
        result = self.run_code('import config.render_wsgi')
        self.assertNotEqual(result.returncode, 0)

    def test_server_port_binding_and_explicit_transport(self):
        from scripts.serve_render import main
        app = object()
        with patch.dict(os.environ, {'RENDER': 'true', 'DJANGO_SETTINGS_MODULE': 'config.render', 'PORT': '10001'}), \
                patch.dict(sys.modules, {'config.render_wsgi': SimpleNamespace(application=app)}), \
                patch('waitress.serve') as serve:
            main()
        serve.assert_called_once_with(app, host='0.0.0.0', port=10001, threads=2, connection_limit=32,
            url_scheme='https', trusted_proxy=None, clear_untrusted_proxy_headers=True,
            max_request_body_size=3 * 1024 * 1024, ident='')
        for value in ['', 'bad', '0', '65536', '18012']:
            with self.subTest(value=value), patch.dict(os.environ, {'RENDER': 'true',
                    'DJANGO_SETTINGS_MODULE': 'config.render', 'PORT': value}), self.assertRaises(SystemExit):
                main()


class BundleTransportTests(SimpleTestCase):
    class Response(io.BytesIO):
        def __init__(self, code, data=b'', headers=None):
            super().__init__(data)
            self.code = code
            self.headers = headers or {}

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='private-bundle-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_token_only_on_fixed_api_host_never_forwarded(self):
        opener = Mock()
        token = 'test-only-placeholder-token'
        opener.open.side_effect = [self.Response(302, headers={'Location':
            'https://release-assets.githubusercontent.com/path?signature=test'}), self.Response(200, b'payload')]
        bundle.download_asset('123', token, self.root / 'download.zip', opener=opener)
        first, second = [c.args[0] for c in opener.open.call_args_list]
        self.assertTrue(first.full_url.startswith('https://api.github.com/repos/' + bundle.REPOSITORY + '/'))
        self.assertEqual(first.get_header('Authorization'), 'Bearer ' + token)
        self.assertIsNone(second.get_header('Authorization'))
        self.assertNotIn(token, first.full_url + second.full_url)
        self.assertEqual((self.root / 'download.zip').read_bytes(), b'payload')

    def test_resolve_release_only_uses_fixed_repo_and_exact_asset(self):
        release = {'draft': False, 'assets': [{'name': bundle.ASSET_NAME, 'id': 123,
                                             'size': 100, 'state': 'uploaded'}]}
        opener = Mock()
        opener.open.return_value = self.Response(200, json.dumps(release).encode())
        self.assertEqual(bundle.resolve_asset_id('inference-v1', 'test-token', opener), '123')
        request = opener.open.call_args.args[0]
        self.assertEqual(request.full_url, f'https://api.github.com/repos/{bundle.REPOSITORY}/releases/tags/inference-v1')
        self.assertNotIn('test-token', request.full_url)
        for invalid in [{'draft': True, 'assets': release['assets']}, {'draft': False, 'assets': []},
                        {'draft': False, 'assets': release['assets'] * 2}]:
            opener.open.return_value = self.Response(200, json.dumps(invalid).encode())
            with self.assertRaises(bundle.BundleError):
                bundle.resolve_asset_id('inference-v1', 'test-token', opener)

    def test_redirect_and_asset_validation(self):
        for location in ['http://release-assets.githubusercontent.com/x', 'https://evil.invalid/x',
                         'https://objects.githubusercontent.com@evil.invalid/x',
                         'https://objects.githubusercontent.com/x?token=test-token']:
            with self.subTest(location=location):
                opener = Mock()
                opener.open.return_value = self.Response(302, headers={'Location': location})
                with self.assertRaises(bundle.BundleError):
                    bundle.download_asset('123', 'test-token', self.root / 'download.zip', opener=opener)
                self.assertEqual(opener.open.call_count, 1)
        with self.assertRaises(bundle.BundleError):
            bundle.download_asset('../other', 'test-token', self.root / 'download.zip')

    def archive(self, *, replace=None, symlink=False, duplicate=False):
        path = self.root / 'bundle.zip'
        with zipfile.ZipFile(path, 'w') as archive:
            for name in sorted(bundle.EXPECTED_FILES):
                actual = replace if name == 'en/model.joblib' and replace else name
                info = zipfile.ZipInfo(actual)
                info.external_attr = ((stat.S_IFLNK | 0o777) if symlink and name == 'en/model.joblib'
                                      else (stat.S_IFREG | 0o600)) << 16
                archive.writestr(info, b'test-placeholder')
            if duplicate:
                # Thêm một tên khác cũng bị chặn, không chỉ dựa vào số tệp duy nhất.
                archive.writestr('unexpected.txt', b'x')
        # ZipInfo trên Windows tự đổi dấu \\ thành /. Chỉnh byte tên trong cả
        # local header và central directory để thực sự kiểm ZIP không an toàn.
        if replace and '\\' in replace:
            path.write_bytes(path.read_bytes().replace(b'en/model.joblib', replace.encode('ascii')))
        return path, hashlib.sha256(path.read_bytes()).hexdigest()

    def test_bad_hash_stops_before_zip_open(self):
        path, digest = self.archive()
        with patch('zipfile.ZipFile', side_effect=AssertionError('must not unzip')), self.assertRaises(bundle.BundleError):
            bundle.install_archive(path, '0' * 64, self.root / 'installed')
        self.assertFalse((self.root / 'installed').exists())

    def test_traversal_extra_symlink_and_failed_inner_hash_rejected(self):
        for replacement in ['../escape', '/absolute', 'C:/escape', 'en\\model.joblib']:
            path, digest = self.archive(replace=replacement)
            with self.subTest(replacement=replacement), self.assertRaises(bundle.BundleError):
                bundle.install_archive(path, digest, self.root / 'installed')
        for kwargs in [{'symlink': True}, {'duplicate': True}]:
            path, digest = self.archive(**kwargs)
            with self.assertRaises(bundle.BundleError):
                bundle.install_archive(path, digest, self.root / 'installed')
        path, digest = self.archive()
        with patch.object(bundle, 'verify', side_effect=ValueError('inner hash mismatch')), self.assertRaises(ValueError):
            bundle.install_archive(path, digest, self.root / 'installed')
        self.assertFalse((self.root / 'installed').exists())

    def test_verified_archive_installs_then_refuses_overwrite(self):
        path, digest = self.archive()
        with patch.object(bundle, 'verify') as verify:
            bundle.install_archive(path, digest, self.root / 'installed')
        verify.assert_called_once()
        self.assertEqual({p.relative_to(self.root / 'installed').as_posix()
                          for p in (self.root / 'installed').rglob('*') if p.is_file()}, bundle.EXPECTED_FILES)
        with self.assertRaises(bundle.BundleError):
            bundle.install_archive(path, digest, self.root / 'installed')


class VendorMigrationTests(SimpleTestCase):
    def test_sqlite_sql_unchanged_and_postgresql_is_gated(self):
        old = importlib.import_module('finance.migrations.0008_budget_category_guards')
        new = importlib.import_module('finance.migrations.0009_postgresql_budget_guards')
        editor = Mock()
        editor.connection.vendor = 'postgresql'
        old.apply_sqlite_guards(None, editor)
        editor.execute.assert_not_called()
        new.apply_guards(None, editor)
        editor.execute.assert_called_once_with(new.FORWARD, params=None)
        self.assertIn('FOR UPDATE', new.FORWARD)
        editor.reset_mock()
        editor.connection.vendor = 'sqlite'
        new.apply_guards(None, editor)
        editor.execute.assert_not_called()


class RenderStartupTests(SimpleTestCase):
    def test_database_failure_never_starts_or_uses_sqlite(self):
        from scripts.render_start import main
        from django.db import OperationalError
        connection = Mock(vendor='postgresql')
        connection.ensure_connection.side_effect = OperationalError('placeholder DB offline')
        with override_settings(DEBUG=False), patch.dict(os.environ, {'RENDER': 'true', 'DJANGO_SETTINGS_MODULE': 'config.render'}), \
                patch('django.setup'), patch('django.db.connection', connection), \
                patch('django.core.management.call_command') as command, \
                patch('scripts.serve_render.main') as serve:
            with self.assertRaises(OperationalError):
                main()
        self.assertEqual([c.args[0] for c in command.call_args_list], ['check', 'check_inference_models'])
        serve.assert_not_called()
