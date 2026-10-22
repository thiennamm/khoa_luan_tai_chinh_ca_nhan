from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import Client, TestCase
from django.urls import reverse

from .forms import TransactionForm
from .models import Category, Kind, Transaction
from .services import monthly_totals
from .templatetags.money import vnd


class FinanceCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Chỉ tồn tại trong cơ sở dữ liệu kiểm thử riêng của Django.
        cls.password = 'OnlyForTests!8391'
        cls.alice = User.objects.create_user('alice', password=cls.password)
        cls.bob = User.objects.create_user('bob', password=cls.password)
        cls.salary = Category.objects.create(user=cls.alice, name='Lương riêng', kind=Kind.INCOME)
        cls.food = Category.objects.create(user=cls.alice, name='Ăn uống riêng', kind=Kind.EXPENSE)
        cls.bob_category = Category.objects.create(user=cls.bob, name='Danh mục bí mật Bob', kind=Kind.EXPENSE)
        cls.alice_row = Transaction.objects.create(user=cls.alice, category=cls.food, kind=Kind.EXPENSE,
            amount=Decimal('125000'), date=date(2026, 10, 1), description='Giao dịch riêng Alice')
        cls.bob_row = Transaction.objects.create(user=cls.bob, category=cls.bob_category, kind=Kind.EXPENSE,
            amount=Decimal('987654'), date=date(2026, 10, 1), description='Giao dịch bí mật Bob')

    def setUp(self):
        self.client.force_login(self.alice)

    def payload(self, **changes):
        data = {'kind': Kind.EXPENSE, 'amount': '250000', 'date': '2026-10-20',
                'category': self.food.pk, 'description': 'Khoản chi'}
        data.update(changes)
        return data


class IsolationTests(FinanceCase):
    def test_lists_and_dashboard_do_not_leak_other_user(self):
        for route in ['transaction_list', 'dashboard']:
            with self.subTest(route=route):
                response = self.client.get(reverse('finance:' + route), {'month': '2026-10'})
                self.assertEqual(response.status_code, 200)
                self.assertNotContains(response, 'Giao dịch bí mật Bob')
                self.assertNotContains(response, '987.654')
        response = self.client.get(reverse('finance:category_list'))
        self.assertContains(response, 'Ăn uống riêng')
        self.assertNotContains(response, 'Danh mục bí mật Bob')

    def test_foreign_transaction_access_is_denied(self):
        for route in ['transaction_detail', 'transaction_edit', 'transaction_delete']:
            url = reverse('finance:' + route, args=[self.bob_row.pk])
            self.assertEqual(self.client.get(url).status_code, 404)
            expected = 405 if route == 'transaction_detail' else 404
            self.assertEqual(self.client.post(url, self.payload()).status_code, expected)
        self.bob_row.refresh_from_db()
        self.assertEqual(self.bob_row.amount, Decimal('987654'))

    def test_foreign_category_get_and_post_return_404(self):
        for route in ['category_edit', 'category_delete']:
            url = reverse('finance:' + route, args=[self.bob_category.pk])
            self.assertEqual(self.client.get(url).status_code, 404)
            self.assertEqual(self.client.post(url, {'name': 'Changed', 'kind': Kind.INCOME}).status_code, 404)
        self.bob_category.refresh_from_db()
        self.assertEqual(self.bob_category.name, 'Danh mục bí mật Bob')

    def test_category_choices_only_include_own_categories(self):
        response = self.client.get(reverse('finance:transaction_create'))
        ids = set(response.context['form'].fields['category'].queryset.values_list('pk', flat=True))
        self.assertEqual(ids, {self.food.pk, self.salary.pk})
        self.assertNotContains(response, 'Danh mục bí mật Bob')

    def test_forged_category_rejected_on_create_and_update(self):
        count = Transaction.objects.count()
        for url in [reverse('finance:transaction_create'), reverse('finance:transaction_edit', args=[self.alice_row.pk])]:
            response = self.client.post(url, self.payload(category=self.bob_category.pk))
            self.assertEqual(response.status_code, 200)
            self.assertIn('category', response.context['form'].errors)
        self.assertEqual(Transaction.objects.count(), count)
        self.alice_row.refresh_from_db()
        self.assertEqual(self.alice_row.category_id, self.food.pk)

    def test_posted_owner_is_ignored(self):
        response = self.client.post(reverse('finance:transaction_create'), self.payload(user=self.bob.pk))
        self.assertEqual(response.status_code, 302)
        row = Transaction.objects.latest('pk')
        self.assertEqual(row.user_id, self.alice.pk)
        response = self.client.post(reverse('finance:category_create'), {'name': 'Mới', 'kind': Kind.INCOME, 'user': self.bob.pk})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Category.objects.latest('pk').user_id, self.alice.pk)

    def test_anonymous_management_redirects_to_login(self):
        self.client.logout()
        urls = [reverse('finance:' + name) for name in ['dashboard', 'transaction_list', 'transaction_create', 'category_list', 'category_create']]
        urls += [reverse('finance:' + name, args=[self.alice_row.pk]) for name in ['transaction_detail', 'transaction_edit', 'transaction_delete']]
        urls += [reverse('finance:' + name, args=[self.food.pk]) for name in ['category_edit', 'category_delete']]
        for url in urls:
            for method in [self.client.get, self.client.post]:
                with self.subTest(url=url, method=method.__name__):
                    response = method(url)
                    self.assertEqual(response.status_code, 302)
                    self.assertTrue(response.url.startswith(reverse('login') + '?next='))


