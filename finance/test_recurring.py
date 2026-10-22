from datetime import date, datetime, timezone as dt_timezone
from decimal import Decimal
from threading import Barrier, Thread
from queue import Queue
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError, OperationalError, close_old_connections, transaction
from django.db.models.deletion import ProtectedError
from django.test import Client, TestCase, TransactionTestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from . import recurring
from .budgets import monthly_budgets
from .models import (Category, Transaction, MonthlyCoverage, ForecastDataVersion, Budget,
    RecurringRule, RecurringRevision, RecurringOccurrence, RecurringEvent, ClassificationFeedback)
from .recurring_forms import RecurringRuleForm, RecurringConfirmationForm


class RecurringCase(TestCase):
    def setUp(self):
        self.clock = patch('finance.recurring.today', return_value=date(2026, 10, 22))
        self.clock.start(); self.addCleanup(self.clock.stop)
        self.user = User.objects.create_user('recurring-qa')
        self.other = User.objects.create_user('other-recurring-qa')
        self.cat = Category.objects.create(user=self.user, name='Định kỳ <QA>', kind='expense')
        self.salary = Category.objects.create(user=self.user, name='Lương', kind='income')
        self.foreign = Category.objects.create(user=self.other, name='Riêng', kind='expense')
        self.client.force_login(self.user)

    def rule(self, **changes):
        form = RecurringRuleForm({'name': 'Tiền nhà', 'kind': 'expense', 'amount': '1000000',
            'category': self.cat.pk, 'due_day': 31, 'start_month': '2026-10', 'end_month': '', **changes}, user=self.user)
        self.assertTrue(form.is_valid(), form.errors)
        return recurring.save_rule(form, self.user)

    def url(self, rule, action, month=date(2026, 10, 1)):
        return reverse('finance:recurring_occurrence', args=[rule.pk, month.year, month.month, action])

    def confirm(self, **changes):
        form = RecurringConfirmationForm({'amount': '900000', 'date': '2026-09-30',
            'category': self.cat.pk, 'description': 'Thực trả QA', **changes}, user=self.user, expected_kind='expense')
        self.assertTrue(form.is_valid(), form.errors)
        return form


