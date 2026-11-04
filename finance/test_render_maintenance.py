"""WSGI behavior checks without source database, browser or operator credentials."""
from unittest.mock import Mock, patch
from types import SimpleNamespace
import os
import sys
from django.test import SimpleTestCase
from scripts.maintenance_gate import (HEADER, HEALTH_PATH, BODY, wrap_application,
                                      require_maintenance_start)

KEY = 'qa-maintenance-key-' + 'x' * 40


class MaintenanceGateTests(SimpleTestCase):
    def setUp(self):
        def application(environ, start_response):
            start_response('200 OK', [('Content-Type', 'text/plain')])
            return [b'normal application']
        self.app = Mock(side_effect=application)
        self.env = {'DJANGO_MAINTENANCE_MODE': '1', 'DJANGO_MAINTENANCE_BYPASS_TOKEN': KEY}
        self.gate = wrap_application(self.app, self.env)

    def call(self, path='/', method='GET', key=None):
        environ = {'PATH_INFO': path, 'REQUEST_METHOD': method}
        if key is not None:
            environ[HEADER] = key
        response = Mock()
        body = b''.join(self.gate(environ, response))
        return environ, response.call_args.args[0], dict(response.call_args.args[1]), body

    def test_default_off_returns_original_app(self):
        self.assertIs(wrap_application(self.app, {}), self.app)
        self.assertIs(wrap_application(self.app, {'DJANGO_MAINTENANCE_MODE': '0'}), self.app)

    def test_public_get_blocked_before_application(self):
        _, status, headers, body = self.call('/vi/')
        self.assertEqual(status, '503 Service Unavailable')
        self.assertIn('bảo trì'.encode(), body)
        self.assertEqual(headers['Cache-Control'], 'no-store, private, max-age=0')
        self.assertNotIn(KEY.encode(), body)
        self.app.assert_not_called()

    def test_all_public_write_methods_blocked_including_login_and_health(self):
        for method in ('POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'):
            for path in ('/giao-dich/them/', '/vi/chuyen/', HEALTH_PATH):
                with self.subTest(method=method, path=path):
                    _, status, _, _ = self.call(path, method)
                    self.assertTrue(status.startswith('503'))
        self.app.assert_not_called()

    def test_health_get_is_static_200_without_login_form_or_application(self):
        _, status, _, body = self.call(HEALTH_PATH)
        self.assertEqual(status, '200 OK')
        self.assertEqual(body, BODY)
        self.assertNotIn(b'<form', body)
        self.app.assert_not_called()

    def test_head_has_no_body_and_correct_content_length(self):
        for path, expected in ((HEALTH_PATH, '200'), ('/vi/', '503')):
            _, status, headers, body = self.call(path, 'HEAD')
            self.assertTrue(status.startswith(expected))
            self.assertEqual(body, b'')
            self.assertEqual(int(headers['Content-Length']), len(BODY))

    def test_exact_operator_key_passes_and_is_removed_before_django(self):
        environ, status, _, body = self.call('/vi/', key=KEY)
        self.app.assert_called_once()
        self.assertNotIn(HEADER, self.app.call_args.args[0])
        self.assertNotIn(HEADER, environ)
        self.assertEqual(body, b'normal application')

    def test_operator_post_passes_without_changing_csrf_cookie_fields(self):
        response = Mock()
        environ = {'PATH_INFO': HEALTH_PATH, 'REQUEST_METHOD': 'POST', HEADER: KEY,
                   'HTTP_COOKIE': 'qa-cookie', 'HTTP_X_CSRFTOKEN': 'qa-csrf'}
        self.assertEqual(self.gate(environ, response), [b'normal application'])
        self.assertEqual(environ['HTTP_COOKIE'], 'qa-cookie')
        self.assertEqual(environ['HTTP_X_CSRFTOKEN'], 'qa-csrf')

    def test_wrong_unicode_long_and_partial_keys_never_bypass(self):
        for key in ('wrong', KEY[:-1], KEY + 'z', 'Tiếng Việt', 'x' * 1000, ''):
            with self.subTest(kind=len(key)):
                _, status, _, body = self.call('/vi/', key=key)
                self.assertTrue(status.startswith('503'))
                self.assertNotIn(KEY.encode(), body)
        self.app.assert_not_called()

    def test_invalid_mode_or_key_fails_without_echoing_secret(self):
        for mode, key in (('bad', KEY), ('1', ''), ('1', 'short'), ('1', 'REPLACE_' + 'a' * 40)):
            with self.subTest(mode=mode):
                with self.assertRaises(RuntimeError) as result:
                    wrap_application(self.app, {'DJANGO_MAINTENANCE_MODE': mode,
                                                'DJANGO_MAINTENANCE_BYPASS_TOKEN': key})
                if key:
                    self.assertNotIn(key, str(result.exception))

    def test_maintenance_start_requires_enabled_valid_gate(self):
        require_maintenance_start(self.env)
        for env in ({}, {'DJANGO_MAINTENANCE_MODE': '0'}, {'DJANGO_MAINTENANCE_MODE': '1'}):
            with self.assertRaises(RuntimeError):
                require_maintenance_start(env)

    def test_render_server_actually_uses_gate(self):
        from scripts.serve_render import main
        with patch.dict(os.environ, {**self.env, 'RENDER': 'true',
                'DJANGO_SETTINGS_MODULE': 'config.render', 'PORT': '10001'}), \
                patch.dict(sys.modules, {'config.render_wsgi': SimpleNamespace(application=self.app)}), \
                patch('waitress.serve') as serve:
            main()
        gate = serve.call_args.args[0]
        response = Mock()
        self.assertIn('bảo trì'.encode(), b''.join(gate({'PATH_INFO': '/vi/', 'REQUEST_METHOD': 'GET'}, response)))
        self.app.assert_not_called()