class ValidationTests(FinanceCase):
    def test_invalid_amounts_are_rejected(self):
        for value in ['0', '-1', '1.5', 'NaN', 'Infinity', 'abc', '1000000000000000', '']:
            with self.subTest(amount=value):
                response = self.client.post(reverse('finance:transaction_create'), self.payload(amount=value))
                self.assertEqual(response.status_code, 200)
                self.assertIn('amount', response.context['form'].errors)
        self.assertEqual(Transaction.objects.filter(user=self.alice).count(), 1)

    def test_mismatched_category_is_rejected(self):
        response = self.client.post(reverse('finance:transaction_create'), self.payload(category=self.salary.pk))
        self.assertIn('category', response.context['form'].errors)

    def test_invalid_fields_are_rejected(self):
        for field, value in [('date', '2026-02-30'), ('date', ''), ('kind', 'other'), ('category', '999999'), ('description', 'x' * 501)]:
            with self.subTest(field=field, value=value):
                response = self.client.post(reverse('finance:transaction_create'), self.payload(**{field: value}))
                self.assertEqual(response.status_code, 200)
                self.assertIn(field, response.context['form'].errors)

    def test_model_rejects_foreign_or_mismatched_category(self):
        for category in [self.bob_category, self.salary]:
            with self.assertRaises(ValidationError):
                Transaction.objects.create(user=self.alice, category=category, kind=Kind.EXPENSE,
                    amount=Decimal('1'), date=date(2026, 10, 20))

    def test_database_blocks_nonpositive_amount_even_if_validation_bypassed(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Transaction.objects.filter(pk=self.alice_row.pk).update(amount=Decimal('0'))

    def test_decimal_round_trip_and_edit(self):
        response = self.client.post(reverse('finance:transaction_edit', args=[self.alice_row.pk]),
            self.payload(kind=Kind.INCOME, category=self.salary.pk, amount='999999999999999'))
        self.assertEqual(response.status_code, 302)
        self.alice_row.refresh_from_db()
        self.assertIsInstance(self.alice_row.amount, Decimal)
        self.assertEqual(self.alice_row.amount, Decimal('999999999999999'))
        self.assertEqual(self.alice_row.kind, Kind.INCOME)

    def test_get_delete_does_not_delete_and_post_does(self):
        url = reverse('finance:transaction_delete', args=[self.alice_row.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertTrue(Transaction.objects.filter(pk=self.alice_row.pk).exists())
        self.assertEqual(self.client.post(url).status_code, 302)
        self.assertFalse(Transaction.objects.filter(pk=self.alice_row.pk).exists())

    def test_used_category_cannot_change_kind_or_be_deleted(self):
        response = self.client.post(reverse('finance:category_edit', args=[self.food.pk]), {'name': self.food.name, 'kind': Kind.INCOME})
        self.assertIn('kind', response.context['form'].errors)
        self.food.refresh_from_db()
        self.assertEqual(self.food.kind, Kind.EXPENSE)
        response = self.client.post(reverse('finance:category_delete', args=[self.food.pk]), follow=True)
        self.assertContains(response, 'Không thể xóa danh mục')
        self.assertTrue(Category.objects.filter(pk=self.food.pk).exists())

    def test_category_rename_and_unused_delete(self):
        response = self.client.post(reverse('finance:category_edit', args=[self.food.pk]), {'name': 'Tên mới', 'kind': Kind.EXPENSE})
        self.assertEqual(response.status_code, 302)
        self.food.refresh_from_db()
        self.assertEqual(self.food.name, 'Tên mới')
        self.assertEqual(self.client.post(reverse('finance:category_delete', args=[self.salary.pk])).status_code, 302)
        self.assertFalse(Category.objects.filter(pk=self.salary.pk).exists())

    def test_duplicate_category_in_same_account_rejected(self):
        response = self.client.post(reverse('finance:category_create'), {'name': self.food.name, 'kind': Kind.EXPENSE})
        self.assertIn('name', response.context['form'].errors)
        response = self.client.post(reverse('finance:category_create'), {'name': self.bob_category.name, 'kind': Kind.EXPENSE})
        self.assertEqual(response.status_code, 302)


class SummaryTests(FinanceCase):
    def test_month_totals_boundaries_and_user_scope(self):
        for day, amount in [(date(2026, 9, 30), '999999'), (date(2026, 10, 1), '5000000'), (date(2026, 10, 31), '1000000'), (date(2026, 11, 1), '888888')]:
            Transaction.objects.create(user=self.alice, category=self.salary, kind=Kind.INCOME, amount=Decimal(amount), date=day)
        response = self.client.get(reverse('finance:dashboard'), {'month': '2026-10'})
        self.assertEqual(response.context['income'], Decimal('6000000'))
        self.assertEqual(response.context['expense'], Decimal('125000'))
        self.assertEqual(response.context['balance'], Decimal('5875000'))
        self.assertEqual(response.context['transaction_count'], 3)
        self.assertContains(response, '6.000.000 ₫')

    def test_negative_balance(self):
        response = self.client.get(reverse('finance:dashboard'), {'month': '2026-10'})
        self.assertEqual(response.context['balance'], Decimal('-125000'))

    def test_empty_month(self):
        response = self.client.get(reverse('finance:dashboard'), {'month': '2025-01'})
        self.assertEqual(response.context['income'], Decimal('0'))
        self.assertEqual(response.context['expense'], Decimal('0'))
        self.assertEqual(response.context['balance'], Decimal('0'))
        self.assertContains(response, 'Tháng này chưa ghi nhận giao dịch')

    def test_large_sums_remain_exact_decimal(self):
        for _ in range(11):
            Transaction.objects.create(user=self.alice, category=self.salary, kind=Kind.INCOME,
                amount=Decimal('999999999999999'), date=date(2026, 10, 20))
        totals = monthly_totals(self.alice, date(2026, 10, 1), date(2026, 11, 1))
        self.assertEqual(totals['income'], Decimal('10999999999999989'))
        self.assertIsInstance(totals['balance'], Decimal)

    def test_december_rolls_into_next_year(self):
        response = self.client.get(reverse('finance:dashboard'), {'month': '2026-12'})
        self.assertEqual(response.context['end'], date(2027, 1, 1))

    def test_invalid_month_does_not_crash(self):
        for value in ['not-a-month', '2026-13', '', '9999-12']:
            with self.subTest(month=value):
                response = self.client.get(reverse('finance:dashboard'), {'month': value})
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context['month_form'].errors)

    def test_list_filters_month(self):
        response = self.client.get(reverse('finance:transaction_list'), {'month': '2026-09'})
        self.assertEqual(response.context['page_obj'].paginator.count, 0)

    def test_vnd_formatting(self):
        self.assertEqual(vnd(Decimal('123456789')), '123.456.789 ₫')
        self.assertEqual(vnd(Decimal('-500')), '-500 ₫')


class AuthenticationTests(TestCase):
    def test_signup_hashes_password_and_starts_empty(self):
        response = self.client.post(reverse('signup'), {
            'username': 'new-person', 'password1': 'Unique!8392Test', 'password2': 'Unique!8392Test',
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        user = User.objects.get(username='new-person')
        self.assertTrue(user.check_password('Unique!8392Test'))
        self.assertEqual(str(user.pk), self.client.session['_auth_user_id'])
        self.assertEqual(Category.objects.count(), 0)
        self.assertEqual(Transaction.objects.count(), 0)
        self.assertContains(response, 'Tháng này chưa ghi nhận giao dịch')

    def test_weak_password_rejected(self):
        response = self.client.post(reverse('signup'), {'username': 'new', 'password1': '123', 'password2': '123'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].errors)
        self.assertEqual(User.objects.count(), 0)

    def test_login_and_post_logout(self):
        user = User.objects.create_user('test-person', password='Unique!8392Test')
        response = self.client.post(reverse('login'), {'username': user.username, 'password': 'Unique!8392Test'})
        self.assertRedirects(response, reverse('finance:dashboard'))
        self.assertEqual(self.client.get(reverse('logout')).status_code, 405)
        self.assertIn('_auth_user_id', self.client.session)
        self.assertRedirects(self.client.post(reverse('logout')), reverse('login'))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_external_next_url_cannot_redirect_off_site(self):
        User.objects.create_user('test-person', password='Unique!8392Test')
        response = self.client.post(reverse('login'), {'username': 'test-person', 'password': 'Unique!8392Test', 'next': 'https://example.org/'})
        self.assertRedirects(response, reverse('finance:dashboard'))

    def test_csrf_required_on_mutating_routes(self):
        secure_client = Client(enforce_csrf_checks=True)
        for route in ['signup', 'login']:
            self.assertEqual(secure_client.post(reverse(route), {}).status_code, 403)
        user = User.objects.create_user('test-person', password='Unique!8392Test')
        secure_client.force_login(user)
        for route in ['logout', 'finance:transaction_create', 'finance:category_create']:
            self.assertEqual(secure_client.post(reverse(route), {}).status_code, 403)

    def test_description_is_escaped(self):
        user = User.objects.create_user('test-person', password='Unique!8392Test')
        category = Category.objects.create(user=user, name='Test', kind=Kind.EXPENSE)
        row = Transaction.objects.create(user=user, category=category, kind=Kind.EXPENSE, amount=Decimal('1'), description='<script>alert(1)</script>')
        self.client.force_login(user)
        response = self.client.get(reverse('finance:transaction_detail', args=[row.pk]))
        self.assertContains(response, '&lt;script&gt;alert(1)&lt;/script&gt;')
        self.assertNotContains(response, '<script>alert(1)</script>')
