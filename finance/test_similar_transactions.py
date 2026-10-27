"""Synthetic fixtures only; never connect a real application database."""
from datetime import date, datetime, timezone as utc
from decimal import Decimal
from queue import Queue
from threading import Barrier, Thread
from unittest.mock import patch

from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, OperationalError, close_old_connections, connection
from django.db.models.deletion import ProtectedError
from django.test import Client, TransactionTestCase
from django.urls import reverse
from django.utils import timezone

from . import classification_feedback as ml
from . import similar_transactions as service
from .forms import SimilarTransactionForm
from .models import (Transaction, Category, SimilarTransactionOperation, ClassificationFeedback,
    ClassificationSuggestion, MonthlyCoverage, ForecastDataVersion, ForecastResult,
    CsvImportReceipt, CsvImportBatch, RecurringRule, RecurringOccurrence, Budget)
from .tests import FinanceCase


class SimilarTransactionTests(FinanceCase):
    def setUp(self):
        super().setUp()
        self.open_url = reverse('finance:transaction_duplicate', args=[self.alice_row.pk])
        self.save_url = reverse('finance:transaction_duplicate_save')

    def opened(self):
        return self.client.get(self.open_url)

    def token(self):
        return self.opened().context['form']['similar_operation'].value()

    def post(self, token=None, **changes):
        return self.client.post(self.save_url, self.payload(similar_operation=token or self.token(), **changes))

    def test_get_prefills_decimal_today_vietnam_and_writes_no_finance_data(self):
        models = list(apps.get_app_config('finance').get_models())
        before = {m.__name__: list(m.objects.order_by('pk').values()) for m in models}
        with patch('django.utils.timezone.now', return_value=datetime(2026, 10, 31, 17, 0, 1, tzinfo=utc.utc)), timezone.override('UTC'):
            response = self.opened()
        form = response.context['form']
        self.assertEqual(form.initial['date'], date(2026, 11, 1))
        for field in ('description', 'kind', 'amount'):
            self.assertEqual(form.initial[field], getattr(self.alice_row, field))
        self.assertIsInstance(form.initial['amount'], Decimal)
        self.assertEqual(form.initial['category'], self.food.pk)
        self.assertTrue(form.instance._state.adding)
        self.assertIsNone(form.instance.pk)
        self.assertEqual(response.context['source_transaction_id'], '')
        self.assertEqual(response.context['suggestion_id'], '')
        self.assertContains(response, 'Tạo giao dịch tương tự')
        self.assertContains(response, 'Đã điền từ giao dịch trước. Chưa tạo giao dịch mới.')
        self.assertContains(response, f'action="{self.save_url}"')
        self.assertIn('no-store', response['Cache-Control'])
        self.assertEqual(before, {m.__name__: list(m.objects.order_by('pk').values()) for m in models})

    def test_access_methods_owner_csrf_and_detail_link(self):
        self.assertContains(self.client.get(reverse('finance:transaction_detail', args=[self.alice_row.pk])), self.open_url)
        self.assertEqual(self.client.get(reverse('finance:transaction_duplicate', args=[self.bob_row.pk])).status_code, 404)
        self.assertEqual(self.client.post(self.open_url, self.payload()).status_code, 405)
        self.assertEqual(self.client.get(self.save_url).status_code, 405)
        csrf = Client(enforce_csrf_checks=True); csrf.force_login(self.alice)
        self.assertEqual(csrf.post(self.save_url, self.payload(similar_operation=self.token())).status_code, 403)
        self.client.logout()
        self.assertEqual(self.client.get(self.open_url).status_code, 302)
        self.assertEqual(self.client.post(self.save_url).status_code, 302)

    def test_save_independent_id_source_unchanged_and_ignores_forged_internal_fields(self):
        source = Transaction.objects.filter(pk=self.alice_row.pk).values().get()
        response = self.post(user_id=self.bob.pk, source_id=self.bob_row.pk,
            transaction_id=self.bob_row.pk, id=self.alice_row.pk, applied=True, predicted_label='Income')
        self.assertEqual(response.status_code, 302)
        saved = Transaction.objects.latest('pk')
        self.assertNotEqual(saved.pk, self.alice_row.pk)
        self.assertEqual(saved.user_id, self.alice.pk)
        self.assertEqual(saved.amount, Decimal('250000'))
        self.assertEqual(source, Transaction.objects.filter(pk=self.alice_row.pk).values().get())
        self.assertFalse(ClassificationFeedback.objects.exists())
        self.assertFalse(ClassificationSuggestion.objects.exists())
        self.assertFalse(RecurringOccurrence.objects.filter(transaction=saved).exists())

    def test_source_edit_and_delete_after_get_do_not_control_submitted_fields(self):
        for remove in (False, True):
            token = self.token()
            if remove:
                self.alice_row.delete()
            else:
                self.alice_row.description = 'Nguồn đã sửa'
                self.alice_row.amount = Decimal('1')
                self.alice_row.save()
            response = self.post(token, description='Tôi đã chỉnh trên form', amount='50.000')
            self.assertEqual(response.status_code, 302)
            saved = Transaction.objects.latest('pk')
            self.assertEqual(saved.description, 'Tôi đã chỉnh trên form')
            self.assertEqual(saved.amount, Decimal('50000'))

    def test_invalid_source_category_is_not_replaced(self):
        # Deliberately inconsistent QA row, bypassing supported Model validation.
        Transaction.objects.filter(pk=self.alice_row.pk).update(kind='income')
        page = self.opened()
        self.assertIsNone(page.context['form'].initial['category'])
        self.assertContains(page, 'Hãy chọn lại danh mục')

    def test_invalid_input_preserved_and_no_receipt_or_transaction(self):
        token = self.token(); before = Transaction.objects.count()
        for changes, field in [({'amount':'50,00'},'amount'), ({'category':self.bob_category.pk},'category'),
                ({'kind':'income'},'category'), ({'date':'2026-02-30'},'date'),
                ({'amount':'1000000000000000'},'amount')]:
            response = self.post(token, description='Giữ dữ liệu <QA>', **changes)
            self.assertIn(field, response.context['form'].errors)
            self.assertEqual(response.context['form']['description'].value(), 'Giữ dữ liệu <QA>')
            self.assertEqual(response.context['form']['similar_operation'].value(), token)
        self.assertEqual(Transaction.objects.count(), before)
        self.assertFalse(SimilarTransactionOperation.objects.exists())

    def test_invalid_missing_expired_or_foreign_token(self):
        for token in ('bad', service.issue(self.bob), 'x' * 1001):
            self.assertEqual(self.post(token).status_code, 200)
        self.assertEqual(self.client.post(self.save_url, self.payload()).status_code, 200)
        token = self.token()
        import time
        with patch('django.core.signing.time.time', return_value=time.time()+service.TOKEN_AGE+1):
            response = self.post(token)
        self.assertContains(response, 'đã hết hạn')
        self.assertFalse(SimilarTransactionOperation.objects.exists())
        self.assertEqual(Transaction.objects.count(), 2)

    def test_repeated_token_once_distinct_opens_allow_same_real_data(self):
        one, two = self.token(), self.token()
        self.assertNotEqual(one, two)
        first, repeated = self.post(one), self.post(one)
        self.assertEqual(first['Location'], repeated['Location'])
        self.assertEqual(SimilarTransactionOperation.objects.count(), 1)
        self.assertEqual(Transaction.objects.count(), 3)
        self.assertEqual(self.post(two).status_code, 302)
        self.assertEqual(Transaction.objects.count(), 4)

    def test_changed_payload_same_token_rejected_and_deleted_result_not_recreated(self):
        token = self.token(); self.post(token)
        response = self.post(token, amount='1000')
        self.assertContains(response, 'dữ liệu khác')
        created = SimilarTransactionOperation.objects.get().saved_transaction
        created.delete()
        response = self.post(token)
        self.assertContains(response, 'đã bị xóa')
        self.assertEqual(Transaction.objects.count(), 2)
        self.assertIsNone(SimilarTransactionOperation.objects.get().saved_transaction_id)

    def test_category_changed_after_validation_rechecked_at_save(self):
        form = SimilarTransactionForm(self.payload(similar_operation=self.token()), user=self.alice)
        self.assertTrue(form.is_valid(), form.errors)
        Category.objects.filter(pk=self.food.pk).update(kind='income')
        with self.assertRaises(Category.DoesNotExist):
            service.save(form, self.alice, form.cleaned_data['similar_operation'])
        self.assertFalse(SimilarTransactionOperation.objects.exists())

    def test_source_recurring_csv_and_ml_trace_not_copied(self):
        source = self.alice_row
        rule = RecurringRule.objects.create(user=self.alice, name='QA', kind='expense', amount=source.amount,
            category=self.food, due_day=1, start_month=source.date)
        occ = RecurringOccurrence.objects.create(user=self.alice, rule=rule, month=source.date,
            due_date=source.date, snapshot={'name':'QA'}, status='recorded', transaction=source)
        receipt = ml.issue(self.alice, {'description':source.description,'kind':'expense','mode':'vi'}, 'Groceries', source)
        ClassificationFeedback.objects.create(user=self.alice, transaction=source, suggestion=receipt,
            mode='vi', model_name=receipt.model_name, model_sha256=receipt.model_sha256,
            predicted_label='Groceries', final_category=self.food, final_category_name=self.food.name,
            final_label='Groceries', applied=True, same_label=True)
        CsvImportReceipt.objects.create(user=self.alice, sha256='a'*64, transaction_count=1)
        self.assertEqual(self.post().status_code, 302)
        created = SimilarTransactionOperation.objects.get().saved_transaction
        occ.refresh_from_db(); self.assertEqual(occ.transaction_id, source.pk)
        self.assertFalse(RecurringOccurrence.objects.filter(transaction=created).exists())
        self.assertEqual(ClassificationFeedback.objects.count(), 1)
        self.assertEqual(ClassificationSuggestion.objects.count(), 1)
        self.assertEqual(CsvImportReceipt.objects.count(), 1)
        self.assertFalse(CsvImportBatch.objects.exists())

    def test_new_ml_apply_save_uses_new_context_and_old_receipt_rejected(self):
        self.food.canonical_label='Groceries'; self.food.save()
        data={'description':'Mua rau chợ', 'kind':'expense','mode':'vi'}
        old=ml.issue(self.alice,data,'Groceries',self.alice_row)
        self.assertEqual(self.post(suggestion_id=str(old.pk),suggestion_mode='vi',description=data['description']).status_code,200)
        self.assertFalse(SimilarTransactionOperation.objects.exists())
        with patch('finance.views.suggest_label', return_value='Groceries'):
            offer=self.client.post(reverse('finance:category_suggestion'), data).json()
        receipt=ClassificationSuggestion.objects.get(pk=offer['suggestion_id'])
        self.assertIsNone(receipt.source_transaction_id)
        applied=self.client.post(reverse('finance:suggestion_action'),{**data,'action':'apply',
            'suggestion_id':str(receipt.pk),'category':self.food.pk})
        self.assertEqual(applied.status_code,200)
        operation=self.token()
        self.assertEqual(self.post(operation,suggestion_id=str(receipt.pk),suggestion_mode='vi',description=data['description']).status_code,302)
        fb=ClassificationFeedback.objects.get()
        self.assertTrue(fb.applied);self.assertTrue(fb.same_label)
        self.assertEqual(fb.transaction_id,SimilarTransactionOperation.objects.get().saved_transaction_id)
        self.post(operation,suggestion_id=str(receipt.pk),suggestion_mode='vi',description=data['description'])
        self.assertEqual(ClassificationFeedback.objects.count(),1)

    def test_consumed_ml_receipt_from_other_form_not_reused(self):
        self.food.canonical_label='Groceries';self.food.save()
        token=ml.issue(self.alice,{'description':'Khoản chi','kind':'expense','mode':'vi'},'Groceries')
        self.client.post(reverse('finance:transaction_create'),self.payload(suggestion_id=str(token.pk),suggestion_mode='vi'))
        before=Transaction.objects.count()
        response=self.post(suggestion_id=str(token.pk),suggestion_mode='vi')
        self.assertContains(response,'Gợi ý không còn hợp lệ')
        self.assertEqual(Transaction.objects.count(),before)
        self.assertFalse(SimilarTransactionOperation.objects.exists())

    def test_unavailable_ml_does_not_block_manual_save(self):
        from .classification_modes import ModelUnavailable
        with patch('finance.views.suggest_label',side_effect=ModelUnavailable):
            self.assertEqual(self.client.post(reverse('finance:category_suggestion'),
                {'description':'QA','kind':'expense','mode':'vi'}).status_code,503)
            self.assertEqual(self.post().status_code,302)
        self.assertFalse(ClassificationFeedback.objects.exists())

    def test_only_successful_save_changes_target_month_coverage_budget_and_forecast(self):
        from .forecasting import snapshot,compute_and_store
        from .budgets import monthly_budgets
        with patch('django.utils.timezone.now',return_value=datetime(2026,10,27,5,tzinfo=utc.utc)):
            for month in (6,7,8,9):
                MonthlyCoverage.objects.create(user=self.alice,month=date(2026,month,1),status='complete',confirmed_at=timezone.now())
            MonthlyCoverage.objects.create(user=self.alice,month=date(2026,10,1),status='incomplete')
            MonthlyCoverage.objects.create(user=self.bob,month=date(2026,9,1),status='complete',confirmed_at=timezone.now())
            Budget.objects.create(user=self.alice,month=date(2026,9,1),amount=Decimal('500000'))
            compute_and_store(self.alice,snapshot(self.alice))
            before_version=ForecastDataVersion.objects.filter(user=self.alice).values_list('version',flat=True).first()
            token=self.token();self.post(token,date='2026-09-15',amount='0')
            self.assertEqual(ForecastDataVersion.objects.filter(user=self.alice).values_list('version',flat=True).first(),before_version)
            self.assertIn('result',self.client.get(reverse('finance:forecast')).context)
            self.assertEqual(self.post(token,date='2026-09-15').status_code,302)
            self.assertEqual(MonthlyCoverage.objects.get(user=self.alice,month=date(2026,9,1)).status,'unknown')
            self.assertEqual(MonthlyCoverage.objects.get(user=self.alice,month=date(2026,10,1)).status,'incomplete')
            self.assertEqual(MonthlyCoverage.objects.get(user=self.bob,month=date(2026,9,1)).status,'complete')
            self.assertTrue(self.client.get(reverse('finance:forecast')).context['stale'])
            self.assertNotIn('result',self.client.get(reverse('finance:forecast')).context)
            self.assertEqual(monthly_budgets(self.alice,date(2026,9,1))['total_budget']['spent'],Decimal('250000'))

    def test_rollback_includes_transaction_operation_ml_coverage_and_version(self):
        MonthlyCoverage.objects.create(user=self.alice,month=date(2026,9,1),status='complete',confirmed_at=timezone.now())
        version=ForecastDataVersion.objects.get(user=self.alice).version
        token=self.token()
        original_save=SimilarTransactionOperation.save
        def fail_after_transaction(obj,*args,**kwargs):
            if kwargs.get('update_fields')==['saved_transaction']:
                raise IntegrityError('QA rollback after financial write')
            return original_save(obj,*args,**kwargs)
        with patch.object(SimilarTransactionOperation,'save',new=fail_after_transaction):
            response=self.post(token,date='2026-09-15')
        self.assertEqual(response.status_code,200)
        self.assertEqual(Transaction.objects.count(),2)
        self.assertFalse(SimilarTransactionOperation.objects.exists())
        self.assertEqual(MonthlyCoverage.objects.get(user=self.alice,month=date(2026,9,1)).status,'complete')
        self.assertEqual(ForecastDataVersion.objects.get(user=self.alice).version,version)
        self.assertEqual(self.post(token,date='2026-09-15').status_code,302)

    def test_account_deletion_cascades_operations(self):
        self.post()
        # Preserve the existing PROTECT policy for accounts with transactions.
        with self.assertRaises(ProtectedError):self.alice.delete()
        Transaction.objects.filter(user=self.alice).delete()
        self.alice.delete()
        self.assertFalse(SimilarTransactionOperation.objects.exists())

    def test_fresh_receipt_becomes_invalid_after_description_kind_or_mode_changes(self):
        data={'description':'Khoản chi','kind':'expense','mode':'vi'}
        for changes in ({'description':'Mô tả mới'}, {'kind':'income','category':self.salary.pk}, {'suggestion_mode':'en'}):
            receipt=ml.issue(self.alice,data,'Groceries')
            response=self.post(suggestion_id=str(receipt.pk),suggestion_mode=changes.get('suggestion_mode','vi'),
                **{k:v for k,v in changes.items() if k!='suggestion_mode'})
            self.assertContains(response,'Gợi ý không còn hợp lệ')
            receipt.refresh_from_db();self.assertIsNone(receipt.consumed_at)
        self.assertFalse(SimilarTransactionOperation.objects.exists())
        self.assertEqual(Transaction.objects.count(),2)


