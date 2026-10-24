from datetime import date
from decimal import Decimal
from unittest.mock import patch
from django.test import SimpleTestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from .models import Category, Transaction, MonthlyCoverage
from .coverage import monthly_history
from .statistics import chart_axis, financial_statistics
from .tests import FinanceCase


class ChartAxisTests(SimpleTestCase):
    def test_compact_labels_use_vietnamese_decimal_separator(self):
        axis = chart_axis(Decimal('125000'))
        self.assertEqual(axis['chart_axis_unit'], 'nghìn VND')
        self.assertEqual([t['label'] for t in axis['chart_axis_ticks']],
                         ['125', '93,75', '62,5', '31,25', '0'])
        self.assertEqual([t['value'] for t in axis['chart_axis_ticks']],
                         [Decimal('125000'), Decimal('93750'), Decimal('62500'),
                          Decimal('31250'), Decimal('0')])

    def test_zero_has_no_fictitious_positive_limit(self):
        axis = chart_axis(Decimal('0'))
        self.assertEqual(axis['chart_axis_unit'], 'VND')
        self.assertEqual(axis['chart_axis_ticks'], [{'position': 0, 'value': Decimal('0'), 'label': '0'}])

    def test_scale_boundaries_and_rounding_preserve_exact_values(self):
        for amount, unit in [('999', 'VND'), ('1000', 'nghìn VND'),
                             ('1000000', 'triệu VND'), ('1000000000', 'tỷ VND'),
                             ('1000000000000', 'nghìn tỷ VND'),
                             ('25000000000124975', 'triệu tỷ VND')]:
            with self.subTest(amount=amount):
                axis = chart_axis(Decimal(amount))
                self.assertEqual(axis['chart_axis_unit'], unit)
                self.assertEqual(axis['chart_axis_ticks'][0]['value'], Decimal(amount))
                self.assertTrue(all(len(t['label']) <= 6 for t in axis['chart_axis_ticks']))


