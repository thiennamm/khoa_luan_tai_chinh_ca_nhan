"""Calendar QA uses synthetic data and isolated test databases only."""
from datetime import date, datetime, timezone as utc
from decimal import Decimal
from unittest.mock import patch

from django.apps import apps
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

from . import recurring
from .financial_calendar import month_data
from .models import Category, Transaction, SavingsGoal, SavingsEntry, MonthlyCoverage
from .recurring_forms import RecurringRuleForm, RecurringConfirmationForm
from .services import monthly_totals


class FinancialCalendarTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        U=get_user_model()
        cls.user=U.objects.create_user('calendar-qa-only')
        cls.other=U.objects.create_user('calendar-other-only')
        cls.food=Category.objects.create(user=cls.user,name='Ăn uống <QA>',kind='expense')
        cls.salary=Category.objects.create(user=cls.user,name='Lương QA',kind='income')
        cls.foreign=Category.objects.create(user=cls.other,name='Ăn uống <QA>',kind='expense')
        cls.source=Transaction.objects.create(user=cls.user,category=cls.food,kind='expense',amount=Decimal('125000'),
            date=date(2026,10,1),description='Riêng A')
        cls.secret=Transaction.objects.create(user=cls.other,category=cls.foreign,kind='expense',amount=Decimal('987654'),
            date=date(2026,10,1),description='RIENG_B_KHONG_HIEN_THI')

    def setUp(self):
        self.clock=patch('django.utils.timezone.now',return_value=datetime(2026,10,27,5,tzinfo=utc.utc))
        self.clock.start();self.addCleanup(self.clock.stop)
        self.client.force_login(self.user)
        self.url=reverse('finance:financial_calendar')

    def month(self,month='2026-10',**params):return self.client.get(self.url,{'month':month,**params})
    def day(self,day='2026-10-01',**params):return self.client.get(reverse('finance:financial_calendar_day',args=[day]),params)

    def row(self,amount='100',day=date(2026,10,10),kind='expense',**extra):
        return Transaction.objects.create(user=self.user,category=self.salary if kind=='income' else self.food,
            kind=kind,amount=Decimal(amount),date=day,**extra)

    def rule(self,**changes):
        form=RecurringRuleForm({'name':'Nhà QA','kind':'expense','amount':'1000000','category':self.food.pk,
            'due_day':31,'start_month':'2020-01','end_month':'',**changes},user=self.user)
        self.assertTrue(form.is_valid(),form.errors)
        return recurring.save_rule(form,self.user)

    def record(self,rule,day='2026-09-30'):
        form=RecurringConfirmationForm({'amount':'900000','date':day,'category':self.food.pk,'description':'Đã trả một lần'},
            user=self.user,expected_kind='expense')
        self.assertTrue(form.is_valid(),form.errors)
        return recurring.process(self.user,rule.pk,date(2026,10,1),'record',form)

    def test_auth_get_only_cache_and_navigation(self):
        for response in (self.month(),self.day()):
            self.assertIn('private',response['Cache-Control']);self.assertIn('no-store',response['Cache-Control'])
            self.assertContains(response,'Lịch thu–chi')
        self.assertEqual(self.client.post(self.url).status_code,405)
        self.assertEqual(self.client.post(reverse('finance:financial_calendar_day',args=['2026-10-01'])).status_code,405)
        self.client.logout()
        self.assertEqual(self.month().status_code,302);self.assertEqual(self.day().status_code,302)

    def test_invalid_month_and_day_never_fall_back(self):
        for month in ('','bad','2026-1','2026-00','2026-13','0000-01','2026-10-01'):
            response=self.month(month)
            self.assertContains(response,'Tháng không hợp lệ',status_code=400)
            self.assertNotIn('income',response.context);self.assertNotIn('weeks',response.context)
        for day in ('2026-2-01','2026-02-30','2026-00-01','bad','0000-01-01'):
            self.assertEqual(self.day(day).status_code,404)

    def test_default_month_today_uses_vietnam_across_utc_boundary(self):
        with patch('django.utils.timezone.now',return_value=datetime(2026,10,31,17,0,1,tzinfo=utc.utc)),timezone.override('UTC'):
            page=self.client.get(self.url)
        self.assertEqual(page.context['month'],date(2026,11,1))
        self.assertEqual(page.context['today'],date(2026,11,1))
        self.assertEqual([x['day'] for x in page.context['days'] if x['today']],[date(2026,11,1)])

    def test_monday_grid_month_edges_leap_and_year_navigation(self):
        data=self.month().context
        self.assertEqual(data['weeks'][0][0]['day'],date(2026,9,28))
        self.assertFalse(data['weeks'][0][0]['inside'])
        self.assertEqual([d['day'].day for d in data['days']],list(range(1,32)))
        for month,count in [('2024-02',29),('2025-02',28),('2026-04',30)]:
            page=self.month(month)
            self.assertEqual(len(page.context['days']),count)
            self.assertTrue(all(len(w)==7 for w in page.context['weeks']))
        january=self.month('2026-01').context
        self.assertEqual(january['previous_month'],date(2025,12,1))
        self.assertEqual(january['next_month'],date(2026,2,1))
        self.assertIsNone(self.month('0001-01').context['previous_month'])
        self.assertIsNone(self.month('9999-12').context['next_month'])

    def test_decimal_daily_monthly_totals_match_existing_list_and_month_service(self):
        for _ in range(25):self.row(amount='999999999999999')
        self.row(amount='50000',kind='income');self.row(amount='20000')
        self.row(amount='777',day=date(2026,9,30));self.row(amount='888',day=date(2026,11,1))
        page=self.month();daily=next(d for d in page.context['days'] if d['day']==date(2026,10,10))
        self.assertEqual(daily['expense'],Decimal('24999999999999975')+Decimal('20000'))
        expected=monthly_totals(self.user,date(2026,10,1),date(2026,11,1))
        listing=self.client.get(reverse('finance:transaction_list'),{'month':'2026-10'})
        for key in ('income','expense','balance'):
            self.assertEqual(page.context[key],expected[key]);self.assertEqual(page.context[key],listing.context[key])
            self.assertIsInstance(page.context[key],Decimal)
        self.assertEqual(sum(d['expense'] for d in page.context['days']),page.context['expense'])
        self.assertEqual(page.context['actual_count'],28)

    def test_future_stored_transaction_counted_and_clearly_marked(self):
        row=self.row(amount='45000',day=date(2026,10,31),description='Khoản tương lai QA')
        month=self.month();self.assertEqual(month.context['expense'],Decimal('170000'))
        self.assertContains(month,'Có giao dịch ngày tương lai đã lưu')
        self.assertContains(self.day('2026-10-31'),'Ngày tương lai')
        self.assertContains(self.client.get(reverse('finance:transaction_detail',args=[row.pk])),'Giao dịch ngày tương lai')
        row.refresh_from_db();self.assertEqual(row.date,date(2026,10,31))

    def test_empty_month_day_and_unknown_coverage_do_not_claim_no_real_spending(self):
        month=self.month('2026-09')
        self.assertEqual(month.context['expense'],Decimal(0))
        self.assertContains(month,'Không có giao dịch được ghi nhận')
        self.assertContains(month,'không khẳng định không phát sinh thu/chi')
        self.assertEqual(month.context['coverage'],'Chưa xác nhận')
        self.assertContains(self.day('2026-09-15'),'Không có giao dịch được ghi nhận')
        self.assertFalse(MonthlyCoverage.objects.exists())

    def test_outside_plan_window_explains_limit_and_preserves_actuals(self):
        self.row(amount='500',day=date(2015,1,1))
        with patch('finance.recurring.monthly_items') as plans:
            page=self.month('2015-01');detail=self.day('2015-01-01')
        plans.assert_not_called()
        self.assertFalse(page.context['plans_available']);self.assertEqual(page.context['expense'],Decimal(500))
        self.assertContains(page,'Ngoài phạm vi không có nghĩa là không có khoản đến hạn')
        self.assertContains(detail,'ngoài phạm vi định kỳ')

    def test_recurring_due_31_uses_last_day_in_leap_and_nonleap_february(self):
        for year,expected in [(2024,29),(2025,28)]:
            with patch('django.utils.timezone.now',return_value=datetime(year,2,15,5,tzinfo=utc.utc)):
                rule=self.rule(name=f'QA {year}',end_month=f'{year}-02')
                page=self.month(f'{year}-02')
                cell=next(c for c in page.context['days'] if c['day'].day==expected)
                self.assertEqual(cell['plan_count'],1)
                self.assertEqual(cell['expense'],Decimal(0))
                self.assertEqual(page.context['expense'],Decimal(0))
                self.assertEqual(cell['items'][0]['rule_id'],rule.pk)

    def test_pause_resume_and_preview_next_month_no_backfill(self):
        rule=self.rule();recurring.set_active(self.user,rule.pk,False)
        self.assertEqual(self.month().context['plan_count'],0)
        recurring.set_active(self.user,rule.pk,True)
        self.assertEqual(self.month().context['plan_count'],0)
        self.assertEqual(self.month('2026-11').context['plan_count'],1)
        detail=self.day('2026-11-30')
        self.assertContains(detail,'Kỳ tháng sau chỉ để xem trước')
        record_url=reverse('finance:recurring_occurrence',args=[rule.pk,2026,11,'record'])
        self.assertNotContains(detail,record_url)

    def test_recorded_skipped_deleted_periods_not_shown_as_unpaid(self):
        one,two,three=(self.rule(name=name) for name in ['Đã ghi','Bỏ qua','Đã xóa'])
        self.record(one,day='2026-10-05')
        recurring.process(self.user,two.pk,date(2026,10,1),'skip')
        deleted=self.record(three,day='2026-10-06');deleted.transaction.delete()
        page=self.month()
        self.assertEqual((page.context['plan_count'],page.context['recorded_periods'],page.context['skipped_periods'],page.context['deleted_periods']),(0,1,1,1))
        self.assertEqual(page.context['expense'],Decimal('1025000'))
        self.assertEqual(self.day('2026-10-31').context['plans_page'].paginator.count,0)

    def test_actual_date_other_month_only_counted_once_and_explained(self):
        rule=self.rule();occ=self.record(rule)
        october=self.month();september=self.month('2026-09')
        self.assertEqual(october.context['expense'],Decimal('125000'))
        self.assertEqual(october.context['plan_count'],0)
        self.assertEqual(september.context['expense'],Decimal('900000'))
        self.assertContains(self.day('2026-09-30'),'chỉ tính một lần theo ngày thực tế')
        detail=self.client.get(reverse('finance:transaction_detail',args=[occ.transaction_id]))
        self.assertContains(detail,'đến hạn 31/10/2026')
        self.assertContains(detail,'đây là cùng một khoản')

    def test_plan_link_opens_existing_confirmation_without_recording(self):
        rule=self.rule()
        url=reverse('finance:recurring_occurrence',args=[rule.pk,2026,10,'record'])
        self.assertContains(self.day('2026-10-31'),url)
        count=Transaction.objects.count()
        self.assertEqual(self.client.get(url).status_code,200)
        self.assertEqual(Transaction.objects.count(),count)
        self.assertFalse(rule.occurrences.exists())

    def test_rule_edit_uses_effective_snapshot_not_latest_name_amount(self):
        rule=self.rule()
        form=RecurringRuleForm({'name':'Tên mới tháng sau','kind':'expense','amount':'2000000',
            'category':self.food.pk,'due_day':15,'start_month':'2020-01','end_month':''},instance=rule,user=self.user)
        self.assertTrue(form.is_valid());recurring.save_rule(form,self.user)
        old=self.day('2026-10-31').context['plans_page'][0]
        new=self.day('2026-11-15').context['plans_page'][0]
        self.assertEqual((old['description'],old['amount']),('Nhà QA',Decimal('1000000')))
        self.assertEqual((new['description'],new['amount']),('Tên mới tháng sau',Decimal('2000000')))

    def test_preview_bounded_and_daily_pagination_full_totals_and_escape(self):
        for i in range(45):self.row(amount=str(i+1),description=f'QA {i}')
        dangerous=self.row(description='<script>alert(1)</script>\n'+'dài'*120)
        page=self.month();cell=next(d for d in page.context['days'] if d['day']==date(2026,10,10))
        self.assertEqual(len(cell['items']),2);self.assertTrue(cell['more']);self.assertEqual(cell['actual_count'],46)
        seen=[]
        for p,count in [(1,20),(2,20),(3,6)]:
            detail=self.day('2026-10-10',page=p)
            self.assertEqual(len(detail.context['page_obj']),count)
            self.assertEqual(detail.context['expense'],Decimal(sum(range(1,46))+100))
            seen += [item['id'] for item in detail.context['page_obj']]
        self.assertEqual(len(set(seen)),46)
        self.assertEqual(seen,sorted(seen,reverse=True))
        self.assertContains(self.day('2026-10-10'),'&lt;script&gt;alert(1)&lt;/script&gt;')
        self.assertNotContains(self.day('2026-10-10'),'<script>alert(1)')
        self.assertIn(dangerous.pk,seen)

    def test_planned_pagination_full_and_estimates_not_in_totals(self):
        for i in range(25):self.rule(name=f'QA dự kiến {i}',due_day=10)
        page=self.month();cell=next(d for d in page.context['days'] if d['day']==date(2026,10,10))
        self.assertEqual(len(cell['items']),2);self.assertEqual(cell['plan_count'],25)
        self.assertEqual(cell['expense'],Decimal(0));self.assertEqual(page.context['expense'],Decimal('125000'))
        first=self.day('2026-10-10');second=self.day('2026-10-10',plans_page=2)
        self.assertEqual(len(first.context['plans_page']),20);self.assertEqual(len(second.context['plans_page']),5)
        self.assertContains(first,'plans_page=2&amp;page=1')

    def test_scope_ignores_forged_user_and_existing_details_enforce_owner(self):
        self.assertNotContains(self.month(user_id=self.other.pk),'RIENG_B_KHONG_HIEN_THI')
        self.assertNotContains(self.day(user_id=self.other.pk),'RIENG_B_KHONG_HIEN_THI')
        self.assertEqual(self.client.get(reverse('finance:transaction_detail',args=[self.secret.pk])).status_code,404)
        foreign_form=RecurringRuleForm({'name':'RIENG_RULE_B','kind':'expense','amount':'123456',
            'category':self.foreign.pk,'due_day':10,'start_month':'2026-10','end_month':''},user=self.other)
        self.assertTrue(foreign_form.is_valid());recurring.save_rule(foreign_form,self.other)
        self.assertNotContains(self.day('2026-10-10'),'RIENG_RULE_B')
        self.client.force_login(self.other)
        self.assertNotContains(self.month(user_id=self.user.pk),'Riêng A')

    def test_get_preserves_all_finance_rows_and_savings_not_actuals(self):
        self.rule()
        goal=SavingsGoal.objects.create(user=self.user,name='QA',amount=Decimal('9000000'),start_date=date(2020,1,1))
        SavingsEntry.objects.create(goal=goal,kind='contribution',amount=Decimal('8000000'),date=date(2026,10,1))
        models=list(apps.get_app_config('finance').get_models())
        before={m.__name__:list(m.objects.order_by('pk').values()) for m in models}
        with patch('finance.forecasting.compute_and_store') as forecast,patch('finance.views.suggest_label') as inference:
            self.assertEqual(self.month().context['expense'],Decimal('125000'))
            self.day();self.day('2026-10-31');self.month('2015-01')
            self.month(show_empty='1');self.day(show_empty='1')
        forecast.assert_not_called();inference.assert_not_called()
        self.assertEqual(before,{m.__name__:list(m.objects.order_by('pk').values()) for m in models})

    def test_query_count_does_not_grow_per_day_transaction_or_rule(self):
        self.rule()
        with CaptureQueriesContext(connection) as small:self.month()
        with CaptureQueriesContext(connection) as day_small:self.day('2026-10-10')
        for i in range(40):self.row(day=date(2026,10,i%28+1),description='QA dài '*50)
        for i in range(15):self.rule(name=f'QA nhiều {i}',due_day=10)
        with CaptureQueriesContext(connection) as large:self.month()
        with CaptureQueriesContext(connection) as day_large:self.day('2026-10-10')
        with CaptureQueriesContext(connection) as show_all:self.month(show_empty='1')
        self.assertEqual(len(small),len(large))
        self.assertEqual(len(show_all),len(large))
        # Empty vs nonempty actual day may add one paginated SELECT, never N+1.
        self.assertLessEqual(len(day_large),len(day_small)+1)
        self.assertLessEqual(len(large),8);self.assertLessEqual(len(day_large),9)

    def cell_html(self, cell, **extra):
        return render_to_string('finance/includes/calendar_cell.html',
            {'cell':cell,'plans_available':True,'show_empty':False,**extra})

    def test_compact_empty_day_keeps_date_link_without_repeated_zero_lines(self):
        cell=next(c for c in self.month().context['days'] if c['day']==date(2026,10,2))
        html=self.cell_html(cell)
        self.assertIn('Chưa có giao dịch',html)
        self.assertIn('/lich-thu-chi/ngay/2026-10-02/?show_empty=0',html)
        self.assertNotIn('0 VND',html)
        self.assertNotIn('0 giao dịch',html);self.assertNotIn('0 dự kiến',html)

    def test_kind_presence_controls_totals_even_when_presented_aggregate_is_zero(self):
        self.row(day=date(2026,10,5),kind='income')
        days=self.month().context['days']
        income=next(c for c in days if c['day']==date(2026,10,5))
        expense=next(c for c in days if c['day']==date(2026,10,1))
        self.assertTrue(income['has_income']);self.assertFalse(income['has_expense'])
        self.assertTrue(expense['has_expense']);self.assertFalse(expense['has_income'])
        # Presentation contract only: no zero/invalid Transaction is persisted.
        html=self.cell_html({**income,'income':Decimal(0)})
        self.assertIn('Thu đã ghi',html);self.assertIn('0 VND',html);self.assertNotIn('Chi đã ghi',html)
        expense_html=self.cell_html(expense)
        self.assertIn('Chi đã ghi',expense_html);self.assertNotIn('Thu đã ghi',expense_html)

    def test_mobile_default_includes_actual_and_planned_days_and_get_can_show_all(self):
        self.row(day=date(2026,10,5),kind='income')
        self.rule(due_day=10)
        default=self.month()
        self.assertEqual([c['day'].day for c in default.context['mobile_days']],[1,5,10])
        self.assertEqual(len(default.context['days']),31)
        self.assertEqual(len(self.month(show_empty='1').context['mobile_days']),31)
        self.assertEqual(len(self.month(show_empty='0').context['mobile_days']),3)
        planned=next(c for c in default.context['mobile_days'] if c['day'].day==10)
        html=self.cell_html(planned)
        self.assertIn('Dự kiến · Chi',html);self.assertIn('1 dự kiến',html)
        self.assertNotIn('Thu đã ghi',html);self.assertNotIn('Chi đã ghi',html)
        self.assertNotIn('0 giao dịch',html)

    def test_get_mode_keeps_selected_month_day_and_both_pagination_states(self):
        for _ in range(22):self.row()
        for i in range(25):self.rule(name=f'QA chế độ {i}',due_day=10)
        month=self.month(show_empty='1')
        self.assertContains(month,'?month=2026-09&amp;show_empty=1')
        self.assertContains(month,'/lich-thu-chi/ngay/2026-10-10/?show_empty=1')
        day=self.day('2026-10-10',show_empty='1')
        self.assertContains(day,'?page=2&amp;plans_page=1&amp;show_empty=1')
        second=self.day('2026-10-10',show_empty='1',page=2,plans_page=1)
        self.assertEqual(second.context['day'],date(2026,10,10))
        self.assertContains(second,'?plans_page=2&amp;page=2&amp;show_empty=1')
        self.assertContains(second,'/lich-thu-chi/?month=2026-10&amp;show_empty=1')

    def test_two_preview_items_and_more_count_represent_remaining_not_truncated_data(self):
        for i in range(4):self.row(description=f'QA phần xem trước {i}')
        self.rule(due_day=10)
        cell=next(c for c in self.month().context['days'] if c['day'].day==10)
        self.assertEqual(cell['item_count'],5);self.assertEqual(len(cell['items']),2)
        self.assertEqual(cell['more_count'],3)
        self.assertIn('Xem thêm 3 mục',self.cell_html(cell))
        self.assertIn('Đã ghi nhận · Chi',self.cell_html(cell))
        day=self.day('2026-10-10')
        self.assertEqual(day.context['page_obj'].paginator.count,4)
        self.assertEqual(day.context['plans_page'].paginator.count,1)

    def test_outside_recurring_window_and_empty_mobile_month_keep_scope_and_action(self):
        page=self.month('2015-01',show_empty='1')
        self.assertFalse(page.context['plans_available'])
        self.assertContains(page,'Ngoài phạm vi không có nghĩa là không có khoản đến hạn')
        self.assertContains(page,'Không có giao dịch được ghi nhận')
        self.assertContains(page,reverse('finance:transaction_create'))
        self.assertEqual(len(page.context['mobile_days']),31)
        self.assertEqual(self.month('2015-01').context['mobile_days'],[])
        html=self.cell_html(page.context['days'][0],plans_available=False)
        self.assertIn('Chưa có giao dịch',html);self.assertNotIn('0 dự kiến',html)
