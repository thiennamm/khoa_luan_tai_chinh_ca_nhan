"""Simulated dates/data in isolated test databases, never real forecast evidence."""
from datetime import date, datetime, timezone as utc
from decimal import Decimal
from queue import Queue
from threading import Barrier, Thread
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.db import IntegrityError, OperationalError, close_old_connections, transaction
from django.db.migrations.executor import MigrationExecutor
from django.db import connection
from django.test import Client, TransactionTestCase
from django.urls import reverse
from django.utils import timezone

from .coverage import change_month_status, review_month
from .csv_import import inspect_csv, stage_csv, confirm_batch
from .forecast_history import eligible, review
from .forecasting import compute_and_store, snapshot
from .models import (ForecastHistory, ForecastResult, ForecastDataVersion, MonthlyCoverage,
    Transaction, Category)
from . import test_forecast as forecast_tests
from .tests import FinanceCase


class ForecastHistoryTests(FinanceCase):
    target = date(2026,10,1)
    seed = forecast_tests.ForecastIntegrationTests.seed

    def setUp(self):
        super().setUp()
        self.clock = patch('django.utils.timezone.now', return_value=datetime(2026,10,20,10,tzinfo=utc.utc))
        self.clock.start(); self.addCleanup(self.clock.stop)
        Transaction.objects.filter(user=self.alice).delete()
        self.url = reverse('finance:forecast_history')

    def compute(self):
        return compute_and_store(self.alice, snapshot(self.alice))

    def complete(self, month, user=None):
        user = user or self.alice
        change_month_status(user, month, 'complete', review_token=review_month(user, month)['review_token'],
            confirm_no_expense=True)

    def actual(self, amount='150', month=date(2026,10,1)):
        return Transaction.objects.create(user=self.alice, category=self.food,
            kind='expense', amount=Decimal(amount), date=month)

    def test_only_successful_personal_post_records_and_repeated_input_deduplicates(self):
        self.seed(3)
        with patch('finance.forecast_views.compute_and_store', wraps=compute_and_store) as compute:
            self.client.get(reverse('finance:forecast'))
            self.client.get(self.url)
            compute.assert_not_called()
            self.assertFalse(ForecastHistory.objects.exists())
            self.assertEqual(self.client.post(reverse('finance:forecast')).status_code,302)
        original = list(ForecastHistory.objects.values())
        with patch('django.utils.timezone.now', return_value=datetime(2026,10,21,10,tzinfo=utc.utc)):
            self.client.post(reverse('finance:forecast'))
        self.assertEqual(list(ForecastHistory.objects.values()),original)
        item = ForecastHistory.objects.get()
        self.assertTrue(eligible(item))
        self.assertEqual(item.configuration_version,'personal-expense-v1')
        self.assertEqual([x['month'] for x in item.inputs],['2026-07-01','2026-08-01','2026-09-01'])
        self.assertNotIn('description',str(item.inputs))
        self.assertEqual(self.client.post(self.url).status_code,405)

    def test_history_immutable_and_kept_when_current_result_stale_or_replaced(self):
        self.seed(3)
        self.compute(); item = ForecastHistory.objects.get(); frozen=list(ForecastHistory.objects.values())
        item.estimate='1'
        with self.assertRaises(ValidationError): item.save()
        with self.assertRaises(ValidationError): ForecastHistory.objects.update(estimate='1')
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                with transaction.atomic(): ForecastHistory.objects.create(**{k:v for k,v in frozen[0].items()})
        self.actual()
        self.assertIsNone(self.client.get(reverse('finance:forecast')).context.get('result'))
        self.assertEqual(list(ForecastHistory.objects.values()),frozen)
        self.compute()
        self.assertEqual(ForecastHistory.objects.count(),2)
        self.assertEqual(ForecastResult.objects.count(),1)
        self.assertEqual(list(ForecastHistory.objects.filter(pk=item.pk).values()),frozen)

    def test_current_month_and_vietnam_boundary_zero_requires_confirmation(self):
        from .recurring_forms import RecurringRuleForm
        from . import recurring
        form=RecurringRuleForm({'name':'Dự kiến chưa ghi nhận QA','kind':'expense','amount':'5000',
            'category':self.food.pk,'due_day':'25','start_month':'2026-10','end_month':''},user=self.alice)
        self.assertTrue(form.is_valid(),form.errors)
        recurring.save_rule(form,self.alice)
        self.seed(3); self.compute()
        self.assertEqual(review(self.alice)['rows'][0]['status'],'Tháng chưa kết thúc')
        for instant, state in [(datetime(2026,10,31,16,59,tzinfo=utc.utc),'Tháng chưa kết thúc'),
                (datetime(2026,10,31,17,0,tzinfo=utc.utc),'Chưa đủ dữ liệu đối chiếu')]:
            with patch('django.utils.timezone.now',return_value=instant), timezone.override('America/New_York'):
                result=review(self.alice)
                self.assertEqual(result['rows'][0]['status'],state)
                self.assertIsNone(result['mae'])
        with patch('django.utils.timezone.now',return_value=datetime(2026,11,1,1,tzinfo=utc.utc)):
            change_month_status(self.alice,self.target,'incomplete')
            self.assertIsNone(review(self.alice)['rows'][0]['actual'])
            self.complete(self.target)
            result=review(self.alice)
            self.assertEqual(result['rows'][0]['actual'],Decimal(0))
            self.assertEqual(result['mae'],Decimal('100'))

    def test_first_valid_version_per_month_late_or_lookahead_entries_excluded(self):
        self.seed(3,values=['100','200','300']); self.compute()
        first=ForecastHistory.objects.get()
        with patch('django.utils.timezone.now',return_value=datetime(2026,10,21,1,tzinfo=utc.utc)):
            self.actual('10',date(2026,9,2)); self.complete(date(2026,9,1)); self.compute()
        base={field:getattr(first,field) for field in ('user_id','target_month','estimate','method',
            'configuration_version','configuration','history_start','history_end','history_count','inputs','details','origin')}
        late=ForecastHistory.objects.create(**base,calculated_at=datetime(2026,11,1,0,tzinfo=utc.utc),fingerprint='a'*64)
        lookahead=ForecastHistory.objects.create(**{**base,'history_end':self.target},
            calculated_at=first.calculated_at,fingerprint='b'*64)
        self.assertFalse(eligible(late)); self.assertFalse(eligible(lookahead))
        with patch('django.utils.timezone.now',return_value=datetime(2026,11,2,1,tzinfo=utc.utc)):
            self.actual(); self.complete(self.target)
            result=review(self.alice)
        self.assertEqual(result['evaluated_months'],1)
        self.assertEqual(result['mae'],Decimal('50'))
        self.assertEqual([r['entry'].pk for r in result['rows'] if r['used_for_mae']],[first.pk])
        self.assertEqual(sum(r['status']=='Không đủ thông tin đánh giá' for r in result['rows']),2)

    def test_signed_errors_decimal_mae_across_months(self):
        self.seed(3,values=['100','200','300']); self.compute()
        with patch('django.utils.timezone.now',return_value=datetime(2026,11,2,1,tzinfo=utc.utc)):
            self.actual('250'); self.complete(self.target); self.compute()
        with patch('django.utils.timezone.now',return_value=datetime(2026,12,2,1,tzinfo=utc.utc)):
            self.complete(date(2026,11,1))
            result=review(self.alice)
        by_month={r['entry'].target_month:r for r in result['rows']}
        self.assertEqual(by_month[self.target]['bias'],Decimal('-50'))
        self.assertEqual(by_month[date(2026,11,1)]['bias'],Decimal('250'))
        self.assertEqual(result['mae'],Decimal('150'))
        self.assertIsInstance(result['mae'],Decimal)
        self.assertEqual(result['evaluated_months'],2)

    def test_large_stored_integer_and_signed_error_do_not_lose_digits(self):
        self.seed(3)
        estimate=Decimal('999999999999999999999999999999')
        with patch('finance.forecasting.calculate',return_value={'method':'mean3','estimate':estimate}):
            self.compute()
        with patch('django.utils.timezone.now',return_value=datetime(2026,11,2,1,tzinfo=utc.utc)):
            self.actual('1'); self.complete(self.target)
            result=review(self.alice)
        expected=Decimal('999999999999999999999999999998')
        self.assertEqual(result['rows'][0]['bias'],expected)
        self.assertEqual(result['rows'][0]['absolute_error'],expected)
        self.assertEqual(result['mae'],expected)

    def test_crud_and_csv_invalidate_and_reconfirmation_recalculates_actual_only(self):
        self.seed(3); self.compute(); frozen=list(ForecastHistory.objects.values())
        with patch('django.utils.timezone.now',return_value=datetime(2026,11,2,1,tzinfo=utc.utc)):
            tx=self.actual(); self.complete(self.target)
            self.assertEqual(review(self.alice)['rows'][0]['actual'],Decimal('150'))
            tx.amount=Decimal('170');tx.save()
            self.assertIsNone(review(self.alice)['mae'])
            self.complete(self.target)
            self.assertEqual(review(self.alice)['rows'][0]['actual'],Decimal('170'))
            tx.delete()
            self.assertIsNone(review(self.alice)['mae'])
            self.complete(self.target)
            raw=('date,kind,amount,category,description\n2026-10-10,expense,25,'+self.food.name+',QA\n').encode()
            inspection=inspect_csv(raw,self.alice);self.assertTrue(inspection.valid)
            batch=stage_csv(raw,self.alice,inspection); confirm_batch(batch.pk,self.alice)
            self.assertIsNone(review(self.alice)['rows'][0]['actual'])
            self.complete(self.target)
            self.assertEqual(review(self.alice)['rows'][0]['actual'],Decimal('25'))
            change_month_status(self.alice,self.target,'unknown')
            self.assertEqual(review(self.alice)['evaluated_months'],0)
        self.assertEqual(list(ForecastHistory.objects.values()),frozen)

    def test_view_owner_pagination_full_summary_and_cache(self):
        self.seed(3); self.compute()
        original=ForecastHistory.objects.get()
        for i in range(22):
            values={f.name:getattr(original,f.name) for f in ForecastHistory._meta.fields if f.name not in ('id','fingerprint')}
            ForecastHistory.objects.create(**values,fingerprint=f'{i:064x}')
        page=self.client.get(self.url)
        self.assertEqual(len(page.context['page_obj']),20)
        self.assertEqual(len(self.client.get(self.url,{'page':2}).context['page_obj']),3)
        with patch('django.utils.timezone.now',return_value=datetime(2026,11,2,1,tzinfo=utc.utc)):
            self.complete(self.target)
            for page_number in (1,2):
                compared=self.client.get(self.url,{'page':page_number})
                self.assertEqual(compared.context['evaluated_months'],1)
                self.assertEqual(compared.context['mae'],Decimal('100'))
        self.assertIn('no-store',page.headers['Cache-Control'])
        self.client.force_login(self.bob)
        page=self.client.get(self.url,{'user_id':self.alice.pk})
        self.assertContains(page,'Chưa có lịch sử dự báo')
        self.assertEqual(page.context['evaluated_months'],0)
        self.assertEqual(Client().get(self.url).status_code,302)

    def test_failure_or_history_insert_error_rolls_back_current_and_history(self):
        self.seed(3)
        with patch('finance.forecasting.ForecastHistory.objects.get_or_create',side_effect=RuntimeError('QA')):
            with self.assertRaises(RuntimeError):self.compute()
        self.assertFalse(ForecastResult.objects.exists());self.assertFalse(ForecastHistory.objects.exists())
        from .forecast_math import ForecastFailure
        with patch('finance.forecasting.calculate',side_effect=ForecastFailure('QA')):
            self.assertEqual(self.client.post(reverse('finance:forecast')).status_code,503)
        self.assertFalse(ForecastHistory.objects.exists())

    def test_personal_compute_post_requires_csrf(self):
        self.seed(3)
        client=Client(enforce_csrf_checks=True);client.force_login(self.alice)
        self.assertEqual(client.post(reverse('finance:forecast')).status_code,403)
        self.assertFalse(ForecastHistory.objects.exists())

    def test_demo_does_not_create_personal_history_and_account_delete_cascades(self):
        self.seed(3);self.compute(); frozen=list(ForecastHistory.objects.values())
        self.client.get(reverse('finance:forecast_demo'))
        self.client.post(reverse('finance:forecast_demo'))
        self.assertEqual(list(ForecastHistory.objects.values()),frozen)
        Transaction.objects.filter(user=self.alice).delete()
        self.food.delete()
        self.alice.delete()
        self.assertFalse(ForecastHistory.objects.exists())

    def test_concurrent_change_during_review_is_not_reported_as_current_actual(self):
        self.seed(3);self.compute()
        from .coverage import monthly_history
        def changed(*args):
            ForecastDataVersion.objects.filter(user=self.alice).update(version=999)
            return monthly_history(*args)
        with patch('django.utils.timezone.now',return_value=datetime(2026,11,2,1,tzinfo=utc.utc)), \
                patch('finance.forecast_history.monthly_history',side_effect=changed):
            self.assertEqual(self.client.get(self.url).status_code,409)


