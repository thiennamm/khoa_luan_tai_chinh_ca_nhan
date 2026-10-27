from datetime import date, datetime, timezone as dt_timezone
from decimal import Decimal
from unittest.mock import patch

from django.apps import apps
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Category, Transaction, MonthlyCoverage, SavingsGoal, SavingsEntry, RecurringRule
from .monthly_report import report_data
from .services import monthly_totals


class MonthlyReportTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user('report-qa-only')
        cls.other = User.objects.create_user('report-other-only')
        cls.food = Category.objects.create(user=cls.user, name='Ăn uống', kind='expense')
        cls.games = Category.objects.create(user=cls.user, name='Giải trí', kind='expense')
        cls.salary = Category.objects.create(user=cls.user, name='Lương', kind='income')
        cls.foreign = Category.objects.create(user=cls.other, name='Ăn uống', kind='expense')
        for category, amount in [(cls.food, '75000'), (cls.games, '25000'), (cls.salary, '400000')]:
            Transaction.objects.create(user=cls.user, category=category, kind=category.kind,
                amount=Decimal(amount), date=date(2026, 10, 15))
        Transaction.objects.create(user=cls.other, category=cls.foreign, kind='expense',
            amount=Decimal('999999'), date=date(2026, 10, 15), description='MÔ TẢ RIÊNG KHÔNG ĐƯỢC LỘ')
        for category, amount in [(cls.food, '200000'), (cls.salary, '100000')]:
            Transaction.objects.create(user=cls.user, category=category, kind=category.kind,
                amount=Decimal(amount), date=date(2026, 9, 15))

    def setUp(self):
        self.client.force_login(self.user)
        self.url = reverse('finance:monthly_report')

    def page(self, month='2026-10', **params):
        return self.client.get(self.url, {'month': month, **params})

    def test_auth_get_only_and_private_cache(self):
        response = self.page()
        self.assertIn('no-store', response['Cache-Control'])
        self.assertIn('private', response['Cache-Control'])
        self.assertEqual(self.client.post(self.url).status_code, 405)
        self.client.logout()
        self.assertEqual(self.page().status_code, 302)

    def test_invalid_month_never_falls_back_to_another_report(self):
        for month in ('', 'bad', '2026-13', '2026-00', '2026-1', '2026-10-01', '0000-01'):
            with self.subTest(month=month):
                response = self.page(month)
                self.assertContains(response, 'Tháng báo cáo không hợp lệ', status_code=400)
                self.assertNotIn('current', response.context)
                self.assertNotContains(response, 'id="report-title"', status_code=400)

    def test_dashboard_link_preserves_selected_month(self):
        page = self.client.get(reverse('finance:dashboard'), {'month': '2025-12'})
        self.assertContains(page, self.url + '?month=2025-12')

    def test_totals_categories_shares_and_dashboard_match(self):
        page = self.page()
        current = page.context['current']
        self.assertEqual((current['income'], current['expense'], current['balance'], current['count']),
                         (Decimal('400000'), Decimal('100000'), Decimal('300000'), 3))
        totals = monthly_totals(self.user, date(2026, 10, 1), date(2026, 11, 1))
        dashboard = self.client.get(reverse('finance:dashboard'), {'month': '2026-10'})
        for key in totals:
            self.assertEqual(current[key], totals[key])
            self.assertEqual(current[key], dashboard.context[key])
        self.assertEqual(page.context['categories'], dashboard.context['category_statistics'])
        self.assertEqual([c['share'] for c in page.context['categories']], [Decimal('75.00'), Decimal('25.00')])
        self.assertEqual(sum(c['amount'] for c in page.context['categories']), current['expense'])
        self.assertEqual(page.context['comparisons'][1]['difference'], Decimal('-100000'))
        self.assertEqual(page.context['comparisons'][1]['percentage'], Decimal('-50.00'))

    def test_empty_zero_no_fictitious_percent_or_claim_of_no_spending(self):
        response = self.page('2025-01')
        self.assertContains(response, 'Không có giao dịch được ghi nhận')
        self.assertContains(response, 'không khẳng định không phát sinh thu/chi')
        self.assertEqual(response.context['categories'], [])
        self.assertTrue(all(c['percentage'] is None for c in response.context['comparisons']))
        self.assertEqual(response.context['previous']['month'], date(2024, 12, 1))
        self.assertEqual(response.context['current']['status'], 'unknown')

    def test_no_expense_with_income_has_no_category_share(self):
        Transaction.objects.create(user=self.user, category=self.salary, kind='income',
            amount=Decimal('50000'), date=date(2026, 1, 31))
        response = self.page('2026-01')
        self.assertEqual(response.context['current']['expense'], Decimal('0'))
        self.assertEqual(response.context['categories'], [])
        self.assertContains(response, 'Chưa có khoản chi được ghi nhận để tính cơ cấu hoặc tỷ trọng.')

    def test_year_boundary_inclusive_dates_and_stable_all_details(self):
        for day in (date(2025, 12, 31), date(2026, 1, 1), date(2026, 1, 31), date(2026, 2, 1)):
            Transaction.objects.create(user=self.user, category=self.food, kind='expense', amount=Decimal('100'), date=day)
        for _ in range(23):
            Transaction.objects.create(user=self.user, category=self.games, kind='expense', amount=Decimal('200'), date=date(2026, 1, 15))
        response = self.page('2026-01', include_details='on', page='2')
        rows = response.context['report_transactions']
        self.assertEqual(len(rows), 25)
        self.assertEqual(response.context['current']['count'], 25)
        self.assertEqual([r.pk for r in rows], list(Transaction.objects.filter(user=self.user,
            date__year=2026, date__month=1).order_by('-date', '-pk').values_list('pk', flat=True)))
        self.assertEqual(response.context['previous']['expense'], Decimal('100'))

    def test_default_no_details_and_no_other_account_or_login_info_in_article(self):
        response = self.page()
        self.assertFalse(response.context['include_details'])
        self.assertEqual(response.context['report_transactions'], [])
        detailed = self.page(include_details='on')
        self.assertNotContains(detailed, 'MÔ TẢ RIÊNG KHÔNG ĐƯỢC LỘ')
        self.assertEqual(len(detailed.context['report_transactions']), 3)
        article = detailed.content.decode().split('<article class="monthly-report"', 1)[1].split('</article>', 1)[0]
        self.assertNotIn(self.user.username, article)
        self.assertNotIn(self.other.username, article)
        self.assertNotIn('Phản hồi phân loại', article)

    def test_escaped_long_text_newlines_and_large_decimal(self):
        self.food.name = '<script>category</script> ' + 'dài' * 15
        self.food.save()
        description = '<img src=x onerror=alert(1)>\n' + 'dài' * 130
        Transaction.objects.create(user=self.user, category=self.food, kind='expense',
            amount=Decimal('999999999999999'), date=date(2026, 10, 31), description=description)
        response = self.page(include_details='on')
        self.assertEqual(response.context['current']['expense'], Decimal('1000000000099999'))
        self.assertContains(response, '1.000.000.000.099.999 VND')
        self.assertContains(response, '&lt;script&gt;category&lt;/script&gt;')
        self.assertContains(response, '&lt;img src=x onerror=alert(1)&gt;')
        self.assertNotContains(response, '<img src=x')

    def test_coverage_both_months_not_assumed_or_automatically_confirmed(self):
        with patch('django.utils.timezone.now', return_value=datetime(2026, 11, 2, tzinfo=dt_timezone.utc)):
            MonthlyCoverage.objects.create(user=self.other, month=date(2026, 10, 1), status='complete', confirmed_at=timezone.now())
            MonthlyCoverage.objects.create(user=self.user, month=date(2026, 9, 1), status='complete', confirmed_at=timezone.now())
            response = self.page()
            self.assertFalse(response.context['both_complete'])
            self.assertContains(response, 'Không diễn giải chênh lệch số đã ghi là xu hướng chi tiêu thực tế.')
            MonthlyCoverage.objects.create(user=self.user, month=date(2026, 10, 1), status='complete', confirmed_at=timezone.now())
            response = self.page()
            self.assertTrue(response.context['both_complete'])
            self.assertNotContains(response, 'Không diễn giải chênh lệch số đã ghi là xu hướng chi tiêu thực tế.')

    def test_vietnam_current_month_generated_time_even_if_other_timezone_active(self):
        instant = datetime(2026, 10, 31, 17, 0, 1, tzinfo=dt_timezone.utc)
        with patch('django.utils.timezone.now', return_value=instant), timezone.override('UTC'):
            response = self.client.get(self.url)
            self.assertEqual(response.context['report_month'], date(2026, 11, 1))
            self.assertContains(response, 'Tháng chưa kết thúc')
            self.assertContains(response, '01/11/2026 00:00:01')

    def test_savings_and_unrecorded_recurring_are_not_actual_transactions(self):
        before = report_data(self.user, date(2026, 10, 1))['current']
        goal = SavingsGoal.objects.create(user=self.user, name='Mục tiêu QA', amount=Decimal('900000'), start_date=date(2020, 1, 1))
        SavingsEntry.objects.create(goal=goal, kind='contribution', amount=Decimal('800000'), date=date(2026, 10, 1))
        RecurringRule.objects.create(user=self.user, name='Khoản dự kiến QA', kind='expense', amount=Decimal('700000'),
            category=self.food, due_day=31, start_month=date(2026, 10, 1))
        self.assertEqual(report_data(self.user, date(2026, 10, 1))['current'], before)

    def test_get_report_does_not_mutate_any_finance_model(self):
        models = list(apps.get_app_config('finance').get_models())
        before = {m.__name__: list(m.objects.order_by('pk').values()) for m in models}
        self.page(); self.page(include_details='on'); self.page('bad')
        self.assertEqual(before, {m.__name__: list(m.objects.order_by('pk').values()) for m in models})

    def test_minimum_and_maximum_calendar_months(self):
        self.assertIsNone(self.page('0001-01').context['previous'])
        self.assertEqual(self.page('9999-12').status_code, 200)