class FinancialStatisticsTests(FinanceCase):
    def row(self, category=None, amount='100', day=date(2026,10,15), kind='expense'):
        return Transaction.objects.create(user=self.alice, category=category or self.food,
            amount=Decimal(amount), date=day, kind=kind)

    def test_categories_by_id_sorted_and_exactly_match_total(self):
        second=Category.objects.create(user=self.alice,name='Khác',kind='expense')
        # Cùng tên ở tài khoản khác/loại thu khác vẫn là danh mục khác.
        Category.objects.filter(pk=self.bob_category.pk).update(name=second.name)
        Category.objects.filter(pk=self.salary.pk).update(name=second.name)
        self.row(second,'250000')
        self.row(amount='25000')
        self.row(self.salary,'900000',kind='income')
        result=financial_statistics(self.alice,date(2026,10,1),6)
        cats=result['category_statistics']
        self.assertEqual([c['id'] for c in cats],[second.pk,self.food.pk])
        self.assertEqual([c['amount'] for c in cats],[Decimal('250000'),Decimal('150000')])
        self.assertEqual(sum(c['amount'] for c in cats),result['statistics_expense'])
        self.assertEqual([c['share'] for c in cats],[Decimal('62.50'),Decimal('37.50')])
        self.assertNotIn(self.bob_category.pk,[c['id'] for c in cats])

    def test_six_twelve_months_cross_year_and_inclusive_boundaries(self):
        for day in [date(2025,9,30),date(2025,10,1),date(2026,3,31),date(2026,4,1)]:self.row(day=day)
        result=financial_statistics(self.alice,date(2026,3,1),6)
        months=result['monthly_statistics']
        self.assertEqual([m['month'] for m in months],[date(2025,10,1),date(2025,11,1),date(2025,12,1),date(2026,1,1),date(2026,2,1),date(2026,3,1)])
        self.assertEqual(sum(m['expense'] for m in months),Decimal('200'))
        self.assertEqual(len(financial_statistics(self.alice,date(2026,3,1),12)['monthly_statistics']),12)

    def test_zero_unknown_and_confirmed_zero_do_not_change_forecast_semantics(self):
        MonthlyCoverage.objects.create(user=self.alice,month=date(2026,8,1),status='complete',confirmed_at=timezone.now())
        MonthlyCoverage.objects.create(user=self.alice,month=date(2026,9,1),status='incomplete')
        result=financial_statistics(self.alice,date(2026,9,1),6)
        bymonth={r['month']:r for r in result['monthly_statistics']}
        self.assertEqual(result['category_statistics'],[])
        self.assertEqual(result['statistics_expense'],Decimal('0'))
        self.assertEqual(bymonth[date(2026,8,1)]['status'],'complete')
        self.assertEqual(bymonth[date(2026,7,1)]['status'],'unknown')
        self.assertTrue(all(r['income_height']=='0' and r['expense_height']=='0' for r in bymonth.values()))
        history=monthly_history(self.alice,date(2026,7,1),date(2026,9,1))
        self.assertEqual([m['forecast_expense'] for m in history],[None,Decimal('0'),None])
        page = self.client.get(reverse('finance:dashboard'), {'month': '2026-09'})
        self.assertContains(page, 'không khẳng định tháng đó không chi tiền')
        self.assertContains(page, 'vẫn là dữ liệu chưa biết cho dự báo')

    def test_current_future_and_vietnam_time(self):
        with patch('finance.statistics.current_month',return_value=date(2026,10,1)):
            rows=financial_statistics(self.alice,date(2026,11,1),6)['monthly_statistics']
        self.assertEqual(rows[-2]['period_note'],'Tháng chưa kết thúc')
        self.assertEqual(rows[-1]['period_note'],'Tháng tương lai')

    def test_coverage_and_transactions_scoped_to_account(self):
        MonthlyCoverage.objects.create(user=self.bob,month=date(2026,9,1),status='complete',confirmed_at=timezone.now())
        rows=financial_statistics(self.alice,date(2026,10,1),6)['monthly_statistics']
        self.assertEqual(rows[-2]['status'],'unknown')
        self.assertEqual(rows[-1]['expense'],Decimal('125000'))

    def test_large_decimal_totals_and_common_chart_scale(self):
        for _ in range(25):self.row(amount='999999999999999')
        self.row(self.salary,'999999999999999',kind='income')
        result=financial_statistics(self.alice,date(2026,10,1),6)
        self.assertEqual(result['statistics_expense'],Decimal('25000000000124975'))
        last=result['monthly_statistics'][-1]
        self.assertEqual(last['expense_height'],'100.00')
        self.assertEqual(last['income_height'],'4.00')
        self.assertEqual(last['balance'],last['income']-last['expense'])
        self.assertEqual(result['chart_axis_ticks'][0]['value'], last['expense'])
        self.assertEqual(result['chart_axis_unit'], 'triệu tỷ VND')

    def test_escaped_special_names_no_js_and_same_data_for_chart_table(self):
        self.food.name='<script>alert("x")</script> & Điện'
        self.food.save()
        response=self.client.get(reverse('finance:dashboard'),{'month':'2026-10','span':'12'})
        self.assertNotContains(response,'<script>alert(')
        self.assertContains(response,'&lt;script&gt;')
        self.assertEqual(response.content.decode().count('width:100.00%'),1)
        self.assertContains(response,'id="category-statistics"')
        self.assertContains(response,'id="monthly-statistics"')
        self.assertEqual(len(response.context['monthly_statistics']),12)
        self.assertEqual(response.context['expense'],response.context['statistics_expense'])
        self.assertContains(response,'Tháng chưa kết thúc')

    def test_empty_month_state_and_invalid_span(self):
        page=self.client.get(reverse('finance:dashboard'),{'month':'2025-01'})
        self.assertContains(page,'Chưa có cơ cấu hoặc tỷ trọng')
        self.assertNotContains(page,'id="category-statistics"')
        for span in ['0','7','9999999','bad','']:
            page=self.client.get(reverse('finance:dashboard'),{'month':'2026-10','span':span})
            self.assertContains(page,'Chỉ chọn 6 hoặc 12 tháng')
            self.assertNotIn('monthly_statistics',page.context)

    def test_read_only_and_login(self):
        from django.db import connection
        queries=[]
        def record(execute,sql,params,many,context):
            queries.append(sql)
            return execute(sql,params,many,context)
        with connection.execute_wrapper(record):
            result=financial_statistics(self.alice,date(2026,10,1),6)
        self.assertTrue(queries)
        self.assertTrue(all(sql.lstrip().upper().startswith('SELECT') for sql in queries))
        self.client.logout()
        self.assertEqual(self.client.get(reverse('finance:dashboard')).status_code,302)

    def test_minimum_calendar_year_no_underflow(self):
        result=financial_statistics(self.alice,date(1,1,1),12)
        self.assertEqual(result['statistics_actual_months'],1)
