from datetime import date, timedelta
from unittest.mock import patch
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.test import Client
from django.urls import reverse
from django.utils import timezone
from .account_forms import UsernameChangeForm
from .models import (Category, Transaction, MonthlyCoverage, ForecastResult,
                     ForecastDataVersion, CsvImportBatch, CsvImportReceipt)
from .tests import FinanceCase


class AccountManagementTests(FinanceCase):
    def setUp(self):
        super().setUp()
        self.url = reverse('account')

    def rename(self, username='alice_new', password=None, **extra):
        return self.client.post(self.url, {'action':'username','username-new_username':username,
            'username-current_password':self.password if password is None else password, **extra})

    def password_change(self, old=None, new='StrongNew!8392zPass', confirm=None, **extra):
        return self.client.post(self.url, {'action':'password',
            'password-old_password':self.password if old is None else old,
            'password-new_password1':new, 'password-new_password2':new if confirm is None else confirm, **extra})

    def finance_snapshot(self):
        return {m.__name__:list(m.objects.order_by('pk').values()) for m in [Category,Transaction,
            MonthlyCoverage,ForecastResult,ForecastDataVersion,CsvImportBatch,CsvImportReceipt]}

    def test_get_read_only_forms_passwords_empty_and_auth(self):
        before=list(User.objects.values());data=self.finance_snapshot()
        response=self.client.get(self.url, {'action':'username','username-new_username':'GET_must_not_change'})
        self.assertContains(response,'alice')
        self.assertContains(response,'id="username-change-form"')
        self.assertContains(response,'id="password-change-form"')
        self.assertEqual(before,list(User.objects.values()))
        self.assertEqual(data,self.finance_snapshot())
        self.assertIn('no-store',response.headers['Cache-Control'])
        self.client.logout();self.assertEqual(self.client.get(self.url).status_code,302)

    def test_username_validation_current_password_and_normalized_duplicate(self):
        for name,pwd in [('new','bad'),('two words',self.password),('bad<script>',self.password),
                         ('x'*151,self.password),('bob',self.password),('ｂｏｂ',self.password),('',self.password)]:
            response=self.rename(name,pwd)
            self.assertTrue(response.context['username_form'].errors)
            self.alice.refresh_from_db();self.assertEqual(self.alice.username,'alice')
            self.assertFalse(response.context['password_form'].is_bound)

    def test_username_nfkc_user_pk_and_only_username_changes(self):
        second=Client();second.force_login(self.alice)
        before=User.objects.values().get(pk=self.alice.pk)
        response=self.rename('ａｌｉｃｅ＿ｎｅｗ',user_id=self.bob.pk,is_staff='1',is_superuser='1',new_password1='malicious')
        self.assertRedirects(response,self.url)
        after=User.objects.values().get(pk=self.alice.pk)
        self.assertEqual(after.pop('username'),'alice_new')
        before.pop('username');self.assertEqual(before,after)
        self.bob.refresh_from_db();self.assertEqual(self.bob.username,'bob')
        self.assertEqual(second.get(self.url).status_code,200)
        self.assertEqual(self.client.session['_auth_user_id'],str(self.alice.pk))
        login=Client()
        self.assertFalse(login.login(username='alice',password=self.password))
        self.assertTrue(login.login(username='alice_new',password=self.password))
        self.assertContains(self.client.get(self.url),'alice_new')

    def test_constraint_race_rolls_back_and_returns_error(self):
        original=UsernameChangeForm.save
        def claimed(form):
            User.objects.create_user(form.cleaned_data['new_username'])  # unusable password, test DB only
            return original(form)
        with patch.object(UsernameChangeForm,'save',claimed):
            response=self.rename('race_claim')
        self.assertContains(response,'đã được sử dụng')
        self.alice.refresh_from_db();self.assertEqual(self.alice.username,'alice')
        self.assertEqual(User.objects.get(username='race_claim').pk != self.alice.pk,True)

    def test_stale_password_between_validation_and_update_rejected(self):
        original=UsernameChangeForm.save
        def changed(form):
            User.objects.filter(pk=form.user.pk).update(password='!unusable-test-race')
            return original(form)
        with patch.object(UsernameChangeForm,'save',changed):
            response=self.rename()
        self.assertContains(response,'Thông tin xác thực đã thay đổi')
        self.alice.refresh_from_db();self.assertEqual(self.alice.username,'alice')

    def test_password_wrong_old_weak_and_mismatch_never_changes_hash(self):
        oldhash=self.alice.password
        for args in [{'old':'bad'}, {'new':'123'}, {'confirm':'Different!639zPass'},
                     {'new':'alice'}, {'new':'123456789012'}]:
            response=self.password_change(**args)
            self.assertTrue(response.context['password_form'].errors)
            self.assertFalse(response.context['username_form'].is_bound)
            self.alice.refresh_from_db();self.assertEqual(self.alice.password,oldhash)
            for name in ['old_password','new_password1','new_password2']:
                self.assertNotIn('value=',str(response.context['password_form'][name]))

    def test_password_success_keeps_current_and_invalidates_other_session(self):
        second=Client();self.assertTrue(second.login(username='alice',password=self.password))
        before=User.objects.values().get(pk=self.alice.pk)
        oldsession=self.client.session.session_key
        response=self.password_change(user_id=self.bob.pk,is_staff='1',username='not_saved')
        self.assertRedirects(response,self.url)
        self.assertEqual(self.client.session['_auth_user_id'],str(self.alice.pk))
        self.assertNotEqual(self.client.session.session_key,oldsession)
        self.assertEqual(self.client.get(self.url).status_code,200)
        self.assertEqual(second.get(self.url).status_code,302)
        self.assertNotIn('_auth_user_id',second.session)
        after=User.objects.values().get(pk=self.alice.pk)
        before.pop('password');stored=after.pop('password');self.assertEqual(before,after)
        self.assertNotEqual(stored,'StrongNew!8392zPass')
        self.alice.refresh_from_db();self.assertTrue(self.alice.check_password('StrongNew!8392zPass'))
        self.bob.refresh_from_db();self.assertTrue(self.bob.check_password(self.password))
        login=Client();self.assertFalse(login.login(username='alice',password=self.password))
        self.assertTrue(login.login(username='alice',password='StrongNew!8392zPass'))

    def test_all_linked_data_preserved_after_both_changes(self):
        MonthlyCoverage.objects.create(user=self.alice,month=date(2026,9,1),status='unknown')
        batch=CsvImportBatch.objects.create(user=self.alice,sha256='a'*64,raw=b'',
            expires_at=timezone.now()+timedelta(minutes=30),status='completed')
        CsvImportReceipt.objects.create(user=self.alice,sha256='a'*64,batch=batch,transaction_count=1)
        ForecastResult.objects.create(user=self.alice,target_month=date(2026,10,1),fingerprint='b'*64,
            history_count=3,history_start=date(2026,7,1),history_end=date(2026,9,1),
            method='mean3',estimate='100',details={},configuration={})
        before=self.finance_snapshot()
        self.assertEqual(self.rename().status_code,302)
        self.assertEqual(self.password_change().status_code,302)
        self.assertEqual(before,self.finance_snapshot())

    def test_csrf_action_security_and_no_passwords_in_redirect(self):
        secure=Client(enforce_csrf_checks=True);secure.force_login(self.alice)
        for action in ['username','password']:
            self.assertEqual(secure.post(self.url,{'action':action}).status_code,403)
        page=secure.get(self.url);csrf=page.cookies['csrftoken'].value
        response=secure.post(self.url,{'action':'unknown'},HTTP_X_CSRFTOKEN=csrf)
        self.assertEqual(response.status_code,400)
        self.assertEqual(response.wsgi_request.sensitive_post_parameters,'__ALL__')
        response=self.password_change()
        self.assertEqual(response.headers['Location'],self.url)
        self.assertNotIn('?',response.headers['Location'])

    def test_unrelated_account_cannot_change_target_by_post_id(self):
        self.client.force_login(self.bob)
        response=self.rename('bob_new',user_id=self.alice.pk)
        self.assertEqual(response.status_code,302)
        self.alice.refresh_from_db();self.bob.refresh_from_db()
        self.assertEqual(self.alice.username,'alice');self.assertEqual(self.bob.username,'bob_new')