class ForecastHistoryConcurrentTests(TransactionTestCase):
    def test_two_calculations_have_one_snapshot(self):
        from django.contrib.auth import get_user_model
        user=get_user_model().objects.create_user('parallel-history-qa')
        category=Category.objects.create(user=user,name='QA',kind='expense')
        barrier=Barrier(2);results=Queue()
        with patch('django.utils.timezone.now',return_value=datetime(2026,10,20,10,tzinfo=utc.utc)):
            for month in (date(2026,7,1),date(2026,8,1),date(2026,9,1)):
                MonthlyCoverage.objects.create(user=user,month=month,status='complete',confirmed_at=timezone.now())
            source=snapshot(user)
            from .forecast_math import calculate
            def simultaneous(rows):
                answer=calculate(rows);barrier.wait(timeout=10);return answer
            def worker():
                close_old_connections()
                try:compute_and_store(user,source);results.put('ok')
                except OperationalError as exc:results.put('locked' if 'locked' in str(exc).lower() else 'error')
                except Exception:results.put('error')
                finally:close_old_connections()
            with patch('finance.forecasting.calculate',side_effect=simultaneous):
                threads=[Thread(target=worker) for _ in range(2)]
                for thread in threads:thread.start()
                for thread in threads:thread.join(timeout=20)
            self.assertTrue(all(not thread.is_alive() for thread in threads))
            output=[results.get_nowait() for _ in threads]
            self.assertIn('ok',output);self.assertNotIn('error',output)
            self.assertEqual(ForecastHistory.objects.count(),1)
            self.assertEqual(ForecastResult.objects.count(),1)


class ForecastHistoryMigrationTests(TransactionTestCase):
    def test_legacy_preserved_but_not_eligible_and_existing_rows_unchanged(self):
        previous=[('finance','0011_recurringoccurrence_recurringevent_recurringrule_and_more')]
        executor=MigrationExecutor(connection);executor.migrate(previous)
        try:
            apps=executor.loader.project_state(previous).apps
            User=apps.get_model('auth','User');Result=apps.get_model('finance','ForecastResult')
            user=User.objects.create(username='legacy-history-qa',password='!')
            Result.objects.create(user=user,target_month=date(2026,10,1),fingerprint='c'*64,
                history_start=date(2026,7,1),history_end=date(2026,9,1),history_count=3,
                method='mean3',estimate='100',configuration={})
            old=list(Result.objects.values())
            latest=MigrationExecutor(connection);latest.migrate(latest.loader.graph.leaf_nodes())
            self.assertEqual(list(Result.objects.values()),old)
            entry=ForecastHistory.objects.get()
            self.assertEqual(entry.origin,'legacy');self.assertEqual(entry.inputs,[])
            self.assertFalse(eligible(entry))
        finally:
            latest=MigrationExecutor(connection);latest.migrate(latest.loader.graph.leaf_nodes())
