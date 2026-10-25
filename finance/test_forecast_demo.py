"""Các tài khoản/bản ghi dưới đây chỉ nằm trong DB kiểm thử Django."""
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.apps import apps
from django.contrib.auth.models import User
from django.db import connection
from django.test import Client, SimpleTestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from . import forecast_demo as demo
from .forecast_math import ForecastFailure, calculate
from .models import ForecastResult, MonthlyCoverage
from .tests import FinanceCase


class DemoCalculationTests(SimpleTestCase):
    def test_fixed_scenario_decimal_dates_hash_and_independent_random_state(self):
        import random
        state = random.getstate()
        first, second = demo.scenario(), demo.scenario()
        self.assertEqual(random.getstate(), state)
        self.assertEqual(first, second)
        self.assertEqual(len(first['history']), 48)
        self.assertEqual(first['history'][0]['month'], date(2022, 1, 1))
        self.assertEqual(first['history'][-1]['month'], date(2025, 12, 1))
        self.assertEqual(first['target'], date(2026, 1, 1))
        self.assertTrue(all(isinstance(r['forecast_expense'], Decimal) and r['forecast_expense'] > 0
                            and r['month'] < first['target'] for r in first['history']))
        self.assertEqual(first['data_sha256'], '80e9c11c324370fa65ebb8ff2878346c2e70d963b6af43f2a2838bb57d42e04f')

    def test_real_calculation_repeatable_and_actual_baseline_selected(self):
        first = calculate(demo.scenario()['history'])
        second = calculate(demo.scenario()['history'])
        self.assertEqual(first['method'], 'mean3')
        self.assertEqual(first['estimate'], Decimal('7802124'))
        self.assertEqual(first['estimate'], second['estimate'])
        self.assertLessEqual(abs(Decimal(first['raw_estimate'])-Decimal(second['raw_estimate'])), Decimal('0.001'))
        self.assertEqual(first['validation_months'], [f'2025-{m:02d}-01' for m in range(7, 13)])
        self.assertEqual(len(first['candidates']), 6)
        for a, b in zip(first['candidates'], second['candidates']):
            self.assertEqual(a['method'], b['method'])
            self.assertLessEqual(abs(Decimal(a['mae'])-Decimal(b['mae'])), Decimal('0.001'))

    def test_every_ridge_origin_uses_only_past_not_target(self):
        rows = demo.scenario()['history']
        calls = []
        def predict(past, alpha):
            calls.append((list(past), alpha))
            return past[-1]
        with patch('finance.forecast_math.ridge_predict', side_effect=predict):
            result = calculate(rows)
        for group, alpha in enumerate([0.1, 1.0, 10.0]):
            for step in range(6):
                past, actual_alpha = calls[group*6+step]
                self.assertEqual(past, [r['forecast_expense'] for r in rows[:42+step]])
                self.assertEqual(alpha, actual_alpha)
        self.assertEqual(len(calls), 18 + int(result['method'].startswith('ridge_')))
        changed = [dict(row) for row in rows]
        changed[-1]['forecast_expense'] += Decimal('9999999')
        with patch('finance.forecast_math.ridge_predict', side_effect=predict):
            later = calculate(changed)
        for first, second in zip(result['candidates'], later['candidates']):
            self.assertEqual(first['points'][:-1], second['points'][:-1])
            self.assertEqual(first['points'][-1]['predicted'], second['points'][-1]['predicted'])

    def test_chart_keeps_prediction_separate_from_48_historical_values(self):
        source = demo.scenario()
        before = demo.chart(source, None)
        after = demo.chart(source, {'estimate': Decimal('8000000')})
        self.assertEqual(len(before['history'].split()), 48)
        self.assertEqual(len(after['history'].split()), 48)
        self.assertNotIn('predicted', before)
        self.assertEqual(len(after['forecast'].split()), 2)
        self.assertEqual(after['predicted']['x'], '875.00')