class RecurringTests(RecurringCase):
    def test_calendar_29_30_31_and_leap_year(self):
        rule = self.rule(start_month='2020-01')
        for year, month, day, expected in [(2024,2,29,29),(2025,2,29,28),(2024,2,30,29),
                (2025,2,31,28),(2026,4,31,30),(2026,1,31,31),(2026,4,29,29)]:
            with self.subTest(year=year, day=day):
                rev = rule.revisions.get()
                rev.effective_month = date(2020,1,1)
                rev.snapshot['due_day'] = day; rev.save()
                self.assertEqual(recurring.planned(rule, date(year,month,1))[1].day, expected)

    def test_create_does_not_backfill_and_start_end_inclusive(self):
        rule = self.rule(start_month='2020-01', end_month='2026-11')
        self.assertIsNone(recurring.planned(rule, date(2026,9,1)))
        self.assertIsNotNone(recurring.planned(rule, date(2026,10,1)))
        self.assertIsNotNone(recurring.planned(rule, date(2026,11,1)))
        self.assertIsNone(recurring.planned(rule, date(2026,12,1)))
        future = self.rule(start_month='2026-11', name='Bắt đầu sau')
        self.assertIsNone(recurring.planned(future,date(2026,10,1)))

    def test_pause_resume_does_not_backfill_paused_month(self):
        rule = self.rule()
        recurring.set_active(self.user, rule.pk, False)
        rule.refresh_from_db()
        self.assertIsNone(recurring.planned(rule,date(2026,10,1)))
        with self.assertRaises(recurring.RecurringConflict):
            recurring.process(self.user,rule.pk,date(2026,10,1),'record',self.confirm())
        recurring.set_active(self.user,rule.pk,True)
        rule.refresh_from_db()
        self.assertIsNone(recurring.planned(rule,date(2026,10,1)))
        self.assertIsNotNone(recurring.planned(rule,date(2026,11,1)))
        self.assertFalse(Transaction.objects.exists())

    def test_second_pause_cancels_scheduled_resume(self):
        rule = self.rule()
        for active in (False,True,False):
            recurring.set_active(self.user,rule.pk,active)
        rule.refresh_from_db()
        self.assertIsNone(recurring.planned(rule,date(2026,11,1)))

    def test_rule_edit_applies_next_month_snapshot_preserves_current_and_processed(self):
        rule = self.rule()
        occurrence = recurring.process(self.user,rule.pk,date(2026,10,1),'skip')
        frozen = occurrence.snapshot.copy()
        form = RecurringRuleForm({'name':'Tên mới','kind':'income','amount':'2000000','category':self.salary.pk,
            'due_day':'15','start_month':'2026-10','end_month':''},instance=rule,user=self.user)
        self.assertTrue(form.is_valid(),form.errors)
        recurring.save_rule(form,self.user)
        rule.refresh_from_db(); occurrence.refresh_from_db()
        self.assertEqual(occurrence.snapshot,frozen)
        self.assertEqual(recurring.planned(rule,date(2026,10,1))[0]['name'],'Tiền nhà')
        self.assertEqual(recurring.planned(rule,date(2026,11,1))[0]['kind'],'income')
        self.assertEqual(RecurringRevision.objects.filter(rule=rule).count(),2)

    def test_record_actual_values_cross_month_and_real_hooks(self):
        rule = self.rule()
        for month in (date(2026,9,1),date(2026,8,1)):
            MonthlyCoverage.objects.create(user=self.user,month=month,status='complete',confirmed_at=timezone.now())
        version = ForecastDataVersion.objects.get(user=self.user).version
        Budget.objects.create(user=self.user,month=date(2026,9,1),amount=Decimal('1000000'))
        self.assertEqual(monthly_budgets(self.user,date(2026,9,1))['recorded_expense'],0)
        occurrence = recurring.process(self.user,rule.pk,date(2026,10,1),'record',self.confirm())
        row = occurrence.transaction
        self.assertEqual((row.date,row.amount,row.description),(date(2026,9,30),Decimal('900000'),'Thực trả QA'))
        self.assertEqual(occurrence.month,date(2026,10,1))
        self.assertEqual(MonthlyCoverage.objects.get(user=self.user,month=date(2026,9,1)).status,'unknown')
        self.assertEqual(MonthlyCoverage.objects.get(user=self.user,month=date(2026,8,1)).status,'complete')
        self.assertGreater(ForecastDataVersion.objects.get(user=self.user).version,version)
        self.assertEqual(monthly_budgets(self.user,date(2026,9,1))['recorded_expense'],Decimal('900000'))
        self.assertFalse(ClassificationFeedback.objects.exists())

    def test_skip_no_actual_effect_and_repeated_post(self):
        rule = self.rule()
        recurring.process(self.user,rule.pk,date(2026,10,1),'skip')
        recurring.process(self.user,rule.pk,date(2026,10,1),'skip')
        self.assertEqual(RecurringOccurrence.objects.count(),1)
        self.assertEqual(RecurringEvent.objects.count(),1)
        self.assertFalse(Transaction.objects.exists())
        self.assertFalse(ForecastDataVersion.objects.exists())
        self.assertFalse(ClassificationFeedback.objects.exists())
        with self.assertRaises(recurring.RecurringConflict):
            recurring.process(self.user,rule.pk,date(2026,10,1),'record',self.confirm())

    def test_repeat_record_returns_original_no_duplicate(self):
        rule = self.rule()
        first = recurring.process(self.user,rule.pk,date(2026,10,1),'record',self.confirm())
        second = recurring.process(self.user,rule.pk,date(2026,10,1),'record',self.confirm(amount='1'))
        self.assertEqual(first.transaction_id,second.transaction_id)
        self.assertEqual(Transaction.objects.get().amount,Decimal('900000'))
        self.assertEqual(RecurringEvent.objects.count(),1)

    def test_database_unique_and_state_constraints(self):
        rule = self.rule()
        occurrence = recurring.process(self.user,rule.pk,date(2026,10,1),'skip')
        with self.assertRaises(IntegrityError),transaction.atomic():
            RecurringOccurrence.objects.create(user=self.user,rule=rule,month=occurrence.month,
                due_date=occurrence.due_date,snapshot=occurrence.snapshot,status='skipped')
        with self.assertRaises(IntegrityError),transaction.atomic():
            RecurringOccurrence.objects.filter(pk=occurrence.pk).update(status='recorded')

    def test_rollback_after_transaction_created_leaves_no_orphans(self):
        rule = self.rule()
        with patch('finance.recurring.RecurringEvent.objects.create',side_effect=IntegrityError('QA rollback')):
            with self.assertRaises(IntegrityError):
                recurring.process(self.user,rule.pk,date(2026,10,1),'record',self.confirm())
        self.assertFalse(Transaction.objects.exists())
        self.assertFalse(RecurringOccurrence.objects.exists())
        self.assertFalse(ForecastDataVersion.objects.exists())

    def test_transaction_edit_keeps_link_delete_requires_explicit_reopen(self):
        rule = self.rule()
        occurrence = recurring.process(self.user,rule.pk,date(2026,10,1),'record',self.confirm())
        tx = occurrence.transaction
        tx.amount = Decimal('15'); tx.date = date(2026,8,31); tx.save()
        occurrence.refresh_from_db()
        self.assertEqual(occurrence.status,'recorded')
        self.assertEqual(occurrence.snapshot['amount'],'1000000')
        Transaction.objects.filter(pk=tx.pk).delete()
        occurrence.refresh_from_db()
        self.assertEqual(occurrence.status,'deleted')
        self.assertIsNone(occurrence.transaction_id)
        with self.assertRaises(recurring.RecurringConflict):
            recurring.process(self.user,rule.pk,date(2026,10,1),'record',self.confirm())
        recurring.process(self.user,rule.pk,date(2026,10,1),'reopen')
        new = recurring.process(self.user,rule.pk,date(2026,10,1),'record',self.confirm())
        self.assertEqual(list(new.events.values_list('action',flat=True)),['record','delete','reopen','record'])
        self.assertEqual(Transaction.objects.count(),1)

    def test_skipped_reopen_preserves_snapshot_even_after_edit_and_pause(self):
        rule = self.rule()
        old = recurring.process(self.user,rule.pk,date(2026,10,1),'skip')
        data = old.snapshot.copy()
        recurring.set_active(self.user,rule.pk,False)
        recurring.process(self.user,rule.pk,date(2026,10,1),'reopen')
        result = recurring.process(self.user,rule.pk,date(2026,10,1),'record',self.confirm())
        self.assertEqual(result.snapshot,data)

    def test_invalid_rules_and_categories(self):
        for changes in ({'due_day':0},{'due_day':32},{'amount':'0'},{'amount':'1.5'},
                        {'amount':'1000000000000000'},{'category':self.foreign.pk},
                        {'category':self.salary.pk},{'start_month':'2026-13'},
                        {'end_month':'2026-09'},{'name':' '}):
            with self.subTest(changes=changes):
                response = self.client.post(reverse('finance:recurring_create'),{'name':'Test','kind':'expense',
                    'amount':'1','category':self.cat.pk,'due_day':'1','start_month':'2026-10','end_month':'',**changes})
                self.assertEqual(response.status_code,200)
                self.assertTrue(response.context['form'].errors)
        self.assertFalse(RecurringRule.objects.exists())

    def test_category_delete_and_kind_guards(self):
        self.rule()
        self.assertContains(self.client.get(reverse('finance:category_delete',args=[self.cat.pk])),'quy tắc định kỳ nên không thể xóa')
        with self.assertRaises(ProtectedError):
            self.cat.delete()
        self.cat.kind = 'income'
        with self.assertRaises(ValidationError):
            self.cat.save()

    def test_current_category_snapshot_not_trusted_at_confirmation(self):
        rule = self.rule()
        form = RecurringConfirmationForm({'category':self.foreign.pk,'amount':'1','date':'2026-10-22','description':''},
            user=self.user,expected_kind='expense')
        self.assertFalse(form.is_valid())
        self.assertEqual(RecurringOccurrence.objects.count(),0)
        # Hidden kind cannot change the rule's kind.
        form = self.confirm(kind='income')
        self.assertEqual(form.cleaned_data['kind'],'expense')

    def test_get_is_read_only_all_pages_and_future_preview(self):
        rule = self.rule()
        urls=[reverse('finance:recurring_list'),reverse('finance:recurring_edit',args=[rule.pk]),
            reverse('finance:recurring_history',args=[rule.pk]),reverse('finance:recurring_status',args=[rule.pk,'pause']),
            self.url(rule,'record'),self.url(rule,'skip'),reverse('finance:dashboard')]
        before=(RecurringRule.objects.count(),RecurringRevision.objects.count())
        for url in urls:
            self.assertEqual(self.client.get(url).status_code,200)
        self.assertEqual(before,(RecurringRule.objects.count(),RecurringRevision.objects.count()))
        self.assertFalse(RecurringOccurrence.objects.exists())
        self.assertFalse(RecurringEvent.objects.exists())
        self.assertFalse(Transaction.objects.exists())
        rows=recurring.monthly_items(self.user,date(2026,11,1))
        self.assertFalse(rows[0]['can_process'])
        self.assertEqual(self.client.get(self.url(rule,'record',date(2026,11,1))).status_code,404)

    def test_isolation_lists_actions_and_ignored_user_id(self):
        rule=self.rule()
        recurring.process(self.user,rule.pk,date(2026,10,1),'skip')
        self.client.force_login(self.other)
        page=self.client.get(reverse('finance:recurring_list'))
        self.assertNotContains(page,'Tiền nhà')
        for url in [reverse('finance:recurring_edit',args=[rule.pk]),
                    reverse('finance:recurring_history',args=[rule.pk]),self.url(rule,'record'),
                    reverse('finance:recurring_status',args=[rule.pk,'resume'])]:
            self.assertEqual(self.client.get(url).status_code,404)
            self.assertIn(self.client.post(url,{'confirm':True,'user_id':self.user.pk}).status_code,(404,405))
        self.client.logout()
        self.assertEqual(self.client.get(reverse('finance:recurring_list')).status_code,302)

    def test_csrf_and_confirmation_required(self):
        rule=self.rule()
        client=Client(enforce_csrf_checks=True); client.force_login(self.user)
        for url in [reverse('finance:recurring_create'),self.url(rule,'record'),self.url(rule,'skip'),
                    reverse('finance:recurring_status',args=[rule.pk,'pause'])]:
            self.assertEqual(client.post(url,{}).status_code,403)
        self.assertEqual(self.client.post(self.url(rule,'skip'),{}).status_code,200)
        self.assertFalse(RecurringOccurrence.objects.exists())

    def test_http_record_invalid_values_then_valid_duplicate_post(self):
        rule=self.rule()
        url=self.url(rule,'record')
        data={'amount':'30','date':'2026-09-30','category':self.cat.pk,'description':'Đã trả'}
        for changes in ({'amount':'-1'},{'amount':'1.2'},{'date':'2026-02-30'},
                        {'category':self.foreign.pk},{'category':self.salary.pk}):
            response=self.client.post(url,{**data,**changes})
            self.assertEqual(response.status_code,200)
            self.assertTrue(response.context['form'].errors)
        self.assertFalse(Transaction.objects.exists())
        first=self.client.post(url,{**data,'user_id':self.other.pk,'kind':'income'})
        second=self.client.post(url,data)
        self.assertEqual(first.status_code,302)
        self.assertEqual(first.url,second.url)
        row=Transaction.objects.get()
        self.assertEqual((row.user_id,row.kind),(self.user.pk,'expense'))
        self.assertContains(self.client.get(first.url),'kỳ định kỳ')
        self.assertContains(self.client.get(reverse('finance:transaction_delete',args=[row.pk])),'không tự tạo lại')

    def test_plans_edits_pause_skip_do_not_change_coverage_budget_or_forecast_version(self):
        coverage=MonthlyCoverage.objects.create(user=self.user,month=date(2026,9,1),status='complete',confirmed_at=timezone.now())
        version=ForecastDataVersion.objects.get(user=self.user).version
        Budget.objects.create(user=self.user,month=date(2026,10,1),amount=Decimal('1000'))
        rule=self.rule()
        recurring.set_active(self.user,rule.pk,False)
        recurring.set_active(self.user,rule.pk,True)
        # Another active rule can be skipped without affecting observed data.
        another=self.rule(name='Khoản khác')
        recurring.process(self.user,another.pk,date(2026,10,1),'skip')
        coverage.refresh_from_db()
        self.assertEqual(coverage.status,'complete')
        self.assertEqual(ForecastDataVersion.objects.get(user=self.user).version,version)
        self.assertEqual(monthly_budgets(self.user,date(2026,10,1))['recorded_expense'],Decimal(0))
        self.assertFalse(Transaction.objects.exists())
        self.assertFalse(ClassificationFeedback.objects.exists())

    def test_income_rule_and_old_category_unavailable_requires_explicit_choice(self):
        rule=self.rule(kind='income',category=self.salary.pk)
        form=RecurringConfirmationForm({'amount':'5','date':'2026-10-22','category':self.salary.pk,'description':''},
            user=self.user,expected_kind='income')
        self.assertTrue(form.is_valid(),form.errors)
        recurring.process(self.user,rule.pk,date(2026,10,1),'record',form)
        self.assertEqual(Transaction.objects.get().kind,'income')
        # A historical revision keeps its category name, not an unchecked FK to use.
        expense=self.rule(name='Danh mục cũ')
        other=Category.objects.create(user=self.user,name='Mới',kind='expense')
        expense.category=other;expense.save()
        self.cat.delete()
        page=self.client.get(self.url(expense,'record'))
        self.assertEqual(page.status_code,200)
        self.assertIsNone(page.context['form'].initial['category'])

    def test_actual_transaction_edit_resets_both_actual_months(self):
        rule=self.rule()
        period=recurring.process(self.user,rule.pk,date(2026,10,1),'record',self.confirm())
        for month in (date(2026,9,1),date(2026,8,1)):
            MonthlyCoverage.objects.create(user=self.user,month=month,status='complete',confirmed_at=timezone.now())
        period.transaction.date=date(2026,8,31)
        period.transaction.save()
        self.assertEqual(set(MonthlyCoverage.objects.filter(user=self.user).values_list('status',flat=True)),{'unknown'})
        period.refresh_from_db()
        self.assertEqual(period.status,'recorded')

    def test_window_filters_pagination_and_escaped_names(self):
        for i in range(22):
            self.rule(name=f'Khoản <QA> {i}')
        url=reverse('finance:recurring_list')
        page=self.client.get(url)
        self.assertEqual(len(page.context['page_obj']),20)
        self.assertEqual(len(self.client.get(url,{'page':2}).context['page_obj']),2)
        self.assertContains(page,'Khoản &lt;QA&gt;')
        self.assertFalse(self.client.get(url,{'state':'due'}).context['page_obj'])
        for data in ({'month':'2020-01'},{'month':'2026-12'},{'month':'bad'},{'state':'private'}):
            self.assertTrue(self.client.get(url,data).context['month_form'].errors)

    def test_dashboard_seven_days_cross_year(self):
        with patch('finance.recurring.today',return_value=date(2026,12,28)):
            rule=self.rule(start_month='2026-12',due_day=2)
            rows=recurring.dashboard_items(self.user)['recurring_due']
            self.assertEqual({r['month'] for r in rows},{date(2026,12,1),date(2027,1,1)})
            self.assertEqual(rows[1]['due_date'],date(2027,1,2))

    def test_vietnam_timezone_at_utc_month_boundary(self):
        self.clock.stop()
        with override_settings(TIME_ZONE='UTC'), patch('django.utils.timezone.now',return_value=datetime(2026,12,31,18,0,tzinfo=dt_timezone.utc)):
            self.assertEqual(recurring.today(),date(2027,1,1))


