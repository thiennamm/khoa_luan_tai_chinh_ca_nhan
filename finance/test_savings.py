from datetime import date, datetime, timedelta, timezone as dt_timezone
from decimal import Decimal
from queue import Queue
from threading import Barrier, Thread
from unittest.mock import patch
import time

from django.apps import apps
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import transaction, IntegrityError, OperationalError, close_old_connections
from django.test import TestCase, TransactionTestCase, Client, override_settings
from django.urls import reverse
from . import savings
from .models import (SavingsGoal, SavingsEntry, SavingsOperation, Budget, MonthlyCoverage,
    ForecastResult, ClassificationSuggestion, ClassificationFeedback)
from .savings_forms import SavingsGoalForm, SavingsEntryForm
from .tests import FinanceCase

NOW = datetime(2026,10,25,4,tzinfo=dt_timezone.utc)


class SavingsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user('savings-qa')
        cls.bob = User.objects.create_user('savings-other-qa')

    def setUp(self):
        self.clock = patch('django.utils.timezone.now',return_value=NOW)
        self.clock.start()
        self.addCleanup(self.clock.stop)
        self.client.force_login(self.user)

    def goal_data(self, **changes):
        data = {'name':'Quỹ học tập','amount':Decimal('1000000'), 'start_date':date(2026,9,1),
            'due_date':date(2026,10,20),'note':'Dữ liệu kiểm thử'}
        return {**data, **changes}

    def goal(self, **changes):
        return savings.execute(self.user,savings.issue(self.user,'goal_create'),'goal_create',data=self.goal_data(**changes))[0]

    def op(self, goal, action, data=None, entry=None, token=None):
        goal.refresh_from_db()
        result = savings.execute(self.user,token or savings.issue(self.user,action,goal,entry),action,
            goal.pk,entry.pk if entry else None,data)
        goal.refresh_from_db()
        return result

    def add(self, goal, amount='100000', kind='contribution', day=date(2026,10,1)):
        self.op(goal,'entry_create',{'kind':kind,'amount':Decimal(amount),'date':day,'note':''})
        return goal.entries.latest('pk')

    def url(self, name, goal=None, *args):
        return reverse('finance:savings_'+name,args=([goal.pk] if goal else [])+list(args))

    def form_post(self, url, data):
        page = self.client.get(url)
        return self.client.post(url,{'operation_token':page.context['form']['operation_token'].value(),**data})

    def test_goal_create_update_and_invalid_deadline(self):
        url = self.url('create')
        data = {'name':'Học tập','amount':'1.000.000','start_date':'2026-09-01','due_date':'2026-10-20','note':''}
        response = self.form_post(url,data)
        self.assertEqual(response.status_code,302)
        goal = SavingsGoal.objects.get()
        self.assertEqual((goal.user,goal.amount),(self.user,Decimal('1000000')))
        response = self.form_post(self.url('edit',goal),{**data,'name':'Tên mới','amount':'50000'})
        self.assertEqual(response.status_code,302)
        goal.refresh_from_db()
        self.assertEqual(goal.name,'Tên mới')
        response = self.form_post(url,{**data,'due_date':'2026-08-31'})
        self.assertIn('due_date',response.context['form'].errors)
        self.assertEqual(SavingsGoal.objects.count(),1)

    def test_goal_money_name_and_date_validation(self):
        for amount in ['0','-1','1.5','50,000','50.00','1000000000000000']:
            form = SavingsGoalForm({**self.goal_data(),'amount':amount,'operation_token':'x'},user=self.user)
            self.assertFalse(form.is_valid(),amount)
        form = SavingsGoalForm({**self.goal_data(),'name':'  ','operation_token':'x'},user=self.user)
        self.assertFalse(form.is_valid())

    def test_reached_over_goal_and_changed_target_recomputes_state(self):
        goal = self.goal(amount=Decimal('100000'))
        self.add(goal)
        self.assertEqual(savings.summary(goal)['state'],'reached')
        self.add(goal,'50000')
        item = savings.summary(goal)
        self.assertEqual((item['accumulated'],item['percent'],item['width']),
            (Decimal('150000'),Decimal('150.00'),'100.00'))
        self.op(goal,'goal_edit',self.goal_data(amount=Decimal('200000')))
        self.assertEqual(savings.summary(goal)['state'],'active')
        self.assertEqual(goal.entries.count(),2)

    def test_overdue_is_warning_and_still_allows_contribution(self):
        goal = self.goal()
        self.assertTrue(savings.summary(goal)['overdue'])
        self.add(goal)
        self.assertContains(self.client.get(self.url('detail',goal)),'Bạn vẫn có thể tiếp tục đóng góp')

    def test_archive_reopen_preserves_history_blocks_all_entry_writes(self):
        goal = self.goal()
        entry = self.add(goal)
        self.op(goal,'archive')
        before = list(goal.entries.values())
        self.assertEqual(savings.summary(goal)['state'],'archived')
        for action in ['entry_create','entry_edit','entry_delete']:
            with self.subTest(action=action),self.assertRaises(savings.SavingsConflict):
                self.op(goal,action,{'kind':'contribution','amount':Decimal(1),'date':date(2026,10,1),'note':''},
                    entry=entry if action!='entry_create' else None)
        self.assertEqual(before,list(goal.entries.values()))
        self.op(goal,'reopen')
        self.add(goal,'50000')
        self.assertEqual(savings.summary(goal)['accumulated'],Decimal('150000'))

    def test_contribution_withdrawal_and_no_overdraw(self):
        goal = self.goal()
        self.add(goal,'100000')
        self.add(goal,'60000','withdrawal')
        self.assertEqual(savings.summary(goal)['accumulated'],Decimal('40000'))
        count = SavingsOperation.objects.count()
        with self.assertRaises(ValidationError):self.add(goal,'40001','withdrawal')
        self.assertEqual((goal.entries.count(),SavingsOperation.objects.count()),(2,count))
        self.add(goal,'40000','withdrawal')
        self.assertEqual(savings.summary(goal)['accumulated'],Decimal(0))

    def test_dates_future_before_start_invalid_date_and_kind(self):
        goal = self.goal()
        for changes in [{'date':'2026-10-26'},{'date':'2026-08-31'},{'date':'2026-02-30'},
                        {'kind':'income'},{'amount':'0'},{'amount':'-1'},{'amount':'50,000'}]:
            data = {'kind':'contribution','amount':'50000','date':'2026-10-25','note':'','operation_token':'x',**changes}
            form = SavingsEntryForm(data,goal=goal)
            self.assertFalse(form.is_valid(),changes)
        for day in [date(2026,8,31),date(2026,10,26)]:
            with self.assertRaises(ValidationError):self.add(goal,day=day)
        self.assertFalse(goal.entries.exists())

    def test_vietnam_day_boundary_independent_of_active_timezone(self):
        goal = self.goal()
        self.clock.stop()
        with override_settings(TIME_ZONE='UTC'):
            for hour, expected in [(16,date(2026,10,24)),(17,date(2026,10,25))]:
                with patch('django.utils.timezone.now',return_value=datetime(2026,10,24,hour,tzinfo=dt_timezone.utc)):
                    self.assertEqual(savings.today(),expected)
                    form = SavingsEntryForm({'kind':'contribution','amount':'1','date':'2026-10-25',
                        'note':'','operation_token':'x'},goal=goal)
                    self.assertEqual(form.is_valid(),expected==date(2026,10,25))

    def test_edit_delete_validate_entire_history_not_just_final_total(self):
        goal = self.goal()
        deposit = self.add(goal,'100000',day=date(2026,10,1))
        self.add(goal,'90000','withdrawal',date(2026,10,2))
        self.add(goal,'100000',day=date(2026,10,3))
        before = list(goal.entries.values())
        for data in [{'kind':'contribution','amount':Decimal('80000'),'date':deposit.date,'note':''},
                     {'kind':'contribution','amount':deposit.amount,'date':date(2026,10,4),'note':''}]:
            with self.assertRaises(ValidationError):self.op(goal,'entry_edit',data,deposit)
        with self.assertRaises(ValidationError):self.op(goal,'entry_delete',entry=deposit)
        self.assertEqual(before,list(goal.entries.values()))

    def test_edit_start_date_rechecks_existing_records(self):
        goal = self.goal()
        self.add(goal,day=date(2026,9,10))
        with self.assertRaises(ValidationError):
            self.op(goal,'goal_edit',self.goal_data(start_date=date(2026,9,11)))
        goal.refresh_from_db()
        self.assertEqual(goal.start_date,date(2026,9,1))

    def test_same_day_order_is_id_order_and_identical_legitimate_entries_allowed(self):
        goal = self.goal()
        self.add(goal,'50')
        self.add(goal,'50')
        self.add(goal,'100','withdrawal')
        self.assertEqual(goal.entries.count(),3)
        with self.assertRaises(ValidationError):self.add(goal,'1','withdrawal')
        self.assertEqual(savings.validate_history(goal,list(goal.entries.all())),Decimal(0))

    def test_valid_edit_and_delete_require_explicit_confirmation(self):
        goal = self.goal()
        entry = self.add(goal)
        url = self.url('entry_edit',goal,entry.pk)
        data = {'kind':'contribution','amount':'75000','date':'2026-10-02','note':'Đã sửa'}
        response = self.form_post(url,data)
        self.assertIn('confirm',response.context['form'].errors)
        response = self.form_post(url,{**data,'confirm':'on'})
        self.assertEqual(response.status_code,302)
        entry.refresh_from_db()
        self.assertEqual((entry.amount,entry.date),(Decimal('75000'),date(2026,10,2)))
        delete = self.url('entry_delete',goal,entry.pk)
        page = self.client.get(delete)
        token = page.context['form']['operation_token'].value()
        self.assertTrue(goal.entries.exists())
        self.assertEqual(self.client.post(delete,{'operation_token':token}).status_code,302)
        self.assertEqual(self.client.post(delete,{'operation_token':token}).status_code,302)
        self.assertFalse(goal.entries.exists())

    def test_duplicate_post_and_changed_payload_cannot_create_duplicate(self):
        url = self.url('create')
        token = self.client.get(url).context['form']['operation_token'].value()
        data = {'name':'Quỹ','amount':'100000','start_date':'2026-09-01','due_date':'','note':'','operation_token':token}
        self.assertEqual(self.client.post(url,data).status_code,302)
        self.assertEqual(self.client.post(url,data).status_code,302)
        self.assertEqual(SavingsGoal.objects.count(),1)
        self.assertEqual(self.client.post(url,{**data,'name':'Khác'}).status_code,200)
        self.assertEqual(SavingsGoal.objects.count(),1)
        goal = SavingsGoal.objects.get()
        token = savings.issue(self.user,'entry_create',goal)
        payload = {'kind':'contribution','amount':Decimal(10),'date':date(2026,10,1),'note':''}
        self.op(goal,'entry_create',payload,token=token)
        self.assertTrue(self.op(goal,'entry_create',payload,token=token)[1])
        self.assertEqual(goal.entries.count(),1)

    def test_invalid_expired_wrong_owner_target_action_and_modified_tokens(self):
        goal = self.goal()
        token = savings.issue(self.user,'archive',goal)
        for bad in ['',token+'x',savings.issue(self.bob,'archive',goal),savings.issue(self.user,'reopen',goal)]:
            with self.assertRaises(savings.SavingsConflict):self.op(goal,'archive',token=bad or 'invalid')
        other = self.goal()
        with self.assertRaises(savings.SavingsConflict):self.op(other,'archive',token=token)
        with patch('django.core.signing.time.time',return_value=time.time()+savings.TOKEN_AGE+1):
            with self.assertRaises(savings.SavingsConflict):self.op(goal,'archive',token=token)
        self.assertEqual(SavingsOperation.objects.count(),2)  # Only the two goal creations.

    def test_stale_goal_and_entry_forms_do_not_overwrite_concurrent_changes(self):
        goal = self.goal()
        stale = savings.issue(self.user,'goal_edit',goal)
        entry = self.add(goal)
        with self.assertRaises(savings.SavingsConflict):self.op(goal,'goal_edit',self.goal_data(name='Stale'),token=stale)
        stale_entry = savings.issue(self.user,'entry_edit',goal,entry)
        payload = {'kind':'contribution','amount':Decimal(100),'date':entry.date,'note':''}
        self.op(goal,'entry_edit',payload,entry)
        with self.assertRaises(savings.SavingsConflict):self.op(goal,'entry_edit',payload,entry,stale_entry)

    def test_rollback_does_not_leave_entry_receipt_or_version_and_can_retry(self):
        goal = self.goal()
        before = SavingsOperation.objects.count()
        token = savings.issue(self.user,'entry_create',goal)
        payload = {'kind':'contribution','amount':Decimal(100),'date':date(2026,10,1),'note':''}
        with patch.object(SavingsOperation,'save',autospec=True) as save:
            # Insertion succeeds; failure after the ledger write must roll everything back.
            def fail_after_insert(obj,*args,**kwargs):
                if kwargs.get('update_fields'):raise RuntimeError('QA rollback')
                return super(SavingsOperation,obj).save(*args,**kwargs)
            save.side_effect=fail_after_insert
            with self.assertRaises(RuntimeError):self.op(goal,'entry_create',payload,token=token)
        goal.refresh_from_db()
        self.assertEqual((goal.version,goal.entries.count(),SavingsOperation.objects.count()),(0,0,before))
        self.op(goal,'entry_create',payload,token=token)
        self.assertEqual(goal.entries.count(),1)

    def test_large_decimal_totals_not_sqlite_sum(self):
        goal = self.goal(amount=Decimal('999999999999999'))
        self.add(goal,'999999999999999')
        self.add(goal,'999999999999999')
        value = savings.summary(goal)['accumulated']
        self.assertIsInstance(value,Decimal)
        self.assertEqual(value,Decimal('1999999999999998'))
        self.assertContains(self.client.get(self.url('detail',goal)),'1.999.999.999.999.998 VND')

    def test_ownership_all_views_and_tokens(self):
        goal = self.goal()
        entry = self.add(goal)
        self.client.force_login(self.bob)
        for name,tail in [('detail',()),('edit',()),('status',('archive',)),('entry_create',()),
                          ('entry_edit',(entry.pk,)),('entry_delete',(entry.pk,))]:
            url = self.url(name,goal,*tail)
            self.assertEqual(self.client.get(url).status_code,404)
            self.assertEqual(self.client.post(url,{}).status_code,405 if name=='detail' else 404)
        self.assertNotContains(self.client.get(self.url('list')),goal.name)
        self.assertNotContains(self.client.get(reverse('finance:dashboard')),goal.name)

    def test_auth_csrf_get_no_writes_and_empty_state(self):
        self.assertContains(self.client.get(self.url('list')),'Bạn chưa có mục tiêu')
        goal = self.goal()
        entry = self.add(goal)
        before = [list(model.objects.values()) for model in [SavingsGoal,SavingsEntry,SavingsOperation]]
        for url in [self.url('list'),self.url('detail',goal),self.url('create'),self.url('edit',goal),
                    self.url('status',goal,'archive'),self.url('entry_create',goal),
                    self.url('entry_edit',goal,entry.pk),self.url('entry_delete',goal,entry.pk)]:
            self.assertEqual(self.client.get(url).status_code,200)
        self.assertEqual(before,[list(model.objects.values()) for model in [SavingsGoal,SavingsEntry,SavingsOperation]])
        csrf = Client(enforce_csrf_checks=True)
        csrf.force_login(self.user)
        self.assertEqual(csrf.post(self.url('entry_create',goal),{}).status_code,403)
        self.client.logout()
        self.assertEqual(self.client.get(self.url('list')).status_code,302)
        self.assertEqual(self.client.post(self.url('entry_create',goal),{}).status_code,302)

    def test_pagination_dashboard_only_three_active_and_escape_text(self):
        goal = self.goal(name='<script>QA</script>')
        for i in range(21):self.add(goal,'1')
        page = self.client.get(self.url('detail',goal))
        self.assertEqual((len(page.context['page_obj']),page.context['page_obj'].paginator.count),(20,21))
        self.assertEqual(len(self.client.get(self.url('detail',goal)+'?page=2').context['page_obj']),1)
        self.assertContains(page,'&lt;script&gt;QA&lt;/script&gt;')
        for i in range(12):self.goal(name=f'QA {i}')
        self.assertEqual(len(self.client.get(self.url('list')+'?page=2').context['page_obj']),1)
        active = self.client.get(reverse('finance:dashboard')).context['savings_goals']
        self.assertEqual(len(active),3)
        reached = active[0]['goal']
        self.add(reached,'1000000')
        self.op(active[1]['goal'],'archive')
        for item in self.client.get(reverse('finance:dashboard')).context['savings_goals']:
            self.assertEqual(item['state'],'active')

    def test_database_constraints_and_account_deletion_cascade(self):
        goal = self.goal()
        self.add(goal)
        for model,fields in [(SavingsGoal,{'amount':-1}),(SavingsEntry,{'amount':0}),(SavingsEntry,{'kind':'fake'})]:
            with self.assertRaises(IntegrityError),transaction.atomic():model.objects.all().update(**fields)
        self.user.delete()
        self.assertEqual((SavingsGoal.objects.count(),SavingsEntry.objects.count(),SavingsOperation.objects.count()),(0,0,0))


