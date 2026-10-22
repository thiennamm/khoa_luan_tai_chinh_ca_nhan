from datetime import date
from decimal import Decimal
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit
from django.urls import reverse
from .models import Transaction, Category
from .tests import FinanceCase


class TransactionFilterTests(FinanceCase):
    def setUp(self):
        super().setUp()
        self.url = reverse('finance:transaction_list')

    def row(self, text='ĐIỆN QA', day=date(2026, 10, 15), amount='100', kind='expense', category=None):
        return Transaction.objects.create(user=self.alice, description=text, date=day,
            amount=Decimal(amount), kind=kind, category=category or (self.salary if kind == 'income' else self.food))

    def get(self, **params):
        return self.client.get(self.url, {'month': '2026-10', **params})

    def test_default_month_and_owner(self):
        self.row(day=date(2026, 9, 30))
        with patch('finance.transaction_filters.timezone.localdate', return_value=date(2026, 10, 21)):
            response = self.client.get(self.url)
        self.assertEqual(response.context['result_count'], 1)
        self.assertEqual(response.context['expense'], Decimal('125000'))
        self.assertNotContains(response, self.bob_row.description)
        self.assertEqual(parse_qs(response.context['filter_query'])['month'], ['2026-10'])

    def test_unicode_casefold_substring_and_literal_sql_wildcards(self):
        row = self.row('Thanh toán ĐIỆN nhà 100%_x')
        self.row('Thanh toán khác 10000ax')
        for query in ['điện', 'ĐIỆN', 'toán đIỆn', '100%_x']:
            response = self.get(q=query)
            self.assertEqual([r.pk for r in response.context['page_obj']], [row.pk])
        self.assertEqual(self.get(q="' OR 1=1 --").context['result_count'], 0)

    def test_combined_kind_category_description_and_dates(self):
        target = self.row('Tiền điện', day=date(2026, 10, 31))
        self.row('Tiền điện', kind='income')
        self.row('Tiền điện', day=date(2026, 11, 1))
        response = self.get(period='range', start='2026-10-31', end='2026-10-31',
                            q='ĐIỆN', kind='expense', category=self.food.pk)
        self.assertEqual([r.pk for r in response.context['page_obj']], [target.pk])
        self.assertEqual(response.context['expense'], Decimal('100'))
        self.assertEqual(self.get(kind='income', category=self.food.pk).context['result_count'], 0)

    def test_inclusive_range_cross_year_and_leap_day(self):
        for day in [date(2024, 2, 28), date(2024, 2, 29), date(2024, 3, 1)]:
            self.row(day=day)
        response = self.get(period='range', start='2024-02-29', end='2024-03-01')
        self.assertEqual(response.context['result_count'], 2)
        for day in [date(2025, 12, 31), date(2026, 1, 1)]:
            self.row(day=day)
        self.assertEqual(self.get(period='range', start='2025-12-31', end='2026-01-01').context['result_count'], 2)

    def test_modes_never_overlap_even_with_invalid_inactive_values(self):
        self.row(day=date(2026, 9, 1))
        month = self.get(period='month', start='bad', end='bad')
        self.assertTrue(month.context['filters_valid'])
        self.assertEqual(month.context['result_count'], 1)
        ranged = self.get(period='range', month='bad', start='2026-09-01', end='2026-09-01')
        self.assertTrue(ranged.context['filters_valid'])
        self.assertEqual(ranged.context['result_count'], 1)

    def test_invalid_inputs_no_silent_fallback_or_partial_results(self):
        for payload in [{'month':'2026-99'}, {'month':''}, {'month':'0000-01'},
                        {'period':'bad'}, {'kind':'other'}, {'q':'x'*501},
                        {'period':'range','start':'2026-10-20','end':'2026-10-01'},
                        {'period':'range','start':'2026-02-30','end':'2026-03-01'},
                        {'period':'range','start':'2026-01-01'}, {'period':'range'}]:
            with self.subTest(payload=payload):
                response = self.get(**payload)
                self.assertFalse(response.context['filters_valid'])
                self.assertEqual(response.context['result_count'], 0)
                self.assertContains(response, 'Bộ lọc chưa hợp lệ')
                self.assertNotContains(response, self.alice_row.description)

    def test_foreign_and_nonexistent_categories_have_same_generic_error(self):
        errors = []
        for pk in [self.bob_category.pk, 9999999, 'not-an-id']:
            response = self.get(category=pk)
            self.assertFalse(response.context['filters_valid'])
            errors.append(str(response.context['filter_form'].errors['category']))
            self.assertNotContains(response, self.bob_category.name)
            self.assertNotContains(response, self.bob_row.description)
        self.assertEqual(errors[0], errors[1])
        self.assertEqual(errors[0], errors[2])

    def test_stable_pagination_totals_over_all_pages_and_preserved_filters(self):
        made=[self.row('ĐIỆN & nước', amount='999999999999999') for _ in range(25)]
        params={'period':'range','start':'2026-10-01','end':'2026-10-31',
                'q':'điện & nước','kind':'expense','category':str(self.food.pk)}
        one=self.get(**params)
        two=self.get(**params, page=2)
        self.assertEqual(len(one.context['page_obj']),20)
        self.assertEqual(len(two.context['page_obj']),5)
        for response in [one,two]:
            self.assertEqual(response.context['result_count'],25)
            self.assertEqual(response.context['expense'],Decimal('24999999999999975'))
            self.assertEqual(response.context['balance'],Decimal('-24999999999999975'))
            parsed=parse_qs(response.context['filter_query'])
            for name,value in params.items():self.assertEqual(parsed[name],[value])
            self.assertNotIn('page',parsed)
        ids=[r.pk for r in one.context['page_obj']]+[r.pk for r in two.context['page_obj']]
        self.assertEqual(ids,[r.pk for r in reversed(made)])

    def test_income_expense_and_zero_totals(self):
        self.row('lọc chung', amount='900',kind='income')
        self.row('lọc chung', amount='200')
        response=self.get(q='lọc chung')
        self.assertEqual((response.context['income'],response.context['expense'],response.context['balance']),
                         (Decimal('900'),Decimal('200'),Decimal('700')))
        empty=self.get(q='không thấy')
        self.assertEqual(empty.context['result_count'],0)
        self.assertContains(empty,'Không có kết quả phù hợp')

    def test_escaping_login_get_only_and_read_only(self):
        before={m.__name__:list(m.objects.values()) for m in [Transaction,Category]}
        response=self.get(q='<script>alert(1)</script>')
        self.assertContains(response,'&lt;script&gt;')
        self.assertNotContains(response,'<script>alert(1)</script>')
        for page in ['x','-1','9999999']:self.assertEqual(self.get(page=page).status_code,200)
        self.assertEqual(self.client.post(self.url).status_code,405)
        self.assertEqual(before,{m.__name__:list(m.objects.values()) for m in [Transaction,Category]})
        self.client.logout()
        self.assertEqual(self.get().status_code,302)

    def test_december_9999_no_overflow(self):
        self.assertTrue(self.get(month='9999-12').context['filters_valid'])