class RecurringStatusAndActualDateTests(RecurringCase):
    def test_rule_status_inclusive_start_end_and_processed_period(self):
        rule = self.rule(start_month='2026-10', end_month='2026-12')
        recurring.process(self.user, rule.pk, date(2026,10,1), 'record', self.confirm())
        for day, label in [(date(2026,10,22), 'Đang hoạt động'),
                (date(2026,12,31), 'Đang hoạt động'), (date(2027,1,1), 'Đã kết thúc')]:
            with self.subTest(day=day), patch('finance.recurring.today', return_value=day):
                self.assertEqual(recurring.rule_status(rule)['label'], label)
        self.assertContains(self.client.get(reverse('finance:recurring_list')), 'Đang hoạt động')
        self.assertEqual(RecurringOccurrence.objects.get().status, 'recorded')

    def test_future_start_pause_and_ended_precedence(self):
        future = self.rule(start_month='2026-11', end_month='2026-12')
        self.assertEqual(recurring.rule_status(future)['label'], 'Chưa đến tháng bắt đầu')
        recurring.set_active(self.user, future.pk, False)
        future.refresh_from_db()
        self.assertEqual(recurring.rule_status(future)['label'], 'Đã tạm dừng')
        with patch('finance.recurring.today', return_value=date(2027,1,1)):
            self.assertEqual(recurring.rule_status(future)['label'], 'Đã kết thúc')
        with patch('finance.recurring.today', return_value=date(2026,9,30)):
            self.assertEqual(recurring.rule_status(future)['label'], 'Chưa đến tháng bắt đầu')

    def test_resume_waits_for_effective_month_and_filters_do_not_change_status(self):
        rule = self.rule()
        recurring.set_active(self.user, rule.pk, False)
        recurring.set_active(self.user, rule.pk, True)
        rule.refresh_from_db()
        status = recurring.rule_status(rule)
        self.assertEqual(status['label'], 'Đã tạm dừng')
        self.assertIn('kích hoạt lại từ 11/2026', status['note'])
        page = self.client.get(reverse('finance:recurring_list'), {'month':'2026-11'})
        self.assertEqual(list(page.context['rules_page'])[0].display_status, status)
        with patch('finance.recurring.today', return_value=date(2026,11,1)):
            self.assertEqual(recurring.rule_status(rule), {'label':'Đang hoạt động', 'note':''})

    def test_scheduled_edit_does_not_change_current_effective_status(self):
        rule = self.rule()
        form = RecurringRuleForm({'name':'Thay đổi', 'kind':'expense', 'amount':'100',
            'category':self.cat.pk, 'due_day':'20', 'start_month':'2026-12', 'end_month':''},
            instance=rule, user=self.user)
        self.assertTrue(form.is_valid(), form.errors)
        recurring.save_rule(form, self.user)
        rule.refresh_from_db()
        self.assertEqual(recurring.rule_status(rule)['label'], 'Đang hoạt động')
        self.assertIn('11/2026', recurring.rule_status(rule)['note'])
        with patch('finance.recurring.today', return_value=date(2026,11,1)):
            self.assertEqual(recurring.rule_status(rule)['label'], 'Chưa đến tháng bắt đầu')

    def test_form_defaults_today_and_keeps_due_date_separate(self):
        rule = self.rule(due_day=31)
        page = self.client.get(self.url(rule, 'record'))
        self.assertEqual(page.context['form'].initial['date'], date(2026,10,22))
        self.assertEqual(page.context['form'].fields['date'].label, 'Ngày giao dịch thực tế')
        self.assertEqual(page.context['form'].fields['date'].widget.attrs['max'], '2026-10-22')
        self.assertContains(page, 'Ngày đến hạn: 31/10/2026')
        self.assertContains(page, 'đã thực sự phát sinh')
        self.assertFalse(Transaction.objects.exists())

    def test_future_date_rejected_preserves_input_without_side_effects(self):
        rule = self.rule()
        data = {'date':'2026-10-31', 'amount':'777', 'category':self.cat.pk, 'description':'Giữ nguyên QA'}
        page = self.client.post(self.url(rule, 'record'), data)
        self.assertEqual(page.status_code, 200)
        self.assertIn('date', page.context['form'].errors)
        for field in ('date', 'amount', 'description'):
            self.assertEqual(page.context['form'][field].value(), data[field])
        self.assertEqual(int(page.context['form']['category'].value()), self.cat.pk)
        self.assertFalse(Transaction.objects.exists())
        self.assertFalse(RecurringOccurrence.objects.exists())
        self.assertFalse(RecurringEvent.objects.exists())
        self.assertFalse(ForecastDataVersion.objects.exists())

    def test_future_date_policy_is_specific_to_recurring_confirmation(self):
        from .forms import TransactionForm
        data = {'date':'2026-10-31', 'amount':'100', 'category':self.cat.pk,
            'description':'QA', 'kind':'expense'}
        normal = TransactionForm(data, user=self.user)
        self.assertTrue(normal.is_valid(), normal.errors)
        confirmation = RecurringConfirmationForm(data, user=self.user, expected_kind='expense')
        self.assertFalse(confirmation.is_valid())
        self.assertIn('date', confirmation.errors)

    def test_actual_past_month_and_today_accepted_due_month_unchanged(self):
        rule = self.rule()
        response = self.client.post(self.url(rule, 'record'), {'date':'2026-09-30',
            'amount':'777', 'category':self.cat.pk, 'description':'Thực tế tháng trước'})
        self.assertEqual(response.status_code, 302)
        occurrence = RecurringOccurrence.objects.get()
        self.assertEqual(occurrence.month, date(2026,10,1))
        self.assertEqual(occurrence.due_date, date(2026,10,31))
        self.assertEqual(occurrence.transaction.date, date(2026,9,30))
        self.assertEqual(monthly_budgets(self.user,date(2026,9,1))['recorded_expense'], Decimal('777'))
        self.assertEqual(monthly_budgets(self.user,date(2026,10,1))['recorded_expense'], Decimal(0))
        self.confirm(date='2026-10-22')

    def test_vietnam_midnight_default_and_validation_independent_of_runtime_timezone(self):
        rule = self.rule()
        self.clock.stop()
        with override_settings(TIME_ZONE='UTC'):
            for instant, expected in [(datetime(2026,10,21,16,59,tzinfo=dt_timezone.utc), date(2026,10,21)),
                    (datetime(2026,10,21,17,0,tzinfo=dt_timezone.utc), date(2026,10,22))]:
                with self.subTest(instant=instant), patch('django.utils.timezone.now', return_value=instant):
                    page = self.client.get(self.url(rule, 'record'))
                    self.assertEqual(page.context['form'].initial['date'], expected)
                    standalone = RecurringConfirmationForm(user=self.user, expected_kind='expense')
                    self.assertEqual(standalone.initial['date'], expected)
                    form = RecurringConfirmationForm({'date':'2026-10-22','amount':'1',
                        'category':self.cat.pk, 'description':''}, user=self.user, expected_kind='expense')
                    self.assertEqual(form.is_valid(), expected == date(2026,10,22))

    def test_vietnam_year_boundary_rule_status(self):
        rule = self.rule(end_month='2026-12')
        self.clock.stop()
        with override_settings(TIME_ZONE='UTC'), patch('django.utils.timezone.now',
                return_value=datetime(2026,12,31,17,0,tzinfo=dt_timezone.utc)):
            self.assertEqual(recurring.rule_status(rule)['label'], 'Đã kết thúc')