class DemoWebTests(FinanceCase):
    def setUp(self):
        super().setUp()
        self.url = reverse('finance:forecast_demo')
        self.cache_patch = patch.object(demo, '_cached', None)
        self.cache_patch.start()
        self.addCleanup(self.cache_patch.stop)
        # Bản ghi không rỗng để phát hiện cả sửa nội dung, không chỉ đếm dòng.
        for user in [self.alice, self.bob]:
            MonthlyCoverage.objects.create(user=user, month=date(2020, 1, 1),
                status='complete', confirmed_at=timezone.now())
            ForecastResult.objects.create(user=user, target_month=date(2020, 2, 1),
                fingerprint='a'*64, history_count=3, history_start=date(2019, 11, 1),
                history_end=date(2020, 1, 1), method='mean3', estimate='111111',
                details={'private': str(user.pk)}, configuration={'private': True})

    def all_rows(self):
        models = [User, *apps.get_app_config('finance').get_models()]
        return {m._meta.label: list(m.objects.order_by('pk').values()) for m in models}

    def test_get_auth_and_post_csrf(self):
        anonymous = Client()
        for method in [anonymous.get, anonymous.post]:
            self.assertEqual(method(self.url).status_code, 302)
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.alice)
        self.assertEqual(csrf_client.post(self.url).status_code, 403)
        page = csrf_client.get(self.url)
        self.assertEqual(page.status_code, 200)
        with patch.object(demo, 'calculate', wraps=calculate) as fit:
            response = csrf_client.post(self.url, {'csrfmiddlewaretoken': csrf_client.cookies['csrftoken'].value})
        self.assertEqual(response.status_code, 302)
        fit.assert_called_once()

    def test_get_no_calculation_or_database_write_and_personal_link(self):
        before = self.all_rows()
        with patch.object(demo, 'calculate') as fit, CaptureQueriesContext(connection) as queries:
            page = self.client.get(self.url)
        fit.assert_not_called()
        self.assertFalse(any(q['sql'].lstrip().upper().startswith(('INSERT', 'UPDATE', 'DELETE')) for q in queries))
        self.assertIsNone(demo._cached)
        self.assertEqual(before, self.all_rows())
        self.assertContains(page, 'Dữ liệu mô phỏng — chỉ để minh họa')
        self.assertContains(page, '01/2026')
        self.assertNotContains(page, 'id="demo-result"')
        self.assertContains(self.client.get(reverse('finance:forecast')), self.url)

    def test_real_post_does_not_change_any_personal_rows_and_get_does_not_refit(self):
        before = self.all_rows()
        response = self.client.post(self.url, {'user_id': self.bob.pk, 'target': '2099-01-01', 'seed': '1'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(before, self.all_rows())
        with patch.object(demo, 'calculate') as fit:
            page = self.client.get(self.url)
        fit.assert_not_called()
        self.assertEqual(before, self.all_rows())
        self.assertContains(page, '7.802.124 VND')
        self.assertContains(page, 'PHƯƠNG PHÁP ĐỐI CHỨNG')
        self.assertContains(page, 'data-series="forecast-point"')
        self.assertContains(page, 'không phải giá trị thực tế')
        self.assertContains(page, 'không phải sai số test độc lập')
        self.assertEqual(page.context['result']['method'], 'mean3')
        self.assertEqual(len(page.context['comparisons']), 6)
        self.assertEqual(page.context['source']['target'], date(2026, 1, 1))

    def test_other_account_sees_only_shared_synthetic_demo_not_personal_values(self):
        self.client.post(self.url)
        self.client.force_login(self.bob)
        before = self.all_rows()
        page = self.client.get(self.url)
        self.assertNotContains(page, 'Giao dịch riêng Alice')
        self.assertNotContains(page, 'Giao dịch bí mật Bob')
        self.assertNotContains(page, '111.111 VND')
        self.assertEqual(before, self.all_rows())
        self.assertEqual(page.context['source']['data_sha256'], demo.scenario()['data_sha256'])

    def test_config_change_invalidates_cache_without_get_recalculation(self):
        self.client.post(self.url)
        cached = demo._cached
        with patch.dict(demo.DEMO, {'version': 'changed-for-test'}), patch.object(demo, 'calculate') as fit:
            page = self.client.get(self.url)
        fit.assert_not_called()
        self.assertIsNone(page.context['result'])
        self.assertIs(demo._cached, cached)

    def test_ml_failure_is_explicit_and_no_baseline_result_or_db_write(self):
        before = self.all_rows()
        with patch('finance.forecast_math.ridge_predict', side_effect=RuntimeError('test runtime')):
            page = self.client.post(self.url)
        self.assertEqual(page.status_code, 503)
        self.assertContains(page, 'Không chạy được bước ML thử nghiệm', status_code=503)
        self.assertNotContains(page, 'id="demo-result"', status_code=503)
        self.assertEqual(before, self.all_rows())
        self.assertIsNone(demo._cached)

    def test_run_reuses_core_and_returns_defensive_cache_copy(self):
        source = demo.scenario()
        expected = {'method': 'mean3', 'estimate': Decimal('123')}
        with patch.object(demo, 'calculate', return_value=expected) as core:
            demo.run_demo(source)
        core.assert_called_once_with(source['history'])
        first = demo.cached_result(source)
        first['estimate'] = Decimal('0')
        self.assertEqual(demo.cached_result(source)['estimate'], Decimal('123'))

    def test_unsupported_methods_do_not_run_or_write(self):
        before = self.all_rows()
        with patch.object(demo, 'calculate') as core:
            self.assertEqual(self.client.put(self.url).status_code, 405)
        core.assert_not_called()
        self.assertEqual(before, self.all_rows())
