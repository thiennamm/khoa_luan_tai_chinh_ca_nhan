import hashlib
import io
import csv
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal
from threading import Barrier
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.db import IntegrityError, OperationalError, close_old_connections
from django.test import Client, TransactionTestCase
from django.urls import reverse
from django.utils import timezone

from .csv_import import (HEADER, MAX_BYTES, ImportProblem, cleanup_batches, confirm_batch,
                         inspect_csv, stage_csv)
from .models import Category, CsvImportBatch, CsvImportReceipt, Transaction
from .tests import FinanceCase


def csv_bytes(rows, header=HEADER, bom=False):
    stream = io.StringIO(newline='')
    writer = csv.writer(stream)
    writer.writerow(header)
    writer.writerows(rows)
    return stream.getvalue().encode('utf-8-sig' if bom else 'utf-8')


class CsvImportTests(FinanceCase):
    def setUp(self):
        super().setUp()
        self.url = reverse('finance:csv_upload')

    def row(self, **changes):
        values = dict(date='2026-10-20', kind='expense', amount='123456',
                      category=self.food.name, description='Ghi chú CSV')
        values.update(changes)
        return [values[name] for name in HEADER]

    def upload(self, raw, name='records.csv', content_type='text/csv'):
        return self.client.post(self.url, {'file': SimpleUploadedFile(name, raw, content_type=content_type)})

    def stage(self, rows=None, bom=False):
        raw = csv_bytes(rows if rows is not None else [self.row()], bom=bom)
        return stage_csv(raw, self.alice, inspect_csv(raw, self.alice))

    def test_header_only_template_and_format_help(self):
        response = self.client.get(reverse('finance:csv_template'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode('utf-8-sig'), ','.join(HEADER) + '\r\n')
        self.assertEqual(len(list(csv.reader(io.StringIO(response.content.decode('utf-8'))))), 1)
        page = self.client.get(self.url)
        for text in ['UTF-8', 'BOM', '2 MiB', '5.000', 'YYYY-MM-DD', 'user_id']:
            self.assertContains(page, text)

    def test_bom_upload_preview_confirm_and_no_client_payload(self):
        before = list(Transaction.objects.order_by('pk').values())
        raw = csv_bytes([self.row(), self.row(kind='income', category=self.salary.name, amount='5000000', description='')], bom=True)
        response = self.upload(raw)
        self.assertEqual(response.status_code, 302)
        batch = CsvImportBatch.objects.get()
        self.assertEqual(batch.sha256, hashlib.sha256(raw).hexdigest())
        self.assertEqual(bytes(batch.raw), raw)
        self.assertEqual(list(Transaction.objects.order_by('pk').values()), before)
        preview = self.client.get(response.url)
        self.assertEqual(preview.context['inspection'].income, Decimal('5000000'))
        self.assertEqual(preview.context['inspection'].expense, Decimal('123456'))
        self.assertTrue(preview.context['can_confirm'])
        self.assertContains(preview, 'Xác nhận nhập toàn bộ 2 giao dịch')
        self.assertNotContains(preview, 'name="description"')
        self.assertNotIn('Ghi chú CSV', str(dict(self.client.session)))
        confirm = self.client.post(reverse('finance:csv_confirm', args=[batch.pk]),
            {'user_id': self.bob.pk, 'amount': '-99', 'category': self.bob_category.pk})
        self.assertEqual(confirm.status_code, 302)
        self.assertEqual(Transaction.objects.filter(user=self.alice).count(), 3)
        self.assertEqual(Transaction.objects.filter(user=self.bob).count(), 1)
        self.assertEqual(list(Transaction.objects.filter(pk__in=[r['id'] for r in before]).order_by('pk').values()), before)
        batch.refresh_from_db()
        self.assertEqual(bytes(batch.raw), b'')
        self.assertEqual(batch.category_bindings, [])
        self.assertEqual(batch.status, 'completed')
        self.assertEqual(CsvImportReceipt.objects.get().transaction_count, 2)
        self.assertContains(self.client.get(confirm.url), 'Đã thêm <strong>2</strong>', html=False)

    def test_content_not_filename_or_mime_determines_csv(self):
        self.assertEqual(self.upload(csv_bytes([self.row()]), 'blob.dat', 'application/octet-stream').status_code, 302)
        response = self.upload(b'%PDF-1.7 binary content', 'pretend.csv', 'text/csv')
        self.assertContains(response, 'Header phải đúng')
        self.assertIsNone(response.context.get('batch'))

    def test_invalid_encoding_binary_empty_header_and_structure(self):
        cases = [b'', b'\xff\xfeabc', b'date\x00,kind', csv_bytes([]),
                 csv_bytes([self.row()], header=HEADER + ['user_id']),
                 csv_bytes([self.row()[:-1]]), csv_bytes([self.row() + ['99']]),
                 b'date,kind,amount,category,description\n"unterminated',
                 b'date;kind;amount;category;description\nanything']
        for raw in cases:
            with self.subTest(raw=raw[:30]):
                response = self.upload(raw)
                self.assertEqual(response.status_code, 200)
                inspection = response.context['inspection']
                self.assertTrue(response.context['form'].errors or (inspection and inspection.error_count))
                self.assertNotContains(response, 'Xác nhận nhập toàn bộ')
        self.assertEqual(CsvImportBatch.objects.count(), 0)

    def test_invalid_money_dates_kinds_categories_and_description(self):
        cases = [('amount', x) for x in ['0', '-1', '1.5', '1,000', '1e3', 'NaN', 'Infinity', '+1', ' 1', '１２３', '1000000000000000', '']]
        cases += [('date', x) for x in ['2026-2-01', '2026-02-30', '0000-01-01', '2026-10-20T00:00', '']]
        cases += [('kind', x) for x in ['transfer', 'Income', ' expense', '']]
        cases += [('category', self.bob_category.name), ('category', self.salary.name), ('category', 'Thiếu'),
                  ('category', ' ' + self.food.name), ('description', 'x' * 501)]
        for field, value in cases:
            with self.subTest(field=field, value=value[:35]):
                result = inspect_csv(csv_bytes([self.row(**{field: value})]), self.alice)
                self.assertFalse(result.valid)
                self.assertEqual(result.errors[0]['line'], 2)
        self.assertEqual(Transaction.objects.count(), 2)

    def test_blank_lines_are_errors_and_line_number_uses_physical_start(self):
        raw = csv_bytes([self.row(description='Hai\ndòng'), self.row(date='bad')])
        result = inspect_csv(raw, self.alice)
        self.assertEqual(result.errors[0]['line'], 4)
        result = inspect_csv(csv_bytes([self.row()]) + b'\n', self.alice)
        self.assertEqual(result.errors[0]['line'], 3)

    def test_upload_and_row_limits(self):
        raw = b'x' * (MAX_BYTES + 1)
        self.assertFalse(inspect_csv(raw, self.alice).valid)
        response = self.upload(raw)
        self.assertContains(response, 'vượt giới hạn 2 MiB')
        self.assertEqual(CsvImportBatch.objects.count(), 0)
        result = inspect_csv(csv_bytes([self.row()] * 5000), self.alice)
        self.assertTrue(result.valid)
        self.assertEqual(len(result.rows), 5000)
        result = inspect_csv(csv_bytes([self.row()] * 5001), self.alice)
        self.assertFalse(result.valid)
        self.assertEqual(result.errors[-1]['line'], 5002)

    def test_decimal_totals_and_preview_cap(self):
        result = inspect_csv(csv_bytes([self.row(amount='999999999999999')] * 21), self.alice)
        self.assertEqual(result.expense, Decimal('20999999999999979'))
        self.assertIsInstance(result.expense, Decimal)
        self.assertEqual(len(result.sample), 20)

    def test_maximum_5000_rows_can_be_confirmed_without_dropping_duplicates(self):
        batch = self.stage([self.row()] * 5000)
        self.assertEqual(confirm_batch(batch.pk, self.alice), 5000)
        self.assertEqual(Transaction.objects.filter(user=self.alice, description='Ghi chú CSV').count(), 5000)
        self.assertEqual(CsvImportReceipt.objects.get(batch=batch).transaction_count, 5000)

    def test_mixed_valid_and_invalid_never_stage_or_confirm(self):
        response = self.upload(csv_bytes([self.row(), self.row(amount='0')]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['inspection'].rows), 1)
        self.assertNotContains(response, 'Xác nhận nhập toàn bộ')
        self.assertEqual(CsvImportBatch.objects.count(), 0)
        self.assertEqual(Transaction.objects.count(), 2)

    def test_ambiguous_casefold_category_is_not_chosen(self):
        # SQLite iexact không đồng nhất mọi chữ Unicode; parser phải phát hiện nhiều kết quả.
        Category.objects.create(user=self.alice, kind='expense', name='Straße')
        Category.objects.create(user=self.alice, kind='expense', name='STRASSE')
        result = inspect_csv(csv_bytes([self.row(category='strasse')]), self.alice)
        self.assertFalse(result.valid)
        self.assertIn('không xác định duy nhất', result.errors[0]['message'])

    def test_duplicate_rows_warn_but_all_imported(self):
        batch = self.stage([self.row(), self.row()])
        response = self.client.get(reverse('finance:csv_preview', args=[batch.pk]))
        self.assertEqual(response.context['inspection'].warning_count, 1)
        self.assertTrue(response.context['can_confirm'])
        self.assertEqual(confirm_batch(batch.pk, self.alice), 2)
        self.assertEqual(Transaction.objects.filter(description='Ghi chú CSV').count(), 2)

    def test_duplicate_existing_transaction_warns_not_drops(self):
        row = self.row(date='2026-10-01', amount='125000', description=self.alice_row.description)
        result = inspect_csv(csv_bytes([row]), self.alice)
        self.assertEqual(result.warning_count, 1)
        self.assertTrue(result.valid)

    def test_same_file_and_repeated_confirmation_blocked(self):
        batch = self.stage()
        second_batch = self.stage()  # hai preview trước khi lô đầu thành công
        url = reverse('finance:csv_confirm', args=[batch.pk])
        self.assertEqual(self.client.post(url).status_code, 302)
        self.assertEqual(self.client.post(url).status_code, 409)
        self.assertEqual(self.client.post(reverse('finance:csv_confirm', args=[second_batch.pk])).status_code, 409)
        response = self.upload(csv_bytes([self.row()]))
        self.assertContains(response, 'cùng SHA-256 đã được nhập thành công')
        self.assertEqual(Transaction.objects.count(), 3)
        self.assertEqual(CsvImportReceipt.objects.count(), 1)

    def test_receipt_is_per_account(self):
        Category.objects.create(user=self.bob, kind='expense', name=self.food.name)
        batch = self.stage()
        raw = bytes(batch.raw)
        confirm_batch(batch.pk, self.alice)
        other = stage_csv(raw, self.bob, inspect_csv(raw, self.bob))
        confirm_batch(other.pk, self.bob)
        self.assertEqual(CsvImportReceipt.objects.filter(sha256=batch.sha256).count(), 2)

    def test_successful_hash_reported_even_after_category_renamed(self):
        batch = self.stage()
        raw = bytes(batch.raw)
        confirm_batch(batch.pk, self.alice)
        self.food.name = 'Tên đã đổi'
        self.food.save()
        response = self.upload(raw)
        self.assertContains(response, 'cùng SHA-256 đã được nhập thành công')
        self.assertEqual(Transaction.objects.count(), 3)

    def test_other_user_cannot_view_or_confirm_batch(self):
        batch = self.stage()
        self.client.force_login(self.bob)
        self.assertEqual(self.client.get(reverse('finance:csv_preview', args=[batch.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse('finance:csv_confirm', args=[batch.pk])).status_code, 404)
        with self.assertRaises(ImportProblem):
            confirm_batch(batch.pk, self.bob)
        self.assertEqual(Transaction.objects.count(), 2)

    def test_expiry_no_payload_exposed_and_cleanup(self):
        batch = self.stage()
        CsvImportBatch.objects.filter(pk=batch.pk).update(expires_at=timezone.now()-timedelta(seconds=1))
        response = self.client.get(reverse('finance:csv_preview', args=[batch.pk]))
        self.assertContains(response, 'hết hạn', status_code=410)
        self.assertNotContains(response, 'Ghi chú CSV', status_code=410)
        self.assertEqual(self.client.post(reverse('finance:csv_confirm', args=[batch.pk])).status_code, 409)
        self.assertEqual(cleanup_batches(self.bob), 0)
        call_command('cleanup_csv_imports', stdout=io.StringIO())
        self.assertFalse(CsvImportBatch.objects.exists())
        self.assertEqual(Transaction.objects.count(), 2)

    def test_cleanup_keeps_success_hash_and_transactions(self):
        batch = self.stage()
        raw = bytes(batch.raw)
        confirm_batch(batch.pk, self.alice)
        CsvImportBatch.objects.filter(pk=batch.pk).update(expires_at=timezone.now()-timedelta(seconds=1))
        self.assertEqual(cleanup_batches(), 1)
        receipt = CsvImportReceipt.objects.get()
        self.assertIsNone(receipt.batch_id)
        self.assertEqual(Transaction.objects.count(), 3)
        with self.assertRaises(ImportProblem):
            stage_csv(raw, self.alice, inspect_csv(raw, self.alice))

    def test_recheck_category_owner_kind_name_and_binding(self):
        for change in [{'user_id': self.bob.pk}, {'kind': 'income'}, {'name': 'Đổi tên'}]:
            with self.subTest(change=change):
                batch = self.stage()
                Category.objects.filter(pk=self.food.pk).update(**change)
                with self.assertRaises(ImportProblem):
                    confirm_batch(batch.pk, self.alice)
                Category.objects.filter(pk=self.food.pk).update(user=self.alice, kind='expense', name=self.food.name)
        batch = self.stage()
        # Danh mục cũ đổi tên, danh mục mới cùng tên không được thay thế âm thầm.
        Category.objects.filter(pk=self.food.pk).update(name='Tên khác')
        Category.objects.create(user=self.alice, name=self.food.name, kind='expense')
        with self.assertRaises(ImportProblem):
            confirm_batch(batch.pk, self.alice)
        self.assertEqual(Transaction.objects.count(), 2)

    def test_hash_tampering_and_category_deleted_rejected(self):
        category = Category.objects.create(user=self.alice, name='Dùng tạm', kind='expense')
        batch = self.stage([self.row(category=category.name)])
        category.delete()
        with self.assertRaises(ImportProblem):
            confirm_batch(batch.pk, self.alice)
        batch = self.stage()
        CsvImportBatch.objects.filter(pk=batch.pk).update(raw=b'modified')
        with self.assertRaises(ImportProblem):
            confirm_batch(batch.pk, self.alice)

    def test_rollback_restores_pending_payload_receipt_and_partial_inserts(self):
        batch = self.stage([self.row(), self.row()])
        original = bytes(batch.raw)
        def fail_after_one(objects, **kwargs):
            objects[0].save()
            raise IntegrityError('test-only simulated insertion failure')
        with patch('finance.csv_import.Transaction.objects.bulk_create', side_effect=fail_after_one):
            response = self.client.post(reverse('finance:csv_confirm', args=[batch.pk]))
        self.assertEqual(response.status_code, 409)
        self.assertEqual(Transaction.objects.count(), 2)
        self.assertEqual(CsvImportReceipt.objects.count(), 0)
        batch.refresh_from_db()
        self.assertEqual(batch.status, 'pending')
        self.assertEqual(bytes(batch.raw), original)
        self.assertEqual(confirm_batch(batch.pk, self.alice), 2)

    def test_auth_csrf_post_only_and_html_escape(self):
        batch = self.stage([self.row(description='<script>alert(1)</script>')])
        preview_url = reverse('finance:csv_preview', args=[batch.pk])
        confirm_url = reverse('finance:csv_confirm', args=[batch.pk])
        page = self.client.get(preview_url)
        self.assertContains(page, '&lt;script&gt;alert(1)&lt;/script&gt;')
        self.assertNotContains(page, '<script>alert(1)</script>')
        self.assertEqual(self.client.get(confirm_url).status_code, 405)
        secure = Client(enforce_csrf_checks=True)
        secure.force_login(self.alice)
        self.assertEqual(secure.post(self.url, {}).status_code, 403)
        self.assertEqual(secure.post(confirm_url, {}).status_code, 403)
        token = secure.get(preview_url).cookies['csrftoken'].value
        self.assertEqual(secure.post(confirm_url, {}, HTTP_X_CSRFTOKEN=token).status_code, 302)
        self.client.logout()
        for url in [self.url, preview_url, reverse('finance:csv_template')]:
            self.assertEqual(self.client.get(url).status_code, 302)
        self.assertEqual(self.client.post(confirm_url).status_code, 302)


class CsvConcurrencyTests(TransactionTestCase):
    def test_simultaneous_confirmations_insert_one_batch_only(self):
        user = User.objects.create(username='concurrency-test', password='!')
        category = Category.objects.create(user=user, name='Test DB only', kind='expense')
        raw = csv_bytes([['2026-10-20','expense','123',category.name,'Test only']])
        for same_batch in [True, False]:
            with self.subTest(same_batch=same_batch):
                # Khác byte để hai lần subtest có hash riêng, không đổi giao dịch cũ.
                if not same_batch:
                    raw = raw.replace(b'Test only', b'Other test only')
                first = stage_csv(raw, user, inspect_csv(raw, user))
                second = first if same_batch else stage_csv(raw, user, inspect_csv(raw, user))
                before = Transaction.objects.count()
                barrier = Barrier(2)
                def work(pk):
                    close_old_connections()
                    try:
                        barrier.wait(timeout=10)
                        return confirm_batch(pk, user)
                    except (ImportProblem, OperationalError, IntegrityError):
                        return 0
                    finally:
                        close_old_connections()
                with ThreadPoolExecutor(max_workers=2) as pool:
                    outcomes = list(pool.map(work, [first.pk, second.pk]))
                self.assertEqual(sum(outcomes), 1)
                self.assertEqual(Transaction.objects.count(), before + 1)
                self.assertEqual(CsvImportReceipt.objects.filter(user=user, sha256=first.sha256).count(), 1)
