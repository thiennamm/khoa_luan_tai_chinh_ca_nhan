"""Dữ liệu cố định dưới đây chỉ tồn tại trong bộ nhớ/test DB, không phải demo."""
from datetime import date, datetime, timezone as dt_timezone
from decimal import Decimal
from unittest.mock import patch

from django.db import IntegrityError, transaction
from django.test import Client, SimpleTestCase
from django.urls import reverse
from django.utils import timezone

from .coverage import change_month_status, review_month
from .csv_import import confirm_batch, inspect_csv, stage_csv
from .test_csv_import import csv_bytes
from .forecast_math import ForecastFailure, calculate, choose_method, features, ridge_predict
from .forecasting import StaleForecast, compute_and_store, shift_month, snapshot
from .models import ForecastDataVersion, ForecastResult, MonthlyCoverage, Transaction
from .tests import FinanceCase


def history(values, first=date(2023, 10, 1)):
    return [{'month': shift_month(first, index), 'forecast_expense': Decimal(value)} for index, value in enumerate(values)]


class ForecastMathTests(SimpleTestCase):
    def test_features_use_only_previous_lags_and_mean(self):
        self.assertEqual(features([Decimal(i) for i in range(1, 14)]),
                         [Decimal('13'),Decimal('12'),Decimal('11'),Decimal('2'),Decimal('12')])
        with self.assertRaises(ForecastFailure):
            features([Decimal('1')] * 11)

    def test_short_regime_decimal_mean_no_ml_and_round_half_up(self):
        with patch('finance.forecast_math.ridge_predict') as ridge:
            result = calculate(history(['10','20','20']))
        ridge.assert_not_called()
        self.assertEqual(result['method'], 'mean3')
        self.assertEqual(result['estimate'], Decimal('17'))
        self.assertEqual(result['candidates'], [])
        result = calculate(history(['999999999999999'] * 3))
        self.assertEqual(result['estimate'], Decimal('999999999999999'))

    def test_missing_month_unknown_negative_and_short_input_fail(self):
        for rows in [history(['1','2']), history(['1','2','-1']),
                     [{'month':date(2026,1,1),'forecast_expense':None}] * 3,
                     [history(['1','2','3'])[0], history(['1','2','3'])[2], history(['1','2','3'])[1]]]:
            with self.assertRaises(ForecastFailure):
                calculate(rows)

    def test_tie_rules_and_unrounded_mae(self):
        candidates = [{'method':method, 'mae':'10'} for method in ['ridge_10','seasonal','previous','ridge_0.1','mean3','ridge_1']]
        self.assertEqual(choose_method(candidates),'mean3')
        self.assertEqual(choose_method([c for c in candidates if c['method'].startswith('ridge_')]),'ridge_0.1')
        self.assertEqual(choose_method([{'method':'mean3','mae':'0.49'}, {'method':'ridge_10','mae':'0.48'}]),'ridge_10')
        self.assertEqual(choose_method([{'method':'previous','mae':'1'}, {'method':'seasonal','mae':'1'}]),'previous')

    def test_validation_six_one_step_origins_only_past(self):
        rows = history([str(100 + i) for i in range(36)])
        calls = []
        def predict(past, alpha):
            calls.append((list(past),alpha))
            return past[-1]
        with patch('finance.forecast_math.ridge_predict',side_effect=predict):
            result = calculate(rows)
        self.assertEqual(result['method'],'previous') # bằng Ridge giả ở test, ưu tiên baseline
        self.assertEqual(len(calls),18)
        for group, alpha in enumerate([0.1,1.0,10.0]):
            for step in range(6):
                past, actual_alpha = calls[group*6+step]
                self.assertEqual(past,[row['forecast_expense'] for row in rows[:30+step]])
                self.assertEqual(actual_alpha,alpha)
        changed = history([str(100+i) if i < 35 else '10000' for i in range(36)])
        changed_calls = []
        with patch('finance.forecast_math.ridge_predict',side_effect=lambda past,alpha: changed_calls.append((list(past),alpha)) or past[-1]):
            calculate(changed)
        self.assertEqual(changed_calls,calls) # đổi target cuối không đổi đầu vào fit của bất kỳ mốc validation

    def test_negative_ridge_clipped_before_mae_and_baseline_wins(self):
        with patch('finance.forecast_math.ridge_predict',return_value=Decimal('-999')):
            result = calculate(history(['0']*36))
        self.assertEqual(result['method'],'mean3')
        for candidate in result['candidates']:
            self.assertEqual(Decimal(candidate['mae']),Decimal('0'))
            self.assertTrue(all(Decimal(point['predicted'])==0 for point in candidate['points']))

    def test_selected_ridge_refits_all_history_after_selection(self):
        calls = []
        def predict(past,alpha):
            calls.append((len(past),alpha))
            return past[-1]+1
        with patch('finance.forecast_math.ridge_predict',side_effect=predict):
            result=calculate(history([str(i) for i in range(36)]))
        self.assertEqual(result['method'],'ridge_0.1')
        self.assertEqual(calls[-1],(36,0.1))
        self.assertEqual(len(calls),19)

    def test_real_pipeline_scaler_fit_on_past_rows_only(self):
        import numpy as np
        from sklearn.pipeline import Pipeline
        original = Pipeline.fit
        observed = []
        def inspect_fit(model,x,y,**kwargs):
            result = original(model,x,y,**kwargs)
            observed.append((x.copy(),y.copy(),model.named_steps['scaler'].mean_.copy(),model.named_steps['scaler'].n_samples_seen_))
            return result
        values=[Decimal(i) for i in range(30)]
        with patch('sklearn.pipeline.Pipeline.fit',new=inspect_fit):
            prediction=ridge_predict(values,0.1)
        x,y,mean,count=observed[0]
        self.assertEqual(x.shape,(18,5))
        np.testing.assert_allclose(x,np.asarray([features(values[:index]) for index in range(12,30)],dtype=float))
        np.testing.assert_allclose(y,np.asarray(values[12:],dtype=float))
        np.testing.assert_allclose(mean,x.mean(axis=0))
        self.assertEqual(count,18)
        self.assertTrue(prediction.is_finite())

    def test_model_error_and_nonfinite_never_fall_back(self):
        for outcome in [OSError('test DLL runtime'), Decimal('NaN')]:
            with self.subTest(outcome=outcome):
                kwargs = {'side_effect':outcome} if isinstance(outcome,Exception) else {'return_value':outcome}
                with patch('finance.forecast_math.ridge_predict',**kwargs),self.assertRaises(ForecastFailure):
                    calculate(history(['1']*36))


