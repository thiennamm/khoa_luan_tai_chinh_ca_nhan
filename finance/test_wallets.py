from datetime import date
from decimal import Decimal
from threading import Thread, Barrier
from queue import Queue
from unittest import skipUnless
from unittest.mock import patch
from django.apps import apps
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import connection, close_old_connections
from django.db.models.deletion import RestrictedError
from django.test import TestCase, TransactionTestCase, Client
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from .models import (Wallet, WalletTransfer, Transaction, Category, MonthlyCoverage,
    ForecastDataVersion, ClassificationFeedback, Budget, RecurringOccurrence)
from .forms import TransactionForm, SimilarTransactionForm
from .wallet_forms import WalletForm, TransferForm
from . import wallets, csv_import, recurring, similar_transactions, classification_feedback
from .recurring_forms import RecurringRuleForm, RecurringConfirmationForm
from .budgets import monthly_budgets

DAY=date(2026,11,3)


class WalletTests(TestCase):
    def setUp(self):
        self.clock=patch('finance.wallets.today',return_value=DAY);self.clock.start();self.addCleanup(self.clock.stop)
        self.user=User.objects.create_user('wallet-qa');self.other=User.objects.create_user('wallet-other')
        self.food=Category.objects.create(user=self.user,name='QA chi',kind='expense',canonical_label='Education')
        self.salary=Category.objects.create(user=self.user,name='QA thu',kind='income')
        self.a=Wallet.objects.create(user=self.user,name='Tiền mặt',kind='cash',opening_balance=Decimal('1000'),start_date=date(2026,1,1))
        self.b=Wallet.objects.create(user=self.user,name='Ngân hàng',kind='bank',opening_balance=Decimal('-50'),start_date=date(2026,1,1))
        self.foreign=Wallet.objects.create(user=self.other,name='Ví riêng',kind='electronic',opening_balance=100,start_date=date(2026,1,1))
        self.client.force_login(self.user)

    def row(self, wallet=None, **changes):
        return Transaction.objects.create(user=self.user,category=self.food,kind='expense',amount=Decimal('100'),
            date=DAY,wallet=wallet,**changes)

    def data(self, **changes):
        return {'source':self.a,'destination':self.b,'amount':Decimal('100'),'date':DAY,'note':'QA chuyển',**changes}

    def totals(self):
        return {r['wallet'].pk:r['balance'] for r in wallets.balances(self.user)['wallet_rows']}

    def raw(self):
        return b'date,kind,amount,category,description\n2026-11-03,expense,100,QA chi,qa\n'

    def test_opening_signed_zero_name_normalization_and_no_income(self):
        self.assertEqual(wallets.balances(self.user)['wallet_total'],Decimal('950'))
        self.assertFalse(Transaction.objects.exists())
        form=WalletForm({'name':'  TIỀN   MẶT ','kind':'cash','opening_balance':'0','start_date':'2026-01-01'},user=self.user)
        self.assertFalse(form.is_valid())
        form=WalletForm({'name':'QA mới','kind':'other','opening_balance':'-50.000','start_date':'2026-01-01'},user=self.user)
        self.assertTrue(form.is_valid(),form.errors);self.assertEqual(form.save().opening_balance,Decimal('-50000'))
        self.assertFalse(WalletForm({'name':'x','kind':'cash','opening_balance':'1,500','start_date':'2026-01-01'},user=self.user).is_valid())

    def test_income_expense_future_unknown_and_opening_not_started(self):
        self.row(self.a)
        Transaction.objects.create(user=self.user,category=self.salary,kind='income',amount=300,date=DAY,wallet=self.a)
        self.row(None)
        Transaction.objects.create(user=self.user,category=self.food,kind='expense',amount=700,date=date(2026,11,4),wallet=self.a)
        future=Wallet.objects.create(user=self.user,name='Chưa bắt đầu',kind='other',opening_balance=999,start_date=date(2026,12,1))
        result=wallets.balances(self.user)
        self.assertEqual(self.totals()[self.a.pk],Decimal('1200'))
        self.assertIsNone(self.totals()[future.pk])
        self.assertEqual(result['unknown']['expense'],100)
        self.assertEqual(next(r for r in result['wallet_rows'] if r['wallet']==self.a)['future_expense'],700)
        self.assertEqual(wallets.balances(self.user,date(2025,12,31))['wallet_total'],0)

    def test_edit_move_and_delete_source_derived_balances(self):
        row=self.row(self.a);self.assertEqual(self.totals()[self.a.pk],900)
        row.wallet=self.b;row.amount=Decimal(150);row.save()
        self.assertEqual(self.totals()[self.a.pk],1000);self.assertEqual(self.totals()[self.b.pk],-200)
        row.delete();self.assertEqual(self.totals()[self.b.pk],-50)

    def test_transaction_owner_start_day_bulk_and_queryset_update(self):
        with self.assertRaises(ValidationError):self.row(self.foreign)
        with self.assertRaises(ValidationError):
            Transaction.objects.create(user=self.user,category=self.food,kind='expense',amount=1,date=date(2025,12,31),wallet=self.a)
        row=self.row(self.a)
        with self.assertRaises(ValidationError):Transaction.objects.filter(pk=row.pk).update(wallet=self.foreign)
        row.refresh_from_db();self.assertEqual(row.wallet,self.a)
        with self.assertRaises(ValidationError):Transaction.objects.bulk_create([Transaction(user=self.user,category=self.food,kind='expense',amount=1,date=DAY,wallet=self.foreign)])
        self.assertEqual(Transaction.objects.count(),1)

    def test_archive_keeps_old_edit_blocks_new_and_excludes_total(self):
        row=self.row(self.a);self.a.archived=True;self.a.save()
        with self.assertRaises(ValidationError):self.row(self.a)
        row.amount=Decimal(110);row.save();self.assertEqual(self.totals()[self.a.pk],890)
        self.assertEqual(wallets.balances(self.user)['wallet_total'],-50)
        self.a.archived=False;self.a.save();self.row(self.a)

    def test_opening_date_locked_and_wallet_delete_protected(self):
        row=self.row(self.a)
        self.a.opening_balance=Decimal(2000)
        with self.assertRaises(ValidationError):self.a.save()
        self.a.refresh_from_db();self.a.start_date=date(2025,1,1)
        with self.assertRaises(ValidationError):self.a.save()
        with self.assertRaises((RestrictedError,ValidationError)):self.a.delete()
        row.delete();self.a.refresh_from_db()
        self.assertTrue(self.a.opening_locked)
        self.a.opening_balance=Decimal(2000);self.a.opening_locked=False
        with self.assertRaises(ValidationError):self.a.save()
        with self.assertRaises(ValidationError):Wallet.objects.filter(pk=self.a.pk).delete()

    def test_transfer_conservation_negative_balance_and_no_financial_side_effects(self):
        MonthlyCoverage.objects.create(user=self.user,month=date(2026,10,1),status='complete',confirmed_at=__import__('django.utils.timezone',fromlist=['now']).now())
        before={m.__name__:list(m.objects.values()) for m in (Transaction,MonthlyCoverage,ForecastDataVersion,ClassificationFeedback,Budget)}
        record,_=wallets.transfer(self.user,wallets.issue_transfer(self.user),self.data(amount=Decimal(1500)))
        self.assertEqual(self.totals()[self.a.pk],-500);self.assertEqual(self.totals()[self.b.pk],1450)
        self.assertEqual(wallets.balances(self.user)['wallet_total'],950)
        self.assertEqual(before,{m.__name__:list(m.objects.values()) for m in (Transaction,MonthlyCoverage,ForecastDataVersion,ClassificationFeedback,Budget)})
        with self.assertRaises(ValidationError):record.delete()
        with self.assertRaises(ValidationError):WalletTransfer.objects.filter(pk=record.pk).update(amount=1)

    def test_repeat_same_operation_and_two_separate_intents(self):
        token=wallets.issue_transfer(self.user)
        first,_=wallets.transfer(self.user,token,self.data())
        second,repeated=wallets.transfer(self.user,token,self.data())
        self.assertEqual(first.pk,second.pk);self.assertTrue(repeated)
        with self.assertRaises(ValidationError):wallets.transfer(self.user,token,self.data(amount=Decimal(101)))
        wallets.transfer(self.user,wallets.issue_transfer(self.user),self.data())
        self.assertEqual(WalletTransfer.objects.count(),2)

    def test_invalid_transfer_owner_same_archive_amount_and_dates(self):
        for changes in ({'source':self.foreign},{'destination':self.a},{'date':date(2026,11,4)},
                        {'date':date(2025,12,31)},{'amount':Decimal(0)},{'amount':Decimal('1.5')}):
            with self.subTest(changes=list(changes)),self.assertRaises(ValidationError):
                wallets.transfer(self.user,wallets.issue_transfer(self.user),self.data(**changes))
        with self.assertRaises(ValidationError):wallets.transfer(self.other,wallets.issue_transfer(self.user),self.data())
        stale=TransferForm({'source':self.a.pk,'destination':self.b.pk,'amount':'100',
            'date':DAY,'note':'QA stale form','operation_token':wallets.issue_transfer(self.user)},user=self.user)
        self.assertTrue(stale.is_valid(),stale.errors)
        live_destination=Wallet.objects.get(pk=self.b.pk)
        live_destination.archived=True;live_destination.save()
        # The ModelChoice in cleaned_data still says active. Save must reload it.
        self.assertFalse(stale.cleaned_data['destination'].archived)
        with self.assertRaises(ValidationError):
            wallets.transfer(self.user,stale.cleaned_data['operation_token'],stale.cleaned_data)
        self.assertFalse(WalletTransfer.objects.exists())

    def test_transfer_rollback_leaves_no_half_record_or_balance(self):
        queryset=type(Wallet.objects.all())
        real_update=queryset.update
        inserted=[]
        def fail_after_insert(rows,**values):
            if values.get('opening_locked') is True:
                inserted.append(WalletTransfer.objects.count())
                raise RuntimeError('QA failure after transfer INSERT')
            return real_update(rows,**values)
        token=wallets.issue_transfer(self.user)
        with patch.object(queryset,'update',fail_after_insert):
            with self.assertRaises(RuntimeError):wallets.transfer(self.user,token,self.data())
        self.assertEqual(inserted,[1])
        self.assertFalse(WalletTransfer.objects.exists());self.assertEqual(wallets.balances(self.user)['wallet_total'],950)
        self.a.refresh_from_db();self.b.refresh_from_db()
        self.assertFalse(self.a.opening_locked or self.b.opening_locked)
        # Rolled-back UUID was not consumed; an explicit retry can succeed once.
        wallets.transfer(self.user,token,self.data())
        self.assertEqual(WalletTransfer.objects.count(),1)

    def test_delete_account_cascades_without_orphan_wallet_data(self):
        wallets.transfer(self.user,wallets.issue_transfer(self.user),self.data())
        self.user.delete()
        self.assertFalse(WalletTransfer.objects.exists());self.assertFalse(Transaction.objects.exists())
        self.assertEqual(Wallet.objects.count(),1)

    def test_wallet_urls_owner_csrf_and_get_never_writes(self):
        models=list(apps.get_app_config('finance').get_models())
        before={m.__name__:list(m.objects.order_by('pk').values()) for m in models}
        for name,kwargs in [('wallet_list',{}),('wallet_detail',{'pk':self.a.pk}),('wallet_transfer',{}),('wallet_unknown',{}),('wallet_create',{})]:
            self.assertEqual(self.client.get(reverse('finance:'+name,kwargs=kwargs)).status_code,200)
        self.assertEqual(before,{m.__name__:list(m.objects.order_by('pk').values()) for m in models})
        for name in ('wallet_detail','wallet_edit','wallet_status'):
            self.assertEqual(self.client.get(reverse('finance:'+name,args=[self.foreign.pk])).status_code,404)
        secure=Client(enforce_csrf_checks=True);secure.force_login(self.user)
        self.assertEqual(secure.post(reverse('finance:wallet_transfer'),{}).status_code,403)
        self.client.logout();self.assertEqual(self.client.get(reverse('finance:wallet_list')).status_code,302)

    def test_archive_post_repeated_is_idempotent(self):
        url=reverse('finance:wallet_status',args=[self.a.pk])
        for _ in range(2):self.assertEqual(self.client.post(url,{'confirm':'on','action':'archive'}).status_code,302)
        self.a.refresh_from_db();self.assertTrue(self.a.archived)
        self.client.post(url,{'confirm':'on','action':'reopen'});self.a.refresh_from_db();self.assertFalse(self.a.archived)

    def test_transfer_form_post_replay_and_foreign_detail(self):
        data={'source':self.a.pk,'destination':self.b.pk,'amount':'50.000','date':DAY,'note':'<b>QA</b>','operation_token':wallets.issue_transfer(self.user)}
        response=self.client.post(reverse('finance:wallet_transfer'),data)
        self.assertEqual(response.status_code,302)
        self.assertEqual(self.client.post(reverse('finance:wallet_transfer'),data).url,response.url)
        self.assertContains(self.client.get(response.url),'&lt;b&gt;QA&lt;/b&gt;')
        self.client.force_login(self.other);self.assertEqual(self.client.get(response.url).status_code,404)

    def test_history_pagination_date_filter_escape_and_direction(self):
        for _ in range(22):self.row(self.a,description='<script>qa</script>')
        wallets.transfer(self.user,wallets.issue_transfer(self.user),self.data())
        url=reverse('finance:wallet_detail',args=[self.a.pk])
        first=self.client.get(url,{'start':'2026-11-03','end':'2026-11-03'})
        self.assertEqual(first.context['page_obj'].paginator.count,23)
        self.assertContains(first,'&lt;script&gt;qa&lt;/script&gt;');self.assertNotContains(first,'<script>qa</script>')
        self.assertEqual(len(self.client.get(url,{'page':2}).context['page_obj']),3)
        self.assertContains(self.client.get(reverse('finance:wallet_detail',args=[self.b.pk])),'Chuyển đến')
        self.assertEqual(self.client.get(url,{'start':'2026-12-01','end':'2026-01-01'}).status_code,400)

    def test_balance_group_queries_do_not_grow_per_wallet_or_transaction(self):
        def measure():
            with CaptureQueriesContext(connection) as captured:wallets.balances(self.user)
            return len(captured)
        count=measure()
        for index in range(12):
            wallet=Wallet.objects.create(user=self.user,name=f'QA {index}',kind='cash',opening_balance=0,start_date=date(2026,1,1))
            self.row(wallet)
        self.assertEqual(measure(),count);self.assertLessEqual(count,5)

    def test_wallet_filter_unknown_combined_pagination_and_export_contract(self):
        self.row(self.a);self.row(self.b);self.row(None)
        url=reverse('finance:transaction_list')
        params={'month':'2026-11','wallet':self.a.pk,'kind':'expense','category':self.food.pk}
        response=self.client.get(url,params)
        self.assertEqual(response.context['expense'],100);self.assertEqual(response.context['result_count'],1)
        self.assertEqual(self.client.get(url,{'month':'2026-11','wallet':'unknown'}).context['result_count'],1)
        self.assertFalse(self.client.get(url,{'wallet':self.foreign.pk}).context['filters_valid'])
        exported=self.client.get(reverse('finance:transaction_export'),params)
        content=b''.join(exported.streaming_content) if exported.streaming else exported.content
        self.assertEqual(content.decode('utf-8-sig').splitlines()[0],'date,kind,amount,category,description')

    def test_csv_wallet_preview_confirm_duplicate_across_wallets(self):
        raw=self.raw();inspection=csv_import.inspect_csv(raw,self.user,self.a)
        self.assertTrue(inspection.valid)
        batch=csv_import.stage_csv(raw,self.user,inspection,self.a)
        preview=self.client.get(reverse('finance:csv_preview',args=[batch.pk]));self.assertContains(preview,'Tiền mặt')
        csv_import.confirm_batch(batch.pk,self.user)
        self.assertEqual(Transaction.objects.get().wallet,self.a)
        with self.assertRaises(csv_import.ImportProblem):csv_import.stage_csv(raw,self.user,inspection,self.b)

    def test_csv_rechecks_archive_owner_and_start_date_rolls_back(self):
        batch=csv_import.stage_csv(self.raw(),self.user,csv_import.inspect_csv(self.raw(),self.user),self.a)
        self.a.archived=True;self.a.save()
        with self.assertRaises(csv_import.ImportProblem):csv_import.confirm_batch(batch.pk,self.user)
        batch.refresh_from_db();self.assertEqual(batch.status,'pending');self.assertFalse(Transaction.objects.exists())
        self.assertFalse(csv_import.inspect_csv(self.raw(),self.user,self.foreign).valid)
        self.b.start_date=date(2026,11,4);self.b.save()
        self.assertFalse(csv_import.inspect_csv(self.raw(),self.user,self.b).valid)

    def test_recurring_default_snapshot_and_record_checks_wallet(self):
        with patch('finance.recurring.today',return_value=DAY):
            form=RecurringRuleForm({'name':'QA kỳ','kind':'expense','amount':'200','category':self.food.pk,'wallet':self.a.pk,'due_day':3,'start_month':'2026-11','end_month':''},user=self.user)
            self.assertTrue(form.is_valid(),form.errors);rule=recurring.save_rule(form,self.user)
            self.assertEqual(rule.revisions.get().snapshot['wallet_id'],self.a.pk)
            actual=RecurringConfirmationForm({'amount':'150','date':DAY,'category':self.food.pk,'wallet':self.b.pk,'description':'QA thực'},user=self.user,expected_kind='expense')
            self.assertTrue(actual.is_valid(),actual.errors)
            occurrence=recurring.process(self.user,rule.pk,date(2026,11,1),'record',actual)
            self.assertEqual(occurrence.transaction.wallet,self.b);self.assertFalse(ClassificationFeedback.objects.exists())

    def test_recurring_archived_default_requires_review_not_silent_fallback(self):
        self.a.archived=True;self.a.save()
        data={'amount':'100','date':DAY,'category':self.food.pk,'wallet':'','description':'qa'}
        form=RecurringConfirmationForm(data,user=self.user,expected_kind='expense',initial={'wallet':self.a.pk})
        self.assertFalse(form.is_valid())
        form=RecurringConfirmationForm({**data,'wallet_review':'on'},user=self.user,expected_kind='expense',initial={'wallet':self.a.pk})
        self.assertTrue(form.is_valid(),form.errors)

    def test_similar_prefills_only_active_wallet_and_hash_binds_final_wallet(self):
        source=self.row(self.a)
        initial,review=similar_transactions.initial_data(source,self.user)
        self.assertFalse(review);self.assertEqual(initial['wallet'],self.a.pk)
        data={'kind':'expense','amount':'100','date':DAY,'category':self.food.pk,'wallet':self.b.pk,'description':'QA','similar_operation':initial['similar_operation']}
        form=SimilarTransactionForm(data,user=self.user);self.assertTrue(form.is_valid(),form.errors)
        new,_=similar_transactions.save(form,self.user,data['similar_operation']);self.assertEqual(new.wallet,self.b)
        changed=SimilarTransactionForm({**data,'wallet':self.a.pk},user=self.user);self.assertTrue(changed.is_valid())
        with self.assertRaises(similar_transactions.SimilarConflict):similar_transactions.save(changed,self.user,data['similar_operation'])
        source.refresh_from_db();self.assertEqual(source.wallet,self.a)

    def test_similar_archived_source_requires_explicit_unknown(self):
        source=self.row(self.a);self.a.archived=True;self.a.save()
        initial,review=similar_transactions.initial_data(source,self.user)
        self.assertTrue(review);self.assertIsNone(initial['wallet'])
        data={'kind':'expense','amount':'100','date':DAY,'category':self.food.pk,'wallet':'','description':'QA','similar_operation':initial['similar_operation']}
        form=SimilarTransactionForm(data,user=self.user);self.assertTrue(form.is_valid())
        with self.assertRaises(similar_transactions.SimilarConflict):similar_transactions.save(form,self.user,data['similar_operation'])
        form=SimilarTransactionForm({**data,'confirm_unknown_wallet':'on'},user=self.user);self.assertTrue(form.is_valid())
        saved,_=similar_transactions.save(form,self.user,data['similar_operation']);self.assertIsNone(saved.wallet)

    def test_ml_apply_save_and_coverage_budget_follow_real_transaction_only(self):
        data={'description':'QA học phí','kind':'expense','mode':'vi'}
        with patch('finance.views.suggest_label',return_value='Education'):
            offered=self.client.post(reverse('finance:category_suggestion'),data).json()
        self.assertEqual(self.client.post(reverse('finance:suggestion_action'),{**data,'action':'apply','suggestion_id':offered['suggestion_id'],'category':self.food.pk}).status_code,200)
        self.assertFalse(Transaction.objects.exists())
        response=self.client.post(reverse('finance:transaction_create'),{**data,'suggestion_mode':'vi','suggestion_id':offered['suggestion_id'],'amount':'100','date':DAY,'category':self.food.pk,'wallet':self.a.pk})
        self.assertEqual(response.status_code,302);self.assertTrue(ClassificationFeedback.objects.get().applied)
        self.assertEqual(Transaction.objects.get().wallet,self.a)
        self.assertEqual(self.totals()[self.a.pk],900)