class SavingsFinancialIsolationTests(FinanceCase):
    def test_all_financial_tables_unchanged_after_every_savings_mutation(self):
        month = date(2026,9,1)
        MonthlyCoverage.objects.create(user=self.alice,month=month,status='complete',confirmed_at=NOW)
        Budget.objects.create(user=self.alice,month=month,amount=Decimal(50000))
        ForecastResult.objects.create(user=self.alice,target_month=date(2026,10,1),fingerprint='a'*64,
            history_count=3,history_start=date(2026,7,1),history_end=month,method='mean3',estimate='50000')
        receipt = ClassificationSuggestion.objects.create(user=self.alice,input_digest='a'*64,kind='expense',
            mode='vi',predicted_label='Restaurants',model_name='QA',model_sha256='b'*64,seal='c'*64,expires_at=NOW)
        ClassificationFeedback.objects.create(user=self.alice,transaction=self.alice_row,suggestion=receipt,
            mode='vi',model_name='QA',model_sha256='b'*64,predicted_label='Restaurants',final_category=self.food,
            final_category_name=self.food.name,final_label='Restaurants',applied=True,same_label=True)
        models = [m for m in apps.get_app_config('finance').get_models() if not m.__name__.startswith('Savings')]
        before = {m.__name__:list(m.objects.order_by('pk').values()) for m in models}
        with patch('django.utils.timezone.now',return_value=NOW):
            goal,_ = savings.execute(self.alice,savings.issue(self.alice,'goal_create'),'goal_create',data={
                'name':'QA riêng','amount':Decimal(100),'start_date':month,'due_date':None,'note':''})
            def run(action,data=None,entry=None):
                goal.refresh_from_db()
                return savings.execute(self.alice,savings.issue(self.alice,action,goal,entry),action,goal.pk,
                    entry.pk if entry else None,data)
            run('entry_create',{'kind':'contribution','amount':Decimal(100),'date':month,'note':''})
            entry = goal.entries.get()
            run('entry_edit',{'kind':'contribution','amount':Decimal(120),'date':month,'note':''},entry)
            run('entry_create',{'kind':'withdrawal','amount':Decimal(10),'date':month,'note':''})
            run('entry_delete',entry=goal.entries.latest('pk'))
            run('archive')
            run('reopen')
        self.assertEqual(before,{m.__name__:list(m.objects.order_by('pk').values()) for m in models})