class ForecastIntegrationTests(FinanceCase):
    target = date(2026,10,1)

    def setUp(self):
        super().setUp()
        clock=patch('finance.coverage_calendar.timezone.now',return_value=datetime(2026,10,20,10,tzinfo=dt_timezone.utc))
        clock.start()
        self.addCleanup(clock.stop)
        self.url=reverse('finance:forecast')

    def seed(self,count,values=None,user=None):
        # Chỉ test DB: ghi tháng đã xác nhận; số 0 không tạo giao dịch tiền 0.
        user=user or self.alice
        category=self.food if user.pk==self.alice.pk else self.bob_category
        values=values if values is not None else [Decimal('100')]*count
        months=[shift_month(self.target,index-count) for index in range(count)]
        Transaction.objects.bulk_create([Transaction(user=user,category=category,kind='expense',amount=Decimal(value),date=month)
                                         for month,value in zip(months,values) if Decimal(value)>0])
        MonthlyCoverage.objects.bulk_create([MonthlyCoverage(user=user,month=month,status='complete',confirmed_at=timezone.now()) for month in months])
        return months

    def test_insufficient_history_lists_exact_months_and_get_post_do_not_fit(self):
        with patch('finance.forecast_views.compute_and_store') as compute:
            for method in [self.client.get,self.client.post]:
                page=method(self.url)
                self.assertContains(page,'Chưa đủ lịch sử')
                self.assertIsNone(page.context.get('result'))
                self.assertEqual([r['month'] for r in page.context['source']['required']],
                                 [date(2026,7,1),date(2026,8,1),date(2026,9,1)])
            compute.assert_not_called()
        self.seed(2)
        source=snapshot(self.alice)
        self.assertEqual(source['history_count'],2)
        self.assertEqual([r['month'] for r in source['required']],[date(2026,7,1)])
        self.assertFalse(ForecastResult.objects.exists())

    def test_three_months_mean_vnd_current_target_and_only_post_calculates(self):
        self.seed(3,values=['100','200','300'])
        with patch('finance.forecast_math.ridge_predict') as ridge,patch('finance.forecast_views.compute_and_store', wraps=compute_and_store) as compute:
            self.client.get(self.url)
            compute.assert_not_called()
            response=self.client.post(self.url,{'user_id':self.bob.pk,'target_month':'2026-11','method':'ridge_10'})
            self.assertEqual(response.status_code,302)
            self.client.get(self.url)
            self.assertEqual(compute.call_count,1)
            ridge.assert_not_called()
        saved=ForecastResult.objects.get(user=self.alice)
        self.assertEqual(saved.target_month,self.target)
        self.assertEqual(saved.estimate_decimal,Decimal('200'))
        self.assertEqual(saved.method,'mean3')
        self.assertEqual(saved.history_end,date(2026,9,1))
        self.assertFalse(ForecastResult.objects.filter(user=self.bob).exists())

    def test_gap_stops_tail_no_join_and_zero_confirmed_remains_valid(self):
        months=self.seed(6,values=['1','2','3','0','0','0'])
        MonthlyCoverage.objects.filter(user=self.alice,month=months[-2]).update(status='incomplete',confirmed_at=None)
        source=snapshot(self.alice)
        self.assertEqual(source['history_count'],1)
        self.assertEqual([r['month'] for r in source['required']],[date(2026,8,1)])
        token=review_month(self.alice,date(2026,8,1))['review_token']
        change_month_status(self.alice,date(2026,8,1),'complete',review_token=token,confirm_no_expense=True)
        result=compute_and_store(self.alice,snapshot(self.alice))
        self.assertEqual(result.estimate_decimal,Decimal('0'))
        self.assertEqual(result.history_count,6)

    def test_old_segment_without_previous_month_does_not_qualify(self):
        months=self.seed(36,values=['0']*36)
        MonthlyCoverage.objects.filter(user=self.alice,month=months[-1]).delete()
        source=snapshot(self.alice)
        self.assertEqual(source['history_count'],0)
        self.assertEqual(source['history'],[])
        self.assertEqual([r['month'] for r in source['required']],[date(2026,9,1)])

    def test_account_separation_and_no_cache_leak(self):
        self.seed(3,values=['111','111','111'])
        self.seed(3,values=['999','999','999'],user=self.bob)
        alice=compute_and_store(self.alice,snapshot(self.alice))
        bob=compute_and_store(self.bob,snapshot(self.bob))
        self.assertEqual((alice.estimate_decimal,bob.estimate_decimal),(Decimal('111'),Decimal('999')))
        page=self.client.get(self.url)
        self.assertEqual(page.context['result'].user_id,self.alice.pk)
        self.assertContains(page,'111 ₫')
        self.assertNotContains(page,'999 ₫')
        self.assertIn('no-store',page.headers['Cache-Control'])

    def test_current_future_and_income_not_numeric_inputs_but_edits_invalidate(self):
        self.seed(3,values=['10','20','30'])
        source=snapshot(self.alice)
        old=compute_and_store(self.alice,source)
        Transaction.objects.create(user=self.alice,category=self.food,kind='expense',amount=Decimal('999999999'),date=self.target)
        Transaction.objects.create(user=self.alice,category=self.food,kind='expense',amount=Decimal('999999999'),date=date(2027,1,1))
        fresh=snapshot(self.alice)
        self.assertEqual([r['forecast_expense'] for r in fresh['history']],[Decimal('10'),Decimal('20'),Decimal('30')])
        self.assertNotEqual(source['fingerprint'],fresh['fingerprint'])
        page=self.client.get(self.url)
        self.assertTrue(page.context['stale'])
        self.assertIsNone(page.context.get('result'))
        self.assertEqual(compute_and_store(self.alice,fresh).estimate,old.estimate)

    def test_changed_transaction_coverage_or_configuration_hides_old_estimate(self):
        self.seed(3)
        result=compute_and_store(self.alice,snapshot(self.alice))
        change_month_status(self.alice,date(2026,9,1),'unknown')
        page=self.client.get(self.url)
        self.assertIsNone(page.context.get('result'))
        self.assertTrue(page.context['stale'])
        token=review_month(self.alice,date(2026,9,1))['review_token']
        change_month_status(self.alice,date(2026,9,1),'complete',review_token=token)
        compute_and_store(self.alice,snapshot(self.alice))
        from .forecasting import configuration
        changed=configuration()
        changed['engine_sha256']='changed-test-only'
        with patch('finance.forecasting.configuration',return_value=changed):
            self.assertIsNone(self.client.get(self.url).context.get('result'))
        Transaction.objects.filter(user=self.alice,date=date(2026,8,1)).update(description='Changed only in test')
        self.assertIsNone(self.client.get(self.url).context.get('result'))

    def test_year_and_vietnamese_midnight_new_target_invalidates(self):
        self.seed(3)
        compute_and_store(self.alice,snapshot(self.alice))
        with timezone.override('America/New_York'),patch('finance.coverage_calendar.timezone.now',return_value=datetime(2026,10,31,17,0,tzinfo=dt_timezone.utc)):
            source=snapshot(self.alice)
            self.assertEqual(source['target'],date(2026,11,1))
            self.assertEqual(source['history_count'],0)
            self.assertIsNone(self.client.get(self.url).context.get('result'))
        with patch('finance.coverage_calendar.timezone.now',return_value=datetime(2026,12,31,17,0,tzinfo=dt_timezone.utc)):
            source=snapshot(self.alice)
            self.assertEqual(source['target'],date(2027,1,1))
            self.assertEqual([r['month'] for r in source['required']],[date(2026,10,1),date(2026,11,1),date(2026,12,1)])

    def test_ml_36_months_real_fit_baseline_can_win_and_validation_is_six(self):
        self.seed(36,values=['0']*36)
        source=snapshot(self.alice)
        saved=compute_and_store(self.alice,source)
        self.assertEqual(saved.method,'mean3')
        self.assertEqual(saved.estimate_decimal,Decimal('0'))
        self.assertEqual(len(saved.details['candidates']),6)
        self.assertEqual(saved.details['validation_months'],[date(2026,m,1).isoformat() for m in range(4,10)])
        page=self.client.get(self.url)
        self.assertContains(page,'So sánh trên 6 tháng validation')
        self.assertContains(page,'KHÔNG PHẢI MACHINE LEARNING')
        self.assertEqual(len(page.context['comparisons']),6)

    def test_35_months_does_not_train_ml(self):
        self.seed(35,values=['0']*35)
        with patch('finance.forecast_math.ridge_predict') as ridge:
            saved=compute_and_store(self.alice,snapshot(self.alice))
        ridge.assert_not_called()
        self.assertEqual(saved.details['candidates'],[])

    def test_large_decimal_estimate_stored_and_reloaded_without_sqlite_rounding(self):
        months=self.seed(3,values=['999999999999999']*3)
        # Hai khoản hợp lệ/tháng tạo tổng 16 chữ số.
        Transaction.objects.bulk_create([Transaction(user=self.alice,category=self.food,kind='expense',
            amount=Decimal('999999999999999'),date=month) for month in months])
        for month in months:
            token=review_month(self.alice,month)['review_token']
            change_month_status(self.alice,month,'complete',review_token=token)
        saved=compute_and_store(self.alice,snapshot(self.alice))
        saved.refresh_from_db()
        self.assertEqual(saved.estimate,'1999999999999998')
        self.assertEqual(saved.estimate_decimal,Decimal('1999999999999998'))
        self.assertContains(self.client.get(self.url),'1.999.999.999.999.998 ₫')

    def test_ml_error_is_explicit_and_no_silent_baseline_result(self):
        self.seed(36,values=['0']*36)
        with patch('finance.forecast_math.ridge_predict',side_effect=OSError('DLL test only')):
            page=self.client.post(self.url)
        self.assertEqual(page.status_code,503)
        self.assertContains(page,'Không chạy được bước ML thử nghiệm',status_code=503)
        self.assertIsNone(page.context.get('result'))
        self.assertFalse(ForecastResult.objects.exists())

    def test_changed_data_during_computation_is_not_published(self):
        self.seed(3)
        source=snapshot(self.alice)
        Transaction.objects.filter(pk=self.alice_row.pk).update(description='Updated current month in test')
        with self.assertRaises(StaleForecast):
            compute_and_store(self.alice,source)
        self.assertFalse(ForecastResult.objects.exists())

    def test_revision_and_cache_rollback_and_other_account_edit(self):
        self.seed(3)
        compute_and_store(self.alice,snapshot(self.alice))
        before=snapshot(self.alice)['fingerprint']
        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                self.alice_row.description='not committed'
                self.alice_row.save()
                raise RuntimeError('test rollback')
        self.assertEqual(snapshot(self.alice)['fingerprint'],before)
        Transaction.objects.filter(pk=self.bob_row.pk).update(description='other account edit')
        self.assertEqual(snapshot(self.alice)['fingerprint'],before)
        self.assertIsNotNone(self.client.get(self.url).context.get('result'))

    def test_csv_preview_and_failure_keep_cache_but_success_invalidates(self):
        self.seed(3)
        compute_and_store(self.alice,snapshot(self.alice))
        before=snapshot(self.alice)['fingerprint']
        raw=csv_bytes([['2026-09-15','expense','12',self.food.name,'CSV test only']])
        batch=stage_csv(raw,self.alice,inspect_csv(raw,self.alice))
        self.assertEqual(snapshot(self.alice)['fingerprint'],before)
        original=Transaction.objects.bulk_create
        def fail(objects,**kwargs):
            original(objects,**kwargs)
            raise IntegrityError('test rollback after insert')
        with patch('finance.csv_import.Transaction.objects.bulk_create',side_effect=fail),self.assertRaises(IntegrityError):
            confirm_batch(batch.pk,self.alice)
        self.assertEqual(snapshot(self.alice)['fingerprint'],before)
        self.assertIsNotNone(self.client.get(self.url).context.get('result'))
        confirm_batch(batch.pk,self.alice)
        self.assertIsNone(self.client.get(self.url).context.get('result'))

    def test_login_csrf_and_get_never_trains(self):
        secure=Client(enforce_csrf_checks=True)
        secure.force_login(self.alice)
        self.assertEqual(secure.post(self.url).status_code,403)
        self.seed(3)
        page=secure.get(self.url)
        csrf=page.cookies['csrftoken'].value
        self.assertEqual(secure.post(self.url,{},HTTP_X_CSRFTOKEN=csrf).status_code,302)
        with patch('finance.forecast_views.compute_and_store') as compute:
            self.client.get(self.url)
            compute.assert_not_called()
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code,302)
        self.assertEqual(self.client.post(self.url).status_code,302)

    def test_user_cascade_signal_does_not_recreate_version_for_deleted_account(self):
        from .signals import transaction_deleted
        with patch('finance.signals.reset_months') as reset:
            transaction_deleted(Transaction,instance=self.alice_row,using='default',origin=self.alice)
            reset.assert_not_called()