class ConcurrentRecurringTests(TransactionTestCase):
    def test_two_concurrent_confirmations_never_duplicate(self):
        user=User.objects.create_user('parallel-qa')
        category=Category.objects.create(user=user,name='QA',kind='expense')
        form=RecurringRuleForm({'name':'Đồng thời','kind':'expense','amount':'100','category':category.pk,
            'due_day':1,'start_month':'2026-10','end_month':''},user=user)
        self.assertTrue(form.is_valid(),form.errors)
        barrier=Barrier(2);results=Queue()
        with patch('finance.recurring.today',return_value=date(2026,10,22)):
            rule=recurring.save_rule(form,user)
            def worker():
                close_old_connections()
                try:
                    own=User.objects.get(pk=user.pk)
                    confirmation=RecurringConfirmationForm({'amount':'100','date':'2026-10-22','category':category.pk,'description':'QA'},
                        user=own,expected_kind='expense')
                    assert confirmation.is_valid()
                    barrier.wait(timeout=10)
                    result=recurring.process(own,rule.pk,date(2026,10,1),'record',confirmation)
                    results.put(('ok',result.transaction_id))
                except OperationalError as exc:
                    results.put(('locked',str(exc)))
                except Exception as exc:
                    results.put(('error',type(exc).__name__))
                finally:
                    close_old_connections()
            threads=[Thread(target=worker) for _ in range(2)]
            for thread in threads: thread.start()
            for thread in threads: thread.join(timeout=20)
        self.assertTrue(all(not thread.is_alive() for thread in threads))
        outputs=[results.get_nowait() for _ in range(2)]
        self.assertIn('ok',[state for state,_ in outputs],outputs)
        self.assertNotIn('error',[state for state,_ in outputs],outputs)
        for state,message in outputs:
            if state=='locked': self.assertIn('locked',message.lower())
        self.assertEqual(Transaction.objects.count(),1)
        self.assertEqual(RecurringOccurrence.objects.count(),1)
        self.assertEqual(RecurringEvent.objects.count(),1)