class ConcurrentSavingsTests(TransactionTestCase):
    def scenario(self, mode):
        user = User.objects.create_user('parallel-savings-qa')
        with patch('django.utils.timezone.now',return_value=NOW):
            goal,_ = savings.execute(user,savings.issue(user,'goal_create'),'goal_create',data={
                'name':'QA đồng thời','amount':Decimal(100),'start_date':date(2026,10,1),'due_date':None,'note':''})
            payload = {'kind':'contribution','amount':Decimal(100),'date':date(2026,10,1),'note':''}
            if mode=='withdraw':
                savings.execute(user,savings.issue(user,'entry_create',goal),'entry_create',goal.pk,data=payload)
                payload={**payload,'kind':'withdrawal','amount':Decimal(80)}
            tokens=[savings.issue(user,'entry_create',goal) for _ in range(2)]
            if mode=='replay':tokens[1]=tokens[0]
            barrier=Barrier(2);results=Queue()
            def worker(index):
                close_old_connections()
                try:
                    own=User.objects.get(pk=user.pk)
                    barrier.wait(timeout=10)
                    savings.execute(own,tokens[index],'entry_create',goal.pk,data=payload)
                    results.put((index,'ok'))
                except OperationalError as exc:
                    results.put((index,'locked' if 'locked' in str(exc).lower() else 'unexpected-db-error'))
                except ValidationError:results.put((index,'invalid'))
                except Exception as exc:results.put((index,type(exc).__name__))
                finally:close_old_connections()
            threads=[Thread(target=worker,args=(i,)) for i in range(2)]
            for thread in threads:thread.start()
            for thread in threads:thread.join(timeout=20)
            self.assertTrue(all(not t.is_alive() for t in threads))
            outputs=[results.get_nowait() for _ in range(2)]
            self.assertIn('ok',[s for _,s in outputs],outputs)
            for index,state in outputs:
                self.assertIn(state,['ok','locked','invalid'],outputs)
                if state=='locked':
                    try:savings.execute(user,tokens[index],'entry_create',goal.pk,data=payload)
                    except ValidationError:self.assertEqual(mode,'withdraw')
            actual=savings.summary(goal)['accumulated']
            expected={'deposit':Decimal(200),'withdraw':Decimal(20),'replay':Decimal(100)}[mode]
            self.assertEqual(actual,expected)
            self.assertEqual(goal.entries.count(),1 if mode=='replay' else 2)
            self.assertEqual(savings.validate_history(goal,list(goal.entries.all())),expected)

    def test_two_distinct_deposits_not_deduplicated_by_date_or_amount(self):self.scenario('deposit')
    def test_two_withdrawals_cannot_overdraw(self):self.scenario('withdraw')
    def test_concurrent_replay_only_one_entry(self):self.scenario('replay')
