"""Chẩn đoán build bằng dữ liệu giả/mạng giả; không mở DB hoặc dùng token thật."""
import hashlib
import importlib.util
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
from unittest import skipUnless
from unittest.mock import Mock, patch
import urllib.error
import zipfile
from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, override_settings
from config.configuration_errors import configuration_error
from scripts import download_inference_bundle as bundle

ROOT = Path(__file__).resolve().parents[1]
SENSITIVE = 'private-sentinel-do-not-log'
SENSITIVE_URL = f'https://qa:{SENSITIVE}@private.invalid/path?signature={SENSITIVE}'


class SafeDiagnosticTests(SimpleTestCase):
    def test_known_config_explains_name_unknown_config_never_echoes_message(self):
        error = configuration_error('CONFIG_REQUIRED', 'GITHUB_ARTIFACT_TOKEN')
        with self.assertRaises(ImproperlyConfigured):
            with bundle.diagnostic_stage('artifact_config'):
                raise error
        message = bundle.failure_message(error)
        self.assertIn('CONFIG_REQUIRED', message)
        self.assertIn('GITHUB_ARTIFACT_TOKEN', message)
        self.assertIn('artifact_config', message)
        for error in [ImproperlyConfigured(SENSITIVE_URL), configuration_error(SENSITIVE, SENSITIVE_URL)]:
            message = bundle.failure_message(error)
            self.assertIn('CONFIG_INVALID', message)
            self.assertNotIn(SENSITIVE, message)
            self.assertNotIn('private.invalid', message)

    def test_http_network_archive_metadata_storage_unknown_never_echo_sensitive_details(self):
        cases = [
            (urllib.error.HTTPError(SENSITIVE_URL, status, SENSITIVE, {'secret': SENSITIVE}, io.BytesIO(SENSITIVE.encode())),
             'release_lookup', f'GITHUB_HTTP_{status}') for status in [401, 403, 404, 429, 500]
        ] + [
            (urllib.error.URLError(SENSITIVE_URL), 'asset_download', 'NETWORK_ERROR'),
            (TimeoutError(SENSITIVE), 'asset_download', 'NETWORK_ERROR'),
            (zipfile.BadZipFile(SENSITIVE_URL), 'zip_extract', 'ZIP_INVALID'),
            (ValueError(SENSITIVE_URL), 'bundle_verify', 'BUNDLE_VERIFY_FAILED'),
            (KeyError(SENSITIVE), 'release_lookup', 'METADATA_INVALID'),
            (PermissionError(SENSITIVE_URL), 'build_storage', 'BUILD_STORAGE_ERROR'),
            (RuntimeError(SENSITIVE_URL), 'release_lookup', 'UNEXPECTED_ERROR'),
            (bundle.BundleError(SENSITIVE_URL), 'zip_extract', 'BUNDLE_INVALID'),
        ]
        for error, stage, code in cases:
            with self.subTest(code=code):
                error._bundle_stage = stage
                message = bundle.failure_message(error)
                self.assertIn(code, message)
                self.assertIn(stage, message)
                for secret in [SENSITIVE, 'private.invalid', SENSITIVE_URL, 'Traceback']:
                    self.assertNotIn(secret, message)

    def test_actual_archive_hash_and_zip_failures_keep_original_type_and_specific_stage(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'bad.zip'
            path.write_bytes(b'not a zip')
            with self.assertRaises(bundle.BundleError) as caught:
                bundle.install_archive(path, '0' * 64, Path(temp) / 'installed')
            self.assertIn('ARCHIVE_HASH_MISMATCH', bundle.failure_message(caught.exception))
            self.assertIn('archive_hash', bundle.failure_message(caught.exception))
            with self.assertRaises(zipfile.BadZipFile) as caught:
                bundle.install_archive(path, hashlib.sha256(path.read_bytes()).hexdigest(), Path(temp) / 'installed')
            self.assertIn('ZIP_INVALID', bundle.failure_message(caught.exception))
            self.assertIn('zip_extract', bundle.failure_message(caught.exception))
            self.assertFalse((Path(temp) / 'installed').exists())

    def test_cli_unknown_exception_has_no_traceback_or_values_and_nonzero_exit(self):
        stderr = io.StringIO()
        with patch.object(bundle, 'main', side_effect=RuntimeError(SENSITIVE_URL)), patch('sys.stderr', stderr):
            self.assertEqual(bundle.run_cli(), 1)
        self.assertIn('UNEXPECTED_ERROR', stderr.getvalue())
        self.assertNotIn(SENSITIVE, stderr.getvalue())
        self.assertNotIn('Traceback', stderr.getvalue())

    def test_diagnostic_failure_itself_stays_redacted(self):
        stderr = io.StringIO()
        with patch.object(bundle, 'main', side_effect=RuntimeError(SENSITIVE_URL)), \
                patch.object(bundle, 'failure_message', side_effect=ValueError(SENSITIVE)), patch('sys.stderr', stderr):
            self.assertEqual(bundle.run_cli(), 1)
        self.assertIn('DIAGNOSTIC_ERROR', stderr.getvalue())
        self.assertNotIn(SENSITIVE, stderr.getvalue())
        self.assertNotIn('Traceback', stderr.getvalue())

    def test_real_download_http_denial_preserves_status_without_reading_body(self):
        for status in [401, 403, 404, 429]:
            with self.subTest(status=status), tempfile.TemporaryDirectory() as temp:
                error = urllib.error.HTTPError(SENSITIVE_URL, status, SENSITIVE, {}, io.BytesIO(SENSITIVE.encode()))
                error.read = Mock(side_effect=AssertionError('must not read sensitive body'))
                opener = Mock()
                opener.open.side_effect = error
                with self.assertRaises(urllib.error.HTTPError) as caught:
                    with bundle.diagnostic_stage('asset_download'):
                        bundle.download_asset('123', SENSITIVE, Path(temp) / 'unused.zip', opener=opener)
                message = bundle.failure_message(caught.exception)
                self.assertIn(f'GITHUB_HTTP_{status}', message)
                self.assertIn('asset_download', message)
                self.assertNotIn(SENSITIVE, message)
                error.read.assert_not_called()
                self.assertFalse((Path(temp) / 'unused.zip').exists())


class BundleFlowDiagnosticTests(SimpleTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='bundle-diagnostic-')
        self.addCleanup(self.temp.cleanup)
        self.env = {'DJANGO_SETTINGS_MODULE': 'config.render', 'RENDER': 'true',
                    'GITHUB_ARTIFACT_TOKEN': SENSITIVE, 'DJANGO_MODEL_RELEASE_TAG': 'inference-vi-en-v1',
                    'DJANGO_MODEL_BUNDLE_SHA256': '0' * 64}

    @staticmethod
    def required(name):
        value = os.environ.get(name, '')
        if not value:
            raise configuration_error('CONFIG_REQUIRED', name)
        return value

    def run_flow(self, lookup_error=None, download_error=None, invalid_hash=False):
        if invalid_hash:
            self.env['DJANGO_MODEL_BUNDLE_SHA256'] = 'not-a-hash'
        stderr = io.StringIO()
        with override_settings(INFERENCE_ROOT=Path(self.temp.name) / 'inference'), \
                patch.dict(os.environ, self.env), \
                patch.dict(sys.modules, {'config.production_shared': SimpleNamespace(required=self.required)}), \
                patch.object(bundle, 'resolve_asset_id', return_value='123', side_effect=lookup_error) as lookup, \
                patch.object(bundle, 'download_asset', side_effect=download_error) as download, \
                patch.object(bundle, 'install_archive') as install, patch('sys.stderr', stderr), \
                patch('sys.stdout', io.StringIO()):
            result = bundle.run_cli()
        self.assertNotIn(SENSITIVE, stderr.getvalue())
        return result, stderr.getvalue(), lookup, download, install

    def test_invalid_hash_fails_before_lookup_or_download(self):
        result, message, lookup, download, install = self.run_flow(invalid_hash=True)
        self.assertEqual(result, 1)
        self.assertIn('DJANGO_MODEL_BUNDLE_SHA256', message)
        self.assertIn('artifact_config', message)
        lookup.assert_not_called()
        download.assert_not_called()
        install.assert_not_called()

    def test_lookup_and_download_errors_have_distinct_stages(self):
        for stage in ['release_lookup', 'asset_download']:
            error = urllib.error.HTTPError(SENSITIVE_URL, 404, SENSITIVE, {}, io.BytesIO())
            kwargs = {'lookup_error': error} if stage == 'release_lookup' else {'download_error': error}
            result, message, lookup, download, install = self.run_flow(**kwargs)
            self.assertEqual(result, 1)
            self.assertIn('GITHUB_HTTP_404', message)
            self.assertIn(stage, message)
            install.assert_not_called()
            if stage == 'release_lookup':
                download.assert_not_called()

    def test_success_keeps_selected_release_and_expected_hash(self):
        result, message, lookup, download, install = self.run_flow()
        self.assertEqual((result, message), (0, ''))
        lookup.assert_called_once_with('inference-vi-en-v1', SENSITIVE)
        self.assertEqual(download.call_args.args[0], '123')
        self.assertEqual(install.call_args.args[1], '0' * 64)


@skipUnless(all(importlib.util.find_spec(name) is not None for name in ('dj_database_url', 'psycopg')),
            'Kiểm CLI Render thật cần venv QA requirements-render; không cài thêm vào local.')
class RenderCliEnvironmentTests(SimpleTestCase):
    def setUp(self):
        self.env = {key: value for key, value in os.environ.items()
                    if not key.startswith(('DJANGO_', 'RENDER', 'DATABASE_URL', 'GITHUB_ARTIFACT_TOKEN'))}
        self.env.update({
            'DJANGO_SETTINGS_MODULE': 'config.render', 'RENDER': 'true',
            'DJANGO_SECRET_KEY': 'test-only-' + 'Ab3!?Cd4' * 8,
            'DJANGO_ALLOWED_HOSTS': 'qa.onrender.com',
            'DJANGO_CSRF_TRUSTED_ORIGINS': 'https://qa.onrender.com',
            'DATABASE_URL': f'postgresql://qa:{SENSITIVE}@localhost:1/qa',
            'GITHUB_ARTIFACT_TOKEN': SENSITIVE, 'DJANGO_MODEL_RELEASE_TAG': 'inference-vi-en-v1',
            'DJANGO_MODEL_BUNDLE_SHA256': '0' * 64,
        })

    def execute_cli(self):
        # Chặn mọi request mạng và DB; nếu code chạm chúng thay vì fail config,
        # chẩn đoán sẽ là UNEXPECTED_ERROR và kiểm thử phải thất bại.
        code = """from unittest.mock import patch
import sys
with patch('urllib.request.OpenerDirector.open', side_effect=AssertionError('network forbidden')), \
     patch('psycopg.connect', side_effect=AssertionError('database forbidden')):
 from scripts.download_inference_bundle import run_cli
 sys.exit(run_cli())
"""
        result = subprocess.run([sys.executable, '-X', 'utf8', '-c', code], cwd=ROOT,
                                env=self.env, capture_output=True, text=True, timeout=30)
        for secret in [SENSITIVE, self.env.get('DJANGO_SECRET_KEY', ''), 'localhost:1/qa']:
            if secret:
                self.assertNotIn(secret, result.stdout + result.stderr)
        self.assertNotIn('Traceback', result.stderr)
        self.assertEqual(result.returncode, 1)
        return result.stderr

    def test_each_missing_required_variable_identified_without_network_or_database(self):
        for name in ['DJANGO_SECRET_KEY', 'DJANGO_ALLOWED_HOSTS', 'DJANGO_CSRF_TRUSTED_ORIGINS',
                     'DATABASE_URL', 'GITHUB_ARTIFACT_TOKEN', 'DJANGO_MODEL_RELEASE_TAG', 'DJANGO_MODEL_BUNDLE_SHA256']:
            value = self.env.pop(name)
            message = self.execute_cli()
            self.env[name] = value
            with self.subTest(name=name):
                self.assertIn('CONFIG_REQUIRED', message)
                self.assertIn(name, message)
                self.assertNotIn('UNEXPECTED_ERROR', message)

    def test_placeholder_and_invalid_config_have_safe_specific_codes(self):
        cases = [
            ('DJANGO_SECRET_KEY', 'REPLACE_WITH_SECRET', 'CONFIG_REQUIRED'),
            ('GITHUB_ARTIFACT_TOKEN', 'REPLACE_WITH_TOKEN', 'CONFIG_REQUIRED'),
            ('DJANGO_SECRET_KEY', 'short-secret', 'SECRET_KEY_INVALID'),
            ('DJANGO_ALLOWED_HOSTS', '*', 'HOSTS_INVALID'),
            ('DJANGO_CSRF_TRUSTED_ORIGINS', SENSITIVE_URL, 'CSRF_ORIGINS_INVALID'),
            ('DATABASE_URL', f'postgresql://qa:{SENSITIVE}@[broken/qa', 'DATABASE_URL_INVALID'),
            ('DATABASE_URL', 'sqlite:///db.sqlite3', 'DATABASE_URL_INVALID'),
            ('DJANGO_MODEL_RELEASE_TAG', SENSITIVE_URL, 'RELEASE_INPUT_INVALID'),
            ('DJANGO_MODEL_BUNDLE_SHA256', 'bad-hash', 'ARCHIVE_HASH_CONFIG'),
            ('RENDER', 'false', 'RENDER_CONTEXT_INVALID'),
        ]
        for name, value, code in cases:
            original = self.env[name]
            self.env[name] = value
            message = self.execute_cli()
            self.env[name] = original
            with self.subTest(name=name, code=code):
                self.assertIn(code, message)
