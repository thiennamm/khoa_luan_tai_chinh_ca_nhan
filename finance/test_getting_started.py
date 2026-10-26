import unicodedata
from datetime import date,timedelta
from decimal import Decimal
from queue import Queue
from threading import Thread,Barrier
from unittest.mock import patch
from django.apps import apps
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import OperationalError,close_old_connections
from django.test import TestCase,TransactionTestCase,Client,SimpleTestCase
from django.urls import reverse
from django.utils import timezone
from .category_defaults import DEFAULTS,add_defaults,normalized_name,getting_started
from .models import Category,Transaction,Budget,MonthlyCoverage,ClassificationSuggestion,ClassificationFeedback
from .tests import FinanceCase


class NormalizationTests(SimpleTestCase):
    def test_unicode_case_and_whitespace_keep_accents_and_punctuation(self):
        self.assertEqual(normalized_name(unicodedata.normalize('NFD',' ĐI  CHỢ\u00a0&  SIÊU THỊ ')),
            normalized_name('Đi chợ & siêu thị'))
        self.assertNotEqual(normalized_name('Đi chợ'),normalized_name('Di cho'))
        self.assertNotEqual(normalized_name('Đi chợ & siêu thị'),normalized_name('Đi chợ và siêu thị'))

    def test_broad_defaults_unmapped_and_no_transfer(self):
        items={item.key:item for item in DEFAULTS}
        self.assertEqual(len(items),11)
        for key in ('dining','housing','bills','other_income'):self.assertEqual(items[key].label,'')
        self.assertEqual(items['salary'].label,'Income')
        self.assertEqual(items['groceries'].label,'Groceries')
        self.assertNotIn('Transfer',[item.label for item in DEFAULTS])


class GettingStartedTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user=User.objects.create_user('qa-start')
        cls.bob=User.objects.create_user('qa-start-other')

    def setUp(self):
        self.client.force_login(self.user)
        self.url=reverse('finance:category_defaults')

    def test_registration_does_not_seed_or_log_in(self):
        self.client.logout()
        response=self.client.post(reverse('signup'),{'username':'qa-new-registration','password1':'VioletRiver!72946Z',
            'password2':'VioletRiver!72946Z'})
        self.assertEqual(response.status_code,302)
        self.assertNotIn('_auth_user_id',self.client.session)
        self.assertEqual(Category.objects.count(),0)
        self.assertEqual(Transaction.objects.count(),0)

    def test_get_preview_category_and_dashboard_do_not_write(self):
        models=list(apps.get_app_config('finance').get_models())
        before={m.__name__:list(m.objects.order_by('pk').values()) for m in models}
        for url in [self.url,reverse('finance:category_list'),reverse('finance:dashboard')]:
            self.assertEqual(self.client.get(url).status_code,200)
        self.assertEqual(before,{m.__name__:list(m.objects.order_by('pk').values()) for m in models})
        self.assertContains(self.client.get(self.url),'Chưa ánh xạ')

    def test_selected_subset_and_post_repeat(self):
        data={'items':['salary','groceries','housing']}
        response=self.client.post(self.url,data)
        self.assertEqual((len(response.context['result']['created']),len(response.context['result']['skipped'])),(3,0))
        self.assertEqual(Category.objects.filter(user=self.user).count(),3)
        self.assertFalse(Category.objects.filter(name='Di chuyển').exists())
        before=list(Category.objects.order_by('pk').values())
        response=self.client.post(self.url,data)
        self.assertEqual((len(response.context['result']['created']),len(response.context['result']['skipped'])),(0,3))
        self.assertEqual(before,list(Category.objects.order_by('pk').values()))

    def test_existing_normalized_name_never_changes_name_mapping_or_id(self):
        names=[unicodedata.normalize('NFD',' ĐI  CHỢ\u00a0& SIÊU THỊ '),'nhà ở']
        Category.objects.create(user=self.user,kind='expense',name=names[0],canonical_label='')
        Category.objects.create(user=self.user,kind='expense',name=names[1],canonical_label='Healthcare')
        before=list(Category.objects.order_by('pk').values())
        result=add_defaults(self.user,['groceries','housing'])
        self.assertEqual((len(result['created']),len(result['skipped'])),(0,2))
        self.assertEqual(before,list(Category.objects.order_by('pk').values()))

    def test_same_name_other_kind_is_not_a_duplicate(self):
        Category.objects.create(user=self.user,kind='income',name='Giáo dục')
        add_defaults(self.user,['education'])
        self.assertEqual(Category.objects.filter(user=self.user,name='Giáo dục').count(),2)

    def test_partial_existing_and_all_existing_states(self):
        add_defaults(self.user,['groceries'])
        response=self.client.post(self.url,{'items':['groceries','salary']})
        self.assertEqual((len(response.context['result']['created']),len(response.context['result']['skipped'])),(1,1))
        add_defaults(self.user,[item.key for item in DEFAULTS])
        response=self.client.get(self.url)
        self.assertContains(response,'Tất cả danh mục mẫu đã tồn tại')
        self.assertNotContains(response,'Xác nhận thêm mục đã chọn')

    def test_invalid_empty_or_unknown_selection_creates_nothing(self):
        for data in [{},{'items':['groceries','not-allowed']},{'items':['Transfer']}]:
            response=self.client.post(self.url,data)
            self.assertTrue(response.context['form'].errors)
            self.assertFalse(Category.objects.exists())
        with self.assertRaises(ValidationError):add_defaults(self.user,['salary','unknown'])

    def test_only_server_catalog_values_and_current_account_used(self):
        response=self.client.post(self.url,{'items':['salary'],'user_id':self.bob.pk,'name':'Forged',
            'kind':'expense','canonical_label':'Transfer'})
        self.assertEqual(response.status_code,200)
        row=Category.objects.get()
        self.assertEqual((row.user_id,row.name,row.kind,row.canonical_label),(self.user.pk,'Lương','income','Income'))
        self.assertFalse(Category.objects.filter(user=self.bob).exists())

    def test_auth_csrf_and_account_isolation(self):
        add_defaults(self.bob,['education'])
        self.assertFalse(next(row for row in self.client.get(self.url).context['rows'] if row['item'].key=='education')['exists'])
        self.client.post(self.url,{'items':['education']})
        self.assertEqual(Category.objects.filter(user=self.bob).count(),1)
        self.assertEqual(Category.objects.filter(user=self.user).count(),1)
        csrf=Client(enforce_csrf_checks=True);csrf.force_login(self.user)
        self.assertEqual(csrf.post(self.url,{'items':['salary']}).status_code,403)
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code,302)
        self.assertEqual(self.client.post(self.url,{'items':['salary']}).status_code,302)

    def test_atomic_failure_rolls_back_entire_selection_and_auth_values(self):
        original=Category.save
        before=User.objects.get(pk=self.user.pk).last_login
        def fail_second(obj,*args,**kwargs):
            if obj.name=='Lương':raise ValidationError('QA rollback')
            return original(obj,*args,**kwargs)
        with patch.object(Category,'save',fail_second):
            response=self.client.post(self.url,{'items':['groceries','salary']})
        self.assertIsNone(response.context['result'])
        self.assertFalse(Category.objects.exists())
        self.assertEqual(User.objects.get(pk=self.user.pk).last_login,before)

    def test_onboarding_owned_data_and_budget_optional_no_coverage_required(self):
        add_defaults(self.bob,['salary'])
        bob_cat=Category.objects.get(user=self.bob)
        Transaction.objects.create(user=self.bob,kind='income',category=bob_cat,amount=1,date=date(2026,10,1))
        Budget.objects.create(user=self.bob,month=date(2026,10,1),amount=1)
        state=getting_started(self.user)
        self.assertEqual((state['completed'],state['budget'],state['complete']),(0,False,False))
        add_defaults(self.user,['salary'])
        self.assertEqual(getting_started(self.user)['completed'],1)
        cat=Category.objects.get(user=self.user)
        Transaction.objects.create(user=self.user,kind='income',category=cat,amount=Decimal('50000'),date=date(2026,10,1))
        state=getting_started(self.user)
        self.assertEqual((state['completed'],state['budget'],state['complete']),(2,False,True))
        self.assertFalse(MonthlyCoverage.objects.exists())
        Budget.objects.create(user=self.user,month=date(2026,10,1),amount=1)
        self.assertTrue(getting_started(self.user)['budget'])
        page=self.client.get(reverse('finance:dashboard'))
        self.assertContains(page,'Bắt đầu với Sổ Thu Chi')
        self.assertTrue(page.context['getting_started']['complete'])

    @patch('finance.views.suggest_label',return_value='Education')
    def test_existing_suggestion_flow_finds_only_explicit_owned_sample(self,predict):
        url=reverse('finance:category_suggestion')
        data={'description':'Đóng học phí','kind':'expense','mode':'vi'}
        self.assertEqual(self.client.post(url,data).json()['categories'],[])
        add_defaults(self.bob,['education'])
        add_defaults(self.user,['education'])
        own=Category.objects.get(user=self.user)
        for mode in ['vi','en']:
            result=self.client.post(url,{**data,'mode':mode}).json()
            self.assertEqual(result['categories'],[{'id':own.pk,'name':'Giáo dục'}])
        wrong=self.client.post(url,{**data,'kind':'income'}).json()
        self.assertEqual(wrong['status'],'review')
        self.assertEqual(Transaction.objects.count(),0)