@skipUnless(connection.vendor=='postgresql','Concurrent row-lock verification requires PostgreSQL QA')
class WalletConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.user=User.objects.create_user('wallet-concurrent')
        self.a=Wallet.objects.create(user=self.user,name='A',kind='cash',opening_balance=1000,start_date=date(2020,1,1))
        self.b=Wallet.objects.create(user=self.user,name='B',kind='bank',opening_balance=0,start_date=date(2020,1,1))

    def run_race(self,tokens):
        barrier=Barrier(2);results=Queue()
        def worker(token):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                item,repeated=wallets.transfer(self.user,token,{'source':self.a,'destination':self.b,'amount':Decimal(100),'date':date(2026,1,1),'note':'QA race'})
                results.put(('ok',item.pk))
            except Exception as exc:results.put(('error',type(exc).__name__))
            finally:close_old_connections()
        threads=[Thread(target=worker,args=[token]) for token in tokens]
        for thread in threads:thread.start()
        for thread in threads:thread.join(timeout=20);self.assertFalse(thread.is_alive())
        values=[results.get_nowait() for _ in threads]
        self.assertTrue(all(v[0]=='ok' for v in values),values)
        return values

    def test_two_requests_same_receipt_create_one_transfer(self):
        token=wallets.issue_transfer(self.user)
        values=self.run_race([token,token]);self.assertEqual(values[0][1],values[1][1])
        self.assertEqual(WalletTransfer.objects.count(),1)
        self.assertEqual(wallets.balances(self.user)['wallet_total'],1000)

    def test_two_distinct_intents_both_commit_without_lost_money(self):
        self.run_race([wallets.issue_transfer(self.user),wallets.issue_transfer(self.user)])
        self.assertEqual(WalletTransfer.objects.count(),2)
        amounts={r['wallet'].pk:r['balance'] for r in wallets.balances(self.user)['wallet_rows']}
        self.assertEqual((amounts[self.a.pk],amounts[self.b.pk]),(800,200))