class SimilarConcurrencyTests(TransactionTestCase):
    def scenario(self, distinct=False, changed=False):
        user=get_user_model().objects.create_user('similar-concurrency-qa')
        cat=Category.objects.create(user=user,name='QA',kind='expense')
        tokens=[service.issue(user),service.issue(user)]
        if not distinct:tokens[1]=tokens[0]
        barrier=Barrier(2);results=Queue()
        def worker(index):
            close_old_connections()
            try:
                own=get_user_model().objects.get(pk=user.pk)
                payload={'similar_operation':tokens[index],'kind':'expense','amount':'200' if changed and index else '100',
                    'date':'2026-09-15','category':cat.pk,'description':'QA'}
                form=SimilarTransactionForm(payload,user=own)
                if not form.is_valid():raise AssertionError('QA form invalid')
                barrier.wait(timeout=10)
                saved,repeated=service.save(form,own,tokens[index])
                results.put(('ok',index,saved.pk,repeated))
            except OperationalError as exc:
                results.put(('locked' if 'locked' in str(exc).lower() else 'db_error',index,None,None))
            except service.SimilarConflict:results.put(('conflict',index,None,None))
            except Exception as exc:results.put((type(exc).__name__,index,None,None))
            finally:close_old_connections()
        threads=[Thread(target=worker,args=(i,)) for i in range(2)]
        for t in threads:t.start()
        for t in threads:t.join(timeout=25)
        self.assertFalse(any(t.is_alive() for t in threads))
        output=[results.get_nowait() for _ in range(2)]
        if connection.vendor=='postgresql':
            self.assertEqual(sorted(r[0] for r in output),['conflict','ok'] if changed else ['ok','ok'],output)
        else:
            self.assertIn('ok',[r[0] for r in output],output)
            self.assertTrue(all(r[0] in ('ok','locked','conflict') for r in output),output)
        if not changed:
            for state,index,_,_ in output:
                if state=='locked':
                    form=SimilarTransactionForm({'similar_operation':tokens[index],'kind':'expense','amount':'100',
                        'date':'2026-09-15','category':cat.pk,'description':'QA'},user=user)
                    self.assertTrue(form.is_valid());service.save(form,user,tokens[index])
        self.assertEqual(Transaction.objects.count(),2 if distinct else 1)
        self.assertEqual(SimilarTransactionOperation.objects.count(),2 if distinct else 1)
        if connection.vendor=='postgresql' and not distinct and not changed:
            self.assertEqual(len({r[2] for r in output}),1)
            self.assertEqual(sorted(r[3] for r in output),[False,True])

    def test_same_operation_concurrent_posts_create_once(self):self.scenario()
    def test_distinct_operations_allow_identical_transactions(self):self.scenario(distinct=True)
    def test_same_operation_changed_payload_conflicts(self):self.scenario(changed=True)