class ExistingDataTests(FinanceCase):
    def test_existing_finance_feedback_and_mapping_unchanged(self):
        receipt=ClassificationSuggestion.objects.create(user=self.alice,input_digest='a'*64,kind='expense',mode='vi',
            predicted_label='Restaurants',model_name='QA',model_sha256='b'*64,seal='c'*64,expires_at=timezone.now()+timedelta(minutes=5))
        ClassificationFeedback.objects.create(user=self.alice,transaction=self.alice_row,suggestion=receipt,mode='vi',
            model_name='QA',model_sha256='b'*64,predicted_label='Restaurants',final_category=self.food,
            final_category_name=self.food.name,final_label='Restaurants',applied=True,same_label=True)
        models=[m for m in apps.get_app_config('finance').get_models() if m is not Category]
        before={m.__name__:list(m.objects.order_by('pk').values()) for m in models}
        categories=list(Category.objects.order_by('pk').values())
        auth=list(User.objects.order_by('pk').values())
        add_defaults(self.alice,[item.key for item in DEFAULTS])
        self.assertEqual(before,{m.__name__:list(m.objects.order_by('pk').values()) for m in models})
        self.assertEqual(categories,list(Category.objects.filter(pk__in=[c['id'] for c in categories]).order_by('pk').values()))
        self.assertEqual(auth,list(User.objects.order_by('pk').values()))


class ConcurrentDefaultsTests(TransactionTestCase):
    def test_same_selection_concurrently_and_retry_does_not_duplicate(self):
        user=User.objects.create_user('qa-parallel-defaults')
        keys=[item.key for item in DEFAULTS]
        gate=Barrier(2);results=Queue()
        def worker():
            close_old_connections()
            try:
                own=User.objects.get(pk=user.pk);gate.wait(timeout=10)
                result=add_defaults(own,keys)
                results.put(('ok',len(result['created'])))
            except OperationalError as exc:results.put(('locked' if 'locked' in str(exc).lower() else 'error',0))
            except Exception as exc:results.put((type(exc).__name__,0))
            finally:close_old_connections()
        threads=[Thread(target=worker) for _ in range(2)]
        for t in threads:t.start()
        for t in threads:t.join(timeout=20)
        self.assertTrue(all(not t.is_alive() for t in threads))
        outcomes=[results.get_nowait() for _ in range(2)]
        self.assertIn('ok',[status for status,_ in outcomes],outcomes)
        for status,_ in outcomes:
            self.assertIn(status,['ok','locked'],outcomes)
            if status=='locked':add_defaults(user,keys)
        rows=Category.objects.filter(user=user)
        self.assertEqual(rows.count(),11)
        self.assertEqual(len({(r.kind,normalized_name(r.name)) for r in rows}),11)
        self.assertEqual(len(add_defaults(user,keys)['created']),0)
        self.assertIsNone(User.objects.get(pk=user.pk).last_login)
