from datetime import date, datetime, timezone as dt_timezone
from decimal import Decimal
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from django.apps import apps
from django.contrib.auth.models import User
from django.db import connection
from django.test import TestCase, SimpleTestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from .models import Category, MonthlyCoverage, Transaction, RecurringRule, SavingsGoal, SavingsEntry
from .monthly_report import MonthlyReportForm, change, report_data
from .services import monthly_totals
from .statistics import financial_statistics


class MonthChangeTests(SimpleTestCase):
    def test_positive_zero_negative_base_and_half_up(self):
        self.assertEqual(change(Decimal('32'), Decimal('33'))['percentage'], Decimal('3.13'))
        self.assertEqual(change(Decimal('100'), Decimal('50'))['direction'], 'Giảm')
        self.assertEqual(change(Decimal('7'), Decimal('7'))['direction'], 'Không đổi')
        for before, expected in [('0', 'tháng gốc bằng 0'), ('-50', 'tháng gốc âm')]:
            result = change(Decimal(before), Decimal('80'))
            self.assertIsNone(result['percentage'])
            self.assertIn(expected, result['ratio_note'])
            self.assertEqual(result['difference'], Decimal('80') - Decimal(before))

    def test_strict_two_months_no_silent_invalid_fallback(self):
        for name in ('month', 'base_month'):
            for value in ('', '2026-2', '2026-13', '0000-01', '2026-01-01', 'bad'):
                form = MonthlyReportForm({'month':'2026-02', 'base_month':'2026-01', name:value})
                self.assertFalse(form.is_valid(), (name, value))


class MonthComparisonTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user('comparison-qa')
        cls.other = User.objects.create_user('comparison-other')
        cls.food = Category.objects.create(user=cls.user, name='Ăn uống', kind='expense')
        cls.new = Category.objects.create(user=cls.user, name='Chỉ tháng B', kind='expense')
        cls.old = Category.objects.create(user=cls.user, name='Chỉ tháng A', kind='expense')
        cls.salary = Category.objects.create(user=cls.user, name='Ăn uống', kind='income')
        cls.foreign = Category.objects.create(user=cls.other, name='Ăn uống', kind='expense')
        for category, amount, day in [(cls.food,'100',date(2025,12,31)),(cls.old,'50',date(2025,12,1)),
            (cls.salary,'500',date(2025,12,15)),(cls.food,'400',date(2026,1,1)),
            (cls.new,'75',date(2026,1,31)),(cls.salary,'700',date(2026,1,15)),
            (cls.foreign,'99999',date(2026,1,15))]:
            Transaction.objects.create(user=category.user, category=category, kind=category.kind,
                                       amount=Decimal(amount), date=day)

    def setUp(self):
        self.client.force_login(self.user)
        self.url = reverse('finance:monthly_report')

    def page(self, a='2025-12', b='2026-01', **params):
        return self.client.get(self.url, {'base_month':a,'month':b,**params})

    def test_arbitrary_pair_matches_dashboard_report_and_totals(self):
        response = self.page()
        for month, name, end in [(date(2025,12,1),'previous',date(2026,1,1)),
                                 (date(2026,1,1),'current',date(2026,2,1))]:
            item=response.context[name]
            totals=monthly_totals(self.user,month,end)
            stats=financial_statistics(self.user,month,6)['monthly_statistics'][-1]
            single=report_data(self.user,month)['current']
            for key in ('income','expense','balance'):
                self.assertEqual(item[key],totals[key])
                self.assertEqual(item[key],stats[key])
                self.assertEqual(item[key],single[key])
                self.assertIsInstance(item[key],Decimal)
        self.assertEqual(response.context['comparisons'][1]['difference'],Decimal('325'))
        self.assertEqual(response.context['comparisons'][1]['percentage'],Decimal('216.67'))
        self.assertContains(response,'B − A')

    def test_categories_union_by_id_stable_sort_links_and_renaming(self):
        self.food.name='Tên mới dùng cho cả lịch sử';self.food.save()
        rows=self.page().context['category_comparisons']
        self.assertEqual([r['id'] for r in rows],[self.food.pk,self.new.pk,self.old.pk])
        self.assertEqual([(r['a'],r['b']) for r in rows],[(Decimal('100'),Decimal('400')),
            (Decimal('0'),Decimal('75')),(Decimal('50'),Decimal('0'))])
        self.assertEqual(rows[0]['name'],self.food.name)
        self.assertNotIn(self.foreign.pk,[r['id'] for r in rows])
        self.assertNotIn(self.salary.pk,[r['id'] for r in rows])
        target=self.client.get(rows[0]['a_url'])
        self.assertEqual(target.context['expense'],Decimal('100'))
        self.assertEqual(target.context['page_obj'].paginator.count,1)
        self.assertContains(target,'Trở về so sánh hai tháng đã chọn')
        self.assertIn('base_month=2025-12',target.context['comparison_url'])

    def test_same_month_all_differences_zero_with_actual_data(self):
        response=self.page('2026-01','2026-01')
        self.assertTrue(all(row['difference']==0 and row['direction']=='Không đổi'
                            for row in response.context['comparisons']+response.context['category_comparisons']))
        self.assertEqual(response.context['current']['count'],3)
        self.assertEqual(len(response.context['comparison_chart']),2)

    def test_zero_empty_only_income_only_expense_and_negative_net(self):
        empty=self.page('2024-03','2024-04')
        self.assertFalse(empty.context['category_comparisons'])
        self.assertTrue(all(row['percentage'] is None for row in empty.context['comparisons']))
        self.assertContains(empty,'Không tính tỷ lệ: tháng gốc bằng 0')
        self.assertContains(empty,'không khẳng định không phát sinh thu/chi')
        Transaction.objects.create(user=self.user,category=self.food,kind='expense',amount=Decimal('80'),date=date(2024,3,2))
        Transaction.objects.create(user=self.user,category=self.salary,kind='income',amount=Decimal('20'),date=date(2024,4,2))
        response=self.page('2024-03','2024-04')
        net=response.context['comparisons'][2]
        self.assertEqual(net['difference'],Decimal('100'))
        self.assertIsNone(net['percentage'])
        self.assertContains(response,'Không tính tỷ lệ: tháng gốc âm')

    def test_vietnam_default_year_boundary_and_timestamp(self):
        instant=datetime(2025,12,31,17,0,1,tzinfo=dt_timezone.utc)
        with patch('django.utils.timezone.now',return_value=instant),timezone.override('UTC'):
            response=self.client.get(self.url)
        self.assertEqual(response.context['base_month'],date(2025,12,1))
        self.assertEqual(response.context['report_month'],date(2026,1,1))
        self.assertContains(response,'Tháng đang diễn ra')
        self.assertContains(response,'01/01/2026 00:00:01')
        self.assertEqual(response.context['report_form']['base_month'].value(),'2025-12')

    def test_leap_day_inclusive_and_nonadjacent_months(self):
        for day in (date(2024,1,31),date(2024,2,1),date(2024,2,29),date(2024,3,1)):
            Transaction.objects.create(user=self.user,category=self.food,kind='expense',amount=Decimal('10'),date=day)
        result=self.page('2024-02','2026-01')
        self.assertEqual(result.context['previous']['expense'],Decimal('20'))
        self.assertEqual(result.context['previous']['count'],2)
        self.assertEqual(result.context['current']['expense'],Decimal('475'))

    def test_coverage_current_future_and_unknown_never_automatically_confirmed(self):
        MonthlyCoverage.objects.create(user=self.user,month=date(2025,12,1),status='complete',confirmed_at=timezone.now())
        MonthlyCoverage.objects.create(user=self.user,month=date(2026,1,1),status='incomplete')
        page=self.page()
        self.assertEqual(page.context['previous']['status'],'complete')
        self.assertEqual(page.context['current']['status'],'incomplete')
        self.assertFalse(page.context['both_complete'])
        self.assertContains(page,'số liệu có thể thiếu')
        with patch('django.utils.timezone.now',return_value=datetime(2026,1,15,tzinfo=dt_timezone.utc)):
            current=self.page()
        self.assertEqual(current.context['current']['future_count'],1)
        self.assertContains(current,'1 giao dịch có ngày tương lai trong tháng B')
        self.assertEqual(current.context['current']['expense'],Decimal('475'))
        MonthlyCoverage.objects.filter(user=self.user).update(status='complete',confirmed_at=timezone.now())
        self.assertTrue(self.page().context['both_complete'])

    def test_large_decimal_sql_aggregation_without_float_rounding(self):
        # Group totals exceed float exactness; many categories still sum exactly.
        for _ in range(25):
            Transaction.objects.create(user=self.user,category=self.food,kind='expense',
                amount=Decimal('999999999999999'),date=date(2026,1,20))
        result=self.page()
        self.assertEqual(result.context['current']['expense'],Decimal('25000000000000450'))
        self.assertEqual(sum((r['b'] for r in result.context['category_comparisons']),Decimal('0')),
                         result.context['current']['expense'])
        self.assertEqual(result.context['comparison_chart'][1]['expense'],result.context['current']['expense'])
        self.assertContains(result,'25.000.000.000.000.450 VND')

    def test_auth_owner_get_only_and_cache(self):
        response=self.page(user_id=self.other.pk)
        self.assertNotContains(response,'99.999 VND')
        self.assertIn('private',response['Cache-Control']);self.assertIn('no-store',response['Cache-Control'])
        self.assertEqual(self.client.post(self.url).status_code,405)
        self.client.force_login(self.other)
        other=self.page()
        self.assertEqual(other.context['current']['expense'],Decimal('99999'))
        self.assertEqual(other.context['previous']['count'],0)
        self.assertEqual([r['id'] for r in other.context['category_comparisons']],[self.foreign.pk])
        self.client.logout();self.assertEqual(self.page().status_code,302)

    def test_invalid_either_month_does_not_display_unfiltered_data(self):
        for a,b in [('wrong','2026-01'),('2025-12','2026-14'),('','2026-01')]:
            response=self.page(a,b)
            self.assertEqual(response.status_code,400)
            self.assertNotIn('current',response.context)

    def test_html_escaped_and_long_category_names(self):
        self.food.name='<img src=x onerror=alert(1)>'+('dài'*17);self.food.save()
        response=self.page()
        self.assertContains(response,'&lt;img src=x onerror=alert(1)&gt;')
        self.assertNotContains(response,'<img src=x')

    def test_two_grouped_queries_independent_of_category_count(self):
        def measure():
            with CaptureQueriesContext(connection) as queries:
                data=report_data(self.user,date(2026,1,1),base_month=date(2025,12,1))
            self.assertEqual(len(queries),2)
            # PostgreSQL iterator() is a read-only server-side SELECT cursor.
            statements=[q['sql'].lstrip().upper() for q in queries]
            self.assertTrue(all(sql.startswith('SELECT') or
                                (sql.startswith('DECLARE ') and ' FOR SELECT ' in sql) for sql in statements))
            self.assertIn('GROUP BY',queries[0]['sql'].upper())
            return data
        measure()
        for index in range(30):
            category=Category.objects.create(user=self.user,name=f'QA nhóm {index}',kind='expense')
            Transaction.objects.create(user=self.user,category=category,kind='expense',amount=Decimal('10'),date=date(2026,1,2))
        self.assertEqual(len(measure()['category_comparisons']),33)

    def test_unrecorded_plans_and_savings_never_in_totals_and_get_read_only(self):
        before=report_data(self.user,date(2026,1,1),base_month=date(2025,12,1))['current']
        RecurringRule.objects.create(user=self.user,name='QA dự kiến',kind='expense',category=self.food,
            amount=Decimal('123456'),due_day=31,start_month=date(2026,1,1))
        goal=SavingsGoal.objects.create(user=self.user,name='QA mục tiêu',amount=Decimal('999999'),start_date=date(2025,1,1))
        SavingsEntry.objects.create(goal=goal,kind='contribution',amount=Decimal('999'),date=date(2026,1,3))
        models=list(apps.get_app_config('finance').get_models())
        snapshot=lambda:{m.__name__:list(m.objects.order_by('pk').values()) for m in models}
        state=snapshot()
        self.assertEqual(self.page().context['current'],before)
        self.page(include_details='on');self.page('bad','bad')
        self.assertEqual(snapshot(),state)

    def test_links_full_result_pagination_and_preserve_pair(self):
        for _ in range(22):
            Transaction.objects.create(user=self.user,category=self.food,kind='expense',amount=Decimal('10'),date=date(2026,1,2))
        item=self.page().context['category_comparisons'][0]
        page=self.client.get(item['b_url'])
        self.assertEqual(page.context['page_obj'].paginator.count,23)
        self.assertEqual(page.context['expense'],Decimal('620'))
        second=self.client.get(reverse('finance:transaction_list')+'?'+page.context['filter_query']+'&page=2')
        self.assertEqual(len(second.context['page_obj']),3)
        self.assertEqual(parse_qs(urlsplit(second.context['comparison_url']).query),
                         {'base_month':['2025-12'],'month':['2026-01']})
        self.assertContains(second,'name="comparison_a"')
        foreign=self.client.get(reverse('finance:transaction_list'),{'period':'month','month':'2026-01','category':self.foreign.pk})
        self.assertFalse(foreign.context['filters_valid'])

    def test_min_max_same_month_and_equal_increase_sort_ties(self):
        for month in ('0001-01','9999-12'):
            self.assertEqual(self.page(month,month).status_code,200)
        Transaction.objects.create(user=self.user,category=self.old,kind='expense',amount=Decimal('125'),date=date(2026,1,2))
        rows=self.page().context['category_comparisons']
        tied=[r['id'] for r in rows if r['difference']==75]
        self.assertEqual(tied,sorted([self.new.pk,self.old.pk]))
