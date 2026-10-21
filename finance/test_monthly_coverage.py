import io
from datetime import date, datetime, timezone as dt_timezone
from decimal import Decimal
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.db.models import F
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from .coverage import change_month_status, monthly_history, review_month
from .coverage_calendar import current_month
from .csv_import import ImportProblem, confirm_batch, inspect_csv, stage_csv
from .models import CsvImportBatch, CsvImportReceipt, Kind, MonthlyCoverage, Transaction
from .test_csv_import import csv_bytes
from .tests import FinanceCase


class MonthlyCoverageTests(FinanceCase):
    month = date(2026, 9, 1)
    older = date(2026, 8, 1)

    def setUp(self):
        super().setUp()
        clock = patch('finance.coverage_calendar.timezone.now', return_value=datetime(2026, 10, 20, 10, tzinfo=dt_timezone.utc))
        clock.start()
        self.addCleanup(clock.stop)

    def record(self, month=None, **changes):
        data = {'user': self.alice, 'kind': 'expense', 'category': self.food, 'amount': Decimal('123'),
                'date': month or self.month, 'description': 'Chỉ trong test DB'}
        data.update(changes)
        return Transaction.objects.create(**data)

    def mark(self, month=None, user=None, status=MonthlyCoverage.Status.COMPLETE):
        user = user or self.alice
        month = month or self.month
        token = review_month(user, month)['review_token'] if status == MonthlyCoverage.Status.COMPLETE else ''
        return change_month_status(user, month, status, review_token=token, confirm_no_expense=True)

    def assert_unknown(self, month=None, user=None):
        row = MonthlyCoverage.objects.get(user=user or self.alice, month=month or self.month)
        self.assertEqual(row.status, 'unknown')
        self.assertIsNone(row.confirmed_at)

    def test_default_unknown_and_forecast_missing_without_creating_status_rows(self):
        rows = monthly_history(self.alice, self.older, self.month)
        self.assertEqual([r['month'] for r in rows], [self.older, self.month])
        self.assertTrue(all(r['status'] == 'unknown' and r['forecast_expense'] is None for r in rows))
        self.assertEqual(MonthlyCoverage.objects.count(), 0)

    def test_confirm_zero_expense_requires_explicit_acknowledgement(self):
        # Có thu nhập vẫn phải xác nhận rõ không có chi.
        self.record(kind='income', category=self.salary)
        token = review_month(self.alice, self.month)['review_token']
        with self.assertRaisesMessage(ValidationError, 'Bạn xác nhận tháng này không có khoản chi?'):
            change_month_status(self.alice, self.month, 'complete', review_token=token)
        self.assertFalse(MonthlyCoverage.objects.exists())
        row = change_month_status(self.alice, self.month, 'complete', review_token=token, confirm_no_expense=True)
        self.assertIsNotNone(row.confirmed_at)
        item = monthly_history(self.alice, self.month, self.month)[0]
        self.assertEqual(item['forecast_expense'], Decimal('0'))
        self.assertIsInstance(item['forecast_expense'], Decimal)
        self.assertEqual(item['transaction_count'], 1)

    def test_incomplete_cancel_and_timestamp_cleared(self):
        self.mark()
        self.mark(status='incomplete')
        row = MonthlyCoverage.objects.get(user=self.alice, month=self.month)
        self.assertEqual(row.status, 'incomplete')
        self.assertIsNone(row.confirmed_at)
        self.assertIsNone(monthly_history(self.alice, self.month, self.month)[0]['forecast_expense'])
        self.mark()
        change_month_status(self.alice, self.month, 'unknown')
        self.assert_unknown()
        self.assertEqual(MonthlyCoverage.objects.count(), 1)

    def test_current_and_future_cannot_be_confirmed_and_not_returned(self):
        for month in [date(2026, 10, 1), date(2026, 11, 1)]:
            with self.subTest(month=month):
                with self.assertRaises(ValidationError):
                    review_month(self.alice, month)
                with self.assertRaises(ValidationError):
                    change_month_status(self.alice, month, 'complete', review_token='forged', confirm_no_expense=True)
                with self.assertRaises(ValidationError):
                    MonthlyCoverage.objects.create(user=self.alice, month=month, status='complete', confirmed_at=timezone.now())
                url = reverse('finance:coverage_confirm', args=[month.year, month.month])
                self.assertEqual(self.client.get(url).status_code, 400)
                self.assertEqual(self.client.post(url, {'confirm_no_expense': 'on', 'review_token':'forged'}).status_code, 400)
        rows = monthly_history(self.alice, self.month, date(2026, 12, 1))
        self.assertEqual([r['month'] for r in rows], [self.month])

    def test_boundary_is_vietnamese_time_even_with_other_active_timezone(self):
        with timezone.override('America/New_York'):
            with patch('finance.coverage_calendar.timezone.now', return_value=datetime(2026, 9, 30, 16, 59, tzinfo=dt_timezone.utc)):
                self.assertEqual(current_month(), date(2026, 9, 1))
                with self.assertRaises(ValidationError):
                    review_month(self.alice, self.month)
            with patch('finance.coverage_calendar.timezone.now', return_value=datetime(2026, 9, 30, 17, 0, tzinfo=dt_timezone.utc)):
                self.assertEqual(current_month(), date(2026, 10, 1))
                self.mark()

    def test_unique_user_month_and_database_constraints(self):
        self.mark()
        self.mark(user=self.bob)
        invalid = [dict(month=self.month), dict(month=date(2026, 8, 15)),
                   dict(month=self.older, status='other'), dict(month=self.older, status='complete'),
                   dict(month=self.older, status='unknown', confirmed_at=timezone.now())]
        for values in invalid:
            with self.subTest(values=values), self.assertRaises(IntegrityError), transaction.atomic():
                MonthlyCoverage.objects.bulk_create([MonthlyCoverage(user=self.alice, **values)])

    def test_account_isolation_totals_and_actions(self):
        self.record(amount=Decimal('123456'))
        self.record(user=self.bob, category=self.bob_category, amount=Decimal('987654'))
        self.mark(user=self.bob)
        item = monthly_history(self.alice, self.month, self.month)[0]
        self.assertEqual(item['recorded_expense'], Decimal('123456'))
        self.assertEqual(item['transaction_count'], 1)
        self.assertEqual(item['status'], 'unknown')
        url = reverse('finance:coverage_status', args=[2026, 9])
        self.client.post(url, {'status':'incomplete','user_id':self.bob.pk})
        self.assertEqual(MonthlyCoverage.objects.get(user=self.bob, month=self.month).status, 'complete')
        page = self.client.get(reverse('finance:monthly_history'), {'year':2026})
        self.assertContains(page, '123.456 ₫')
        self.assertNotContains(page, '987.654')

    def test_confirmation_token_cannot_cross_account_or_month(self):
        token = review_month(self.bob, self.month)['review_token']
        with self.assertRaises(ValidationError):
            change_month_status(self.alice, self.month, 'complete', review_token=token, confirm_no_expense=True)
        token = review_month(self.alice, self.older)['review_token']
        with self.assertRaises(ValidationError):
            change_month_status(self.alice, self.month, 'complete', review_token=token, confirm_no_expense=True)

    def test_stale_review_does_not_restore_confirmation_after_edit(self):
        row = self.record()
        token = review_month(self.alice, self.month)['review_token']
        self.mark()
        row.description = 'Đã thay đổi trong test'
        row.save()
        with self.assertRaisesMessage(ValidationError, 'Giao dịch đã thay đổi'):
            change_month_status(self.alice, self.month, 'complete', review_token=token)
        self.assert_unknown()

    def test_crud_model_create_edit_delete_resets_even_income_only_change(self):
        for operation in ['create', 'edit', 'delete']:
            with self.subTest(operation=operation):
                row = self.record()
                self.mark()
                if operation == 'create':
                    self.record(kind='income', category=self.salary)
                elif operation == 'edit':
                    row.amount = Decimal('456')
                    row.save()
                else:
                    row.delete()
                self.assert_unknown()

    def test_date_moved_resets_both_months_but_not_other_user_or_month(self):
        row = self.record()
        self.mark()
        self.mark(self.older)
        self.mark(date(2026, 7, 1))
        self.mark(user=self.bob)
        row.date = date(2026, 8, 20)
        row.save()
        self.assert_unknown()
        self.assert_unknown(self.older)
        self.assertEqual(MonthlyCoverage.objects.get(user=self.alice, month=date(2026, 7, 1)).status, 'complete')
        self.assertEqual(MonthlyCoverage.objects.get(user=self.bob, month=self.month).status, 'complete')

    def test_queryset_update_bulk_update_and_queryset_delete_are_covered(self):
        row = self.record()
        for operation in ['update', 'bulk_update', 'delete']:
            with self.subTest(operation=operation):
                self.mark()
                if operation == 'update':
                    Transaction.objects.filter(pk=row.pk).update(amount=F('amount') + 1)
                elif operation == 'bulk_update':
                    row.description = 'Sửa theo lô'
                    Transaction.objects.bulk_update([row], ['description'])
                else:
                    Transaction.objects.filter(pk=row.pk).delete()
                self.assert_unknown()

    def test_queryset_date_update_resets_old_and_new_and_save_update_fields_uses_saved_date(self):
        row = self.record()
        self.mark()
        self.mark(self.older)
        Transaction.objects.filter(pk=row.pk).update(date=date(2026, 8, 20))
        self.assert_unknown()
        self.assert_unknown(self.older)
        self.mark()
        self.mark(self.older)
        row.date = date(2026, 7, 20)  # không nằm trong update_fields, không được lưu
        row.description = 'Chỉ đổi mô tả'
        row.save(update_fields=['description'])
        self.assert_unknown(self.older)
        self.assertEqual(MonthlyCoverage.objects.get(user=self.alice, month=self.month).status, 'complete')

    def test_bulk_create_resets_all_affected_months(self):
        self.mark()
        self.mark(self.older, status='incomplete')
        Transaction.objects.bulk_create([
            Transaction(user=self.alice, category=self.food, kind='expense', amount=Decimal('1'), date=day)
            for day in [self.month, self.older]])
        self.assert_unknown()
        self.assert_unknown(self.older)

    def test_failed_model_validation_and_database_update_keep_status(self):
        row = self.record()
        saved = self.mark()
        row.amount = Decimal('0')
        with self.assertRaises(ValidationError):
            row.save()
        with self.assertRaises(IntegrityError), transaction.atomic():
            Transaction.objects.filter(pk=row.pk).update(amount=Decimal('0'))
        saved.refresh_from_db()
        self.assertEqual(saved.status, 'complete')
        self.assertIsNotNone(saved.confirmed_at)

    def test_outer_rollback_restores_transaction_and_coverage_for_save_delete_bulk(self):
        row = self.record()
        for operation in ['save', 'delete', 'bulk_create']:
            saved = self.mark()
            before = Transaction.objects.count()
            with self.subTest(operation=operation), self.assertRaises(RuntimeError):
                with transaction.atomic():
                    if operation == 'save':
                        row.description = 'Chưa được commit'
                        row.save()
                    elif operation == 'delete':
                        Transaction.objects.filter(pk=row.pk).delete()
                    else:
                        Transaction.objects.bulk_create([Transaction(user=self.alice, category=self.food, kind='expense', amount=Decimal('1'), date=self.month)])
                    self.assert_unknown()
                    raise RuntimeError('test rollback')
            saved.refresh_from_db()
            self.assertEqual(saved.status, 'complete')
            self.assertEqual(Transaction.objects.count(), before)
            row.refresh_from_db()

    def test_reset_failure_rolls_back_save_delete_and_bulk_insert(self):
        row = self.record()
        for target, operation in [('finance.models.reset_months', 'save'), ('finance.signals.reset_months', 'delete'), ('finance.transaction_queries.reset_months', 'bulk_create')]:
            saved = self.mark()
            with self.subTest(operation=operation), patch(target, side_effect=RuntimeError('test-only state failure')), self.assertRaises(RuntimeError):
                # Collector.delete dùng atomic(savepoint=False): savepoint ngoài
                # giữ test DB dùng tiếp được sau lỗi tín hiệu được chủ động gây ra.
                with transaction.atomic():
                    if operation == 'save':
                        row.description = 'Không được lưu'
                        row.save()
                    elif operation == 'delete':
                        Transaction.objects.filter(pk=row.pk).delete()
                    else:
                        Transaction.objects.bulk_create([Transaction(user=self.alice, category=self.food, kind='expense', amount=Decimal('1'), date=self.month)])
            row.refresh_from_db()
            self.assertEqual(row.description, 'Chỉ trong test DB')
            self.assertEqual(Transaction.objects.filter(user=self.alice, date__month=9).count(), 1)
            saved.refresh_from_db()
            self.assertEqual(saved.status, 'complete')

    def csv_stage(self):
        raw = csv_bytes([['2026-09-10','expense','100',self.food.name,'CSV test'],
                         ['2026-08-10','income','200',self.salary.name,'CSV test income']])
        return stage_csv(raw, self.alice, inspect_csv(raw, self.alice))

    def test_csv_preview_does_not_confirm_and_success_resets_affected_months_only(self):
        self.mark()
        self.mark(self.older)
        self.mark(date(2026, 7, 1))
        self.mark(user=self.bob)
        batch = self.csv_stage()
        self.assertEqual(MonthlyCoverage.objects.get(user=self.alice, month=self.month).status, 'complete')
        self.assertEqual(confirm_batch(batch.pk, self.alice), 2)
        self.assert_unknown()
        self.assert_unknown(self.older)
        self.assertEqual(MonthlyCoverage.objects.get(user=self.alice, month=date(2026, 7, 1)).status, 'complete')
        self.assertEqual(MonthlyCoverage.objects.get(user=self.bob, month=self.month).status, 'complete')
        self.assertIsNone(monthly_history(self.alice, self.month, self.month)[0]['forecast_expense'])

    def test_failed_csv_import_preserves_status_timestamp_and_rows(self):
        saved = self.mark()
        self.mark(self.older)
        batch = self.csv_stage()
        original_bulk = Transaction.objects.bulk_create
        def fail_after_bulk(objects, **kwargs):
            original_bulk(objects, **kwargs)
            self.assert_unknown()
            raise IntegrityError('test-only post-insert failure')
        before = Transaction.objects.count()
        stamp = saved.confirmed_at
        with patch('finance.csv_import.Transaction.objects.bulk_create', side_effect=fail_after_bulk), self.assertRaises(IntegrityError):
            confirm_batch(batch.pk, self.alice)
        self.assertEqual(Transaction.objects.count(), before)
        self.assertFalse(CsvImportReceipt.objects.exists())
        saved.refresh_from_db()
        self.assertEqual((saved.status, saved.confirmed_at), ('complete', stamp))
        self.assertEqual(MonthlyCoverage.objects.get(user=self.alice, month=self.older).status, 'complete')
        batch.refresh_from_db()
        self.assertEqual(batch.status, 'pending')

    def test_invalid_csv_never_changes_coverage(self):
        self.mark()
        bad = csv_bytes([['2026-09-10','expense','0',self.food.name,'test']])
        response = self.client.post(reverse('finance:csv_upload'), {'file':SimpleUploadedFile('test.csv',bad)})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(MonthlyCoverage.objects.get(user=self.alice, month=self.month).status, 'complete')

    def test_repeated_and_expired_csv_confirmation_keep_reconfirmed_months(self):
        batch = self.csv_stage()
        confirm_batch(batch.pk, self.alice)
        self.mark()
        self.mark(self.older)
        with self.assertRaises(ImportProblem):
            confirm_batch(batch.pk, self.alice)
        fresh_raw = csv_bytes([['2026-09-11','expense','12',self.food.name,'Expired test']])
        expired = stage_csv(fresh_raw, self.alice, inspect_csv(fresh_raw, self.alice))
        CsvImportBatch.objects.filter(pk=expired.pk).update(expires_at=datetime(2026,10,19,tzinfo=dt_timezone.utc))
        with self.assertRaises(ImportProblem):
            confirm_batch(expired.pk, self.alice)
        self.assertEqual(list(MonthlyCoverage.objects.filter(user=self.alice,month__in=[self.older,self.month]).values_list('status',flat=True)),['complete','complete'])

    def test_consecutive_calendar_gaps_decimal_totals_and_year_transition(self):
        self.record(month=date(2025, 12, 31), amount=Decimal('999999999999999'))
        self.record(month=date(2026, 2, 1), amount=Decimal('999999999999999'))
        self.record(month=date(2026, 2, 28), amount=Decimal('999999999999999'))
        self.mark(date(2025, 12, 1))
        self.mark(date(2026, 2, 1), status='incomplete')
        rows = monthly_history(self.alice, date(2025, 12, 1), date(2026, 3, 1))
        self.assertEqual([r['month'] for r in rows], [date(2025,12,1),date(2026,1,1),date(2026,2,1),date(2026,3,1)])
        self.assertEqual([r['forecast_expense'] for r in rows], [Decimal('999999999999999'),None,None,None])
        self.assertEqual(rows[2]['recorded_expense'], Decimal('1999999999999998'))
        self.mark(date(2026, 1, 1))
        self.assertEqual(monthly_history(self.alice,date(2026,1,1),date(2026,1,1))[0]['forecast_expense'], Decimal('0'))

    def test_web_crud_resets_and_moving_date_resets_two_months(self):
        row = self.record()
        self.mark()
        response = self.client.post(reverse('finance:transaction_create'), self.payload(date='2026-09-15'))
        self.assertEqual(response.status_code, 302)
        self.assert_unknown()
        self.mark()
        self.mark(self.older)
        response = self.client.post(reverse('finance:transaction_edit',args=[row.pk]), self.payload(date='2026-08-15'))
        self.assertEqual(response.status_code, 302)
        self.assert_unknown()
        self.assert_unknown(self.older)
        self.mark(self.older)
        self.assertEqual(self.client.post(reverse('finance:transaction_delete',args=[row.pk])).status_code,302)
        self.assert_unknown(self.older)

    def test_history_confirm_cancel_csrf_login_and_bad_year(self):
        url = reverse('finance:coverage_confirm', args=[2026,9])
        status_url = reverse('finance:coverage_status', args=[2026,9])
        page = self.client.get(url)
        self.assertContains(page, 'Bạn xác nhận tháng này không có khoản chi?')
        self.assertFalse(MonthlyCoverage.objects.exists())
        token = page.context['form'].initial['review_token']
        self.assertEqual(self.client.post(url, {'review_token':token}).status_code,200)
        self.assertFalse(MonthlyCoverage.objects.exists())
        self.assertEqual(self.client.post(url, {'review_token':token,'confirm_no_expense':'on'}).status_code,302)
        self.assertEqual(self.client.get(status_url).status_code,405)
        self.assertEqual(self.client.post(status_url, {'status':'complete'}).status_code,400)
        self.assertEqual(self.client.post(status_url, {'status':'unknown'}).status_code,302)
        self.assert_unknown()
        secure = Client(enforce_csrf_checks=True)
        secure.force_login(self.alice)
        self.assertEqual(secure.post(url, {}).status_code,403)
        self.assertEqual(secure.post(status_url, {'status':'unknown'}).status_code,403)
        for year in ['bad','0','10000']:
            response = self.client.get(reverse('finance:monthly_history'),{'year':year})
            self.assertEqual(response.status_code,200)
            self.assertTrue(response.context['year_form'].errors)
        self.assertEqual(self.client.get(reverse('finance:coverage_confirm',args=[2026,13])).status_code,404)
        self.assertEqual(self.client.get(reverse('finance:monthly_history'),{'year':2027}).context['rows'],[])
        self.client.logout()
        for route in [reverse('finance:monthly_history'),url]:
            self.assertEqual(self.client.get(route).status_code,302)
        self.assertEqual(self.client.post(status_url, {'status':'unknown'}).status_code,302)
