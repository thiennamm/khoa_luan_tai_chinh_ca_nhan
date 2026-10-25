from datetime import date, datetime, UTC
from unittest.mock import patch
from django.apps import apps
from django.test import SimpleTestCase, Client, RequestFactory
from django.urls import reverse
from django.utils import timezone
from .quick_entry import parse_entry, QuickEntryError, MAX_AMOUNT
from .quick_entry_views import analyze
from .tests import FinanceCase
from .models import Transaction, ClassificationFeedback


class QuickParserTests(SimpleTestCase):
    def parse(self, text):
        with patch('finance.quick_entry.timezone.localdate', return_value=date(2026, 10, 25)):
            return parse_entry(text)

    def test_supported_money_units_and_decimal_exactness(self):
        for token, amount in [('45k', '45000'), ('45 K', '45000'), ('45 nghìn', '45000'),
                              ('1,5 triệu', '1500000'), ('45000đ', '45000'), ('45000 ₫', '45000'),
                              ('45000 VND', '45000'), ('0,001k', '1'), ('0,000001 triệu', '1'),
                              ('999999999999999đ', str(MAX_AMOUNT))]:
            with self.subTest(token=token):
                result = self.parse('Chi: Ăn trưa ' + token + ' hôm nay')
                self.assertEqual(result['fields'], {'amount': amount, 'date': '2026-10-25',
                    'kind': 'expense', 'description': 'Ăn trưa'})

    def test_explicit_kind_only_and_default_date_explained(self):
        for prefix, expected in [('Thu:', 'income'), ('THU NHẬP:', 'income'),
                                 ('Chi tiêu:', 'expense'), ('Thu Hoài gửi ', ''), ('Ăn trưa ', '')]:
            result = self.parse(prefix + ' quà 45k')
            self.assertEqual(result['fields']['kind'], expected)
            self.assertTrue(result['date_defaulted'])
            self.assertTrue(any('25/10/2026' in warning for warning in result['warnings']))
        self.assertEqual(self.parse('Nhận chuyển khoản 45k')['fields']['kind'], '')

    def test_supported_dates_leap_year_and_future_keeps_general_policy(self):
        self.assertEqual(self.parse('Ăn 45k hôm qua')['fields']['date'], '2026-10-24')
        self.assertEqual(self.parse('Ăn 45k 29/02/2024')['fields']['date'], '2024-02-29')
        result = self.parse('Ăn 45k 26/10/2026')
        self.assertEqual(result['fields']['date'], '2026-10-26')
        self.assertTrue(any('tương lai' in warning for warning in result['warnings']))

    def test_vietnam_midnight_and_new_year(self):
        with timezone.override('Asia/Ho_Chi_Minh'):
            for utc, expected in [(datetime(2026, 12, 31, 16, 59, tzinfo=UTC), '2026-12-31'),
                                  (datetime(2026, 12, 31, 17, 1, tzinfo=UTC), '2027-01-01')]:
                with patch('django.utils.timezone.now', return_value=utc):
                    self.assertEqual(parse_entry('Ăn 45k')['fields']['date'], expected)
            with patch('django.utils.timezone.now', return_value=datetime(2026, 12, 31, 17, 1, tzinfo=UTC)):
                self.assertEqual(parse_entry('Ăn 45k hôm qua')['fields']['date'], '2026-12-31')

    def test_ambiguous_and_unsupported_input_never_returns_partial_fields(self):
        invalid = ['', '   ', 'x'*501, 'Ăn 45k\nCà phê', '45k 50k', '45k hôm nay hôm qua',
            '45k hôm nay 25/10/2026', '45k 31/02/2026', '45k 29/02/2025', '45k 2/3/2026',
            '45k 2026-10-25', '45k 25/10', '45k ngày mai', '45k hôm kia',
            '0901234567', 'Hóa đơn 123456', 'Ăn 45000 hôm nay', '25/10/2026',
            '-45k', '−45k', '+45k', 'ăn-45k', 'HD+45k', '—45k', '0đ', '1000000000000000đ', '0,0001k',
            '1.5 triệu', '1.000đ', '45 000đ', '1,000đ', '45 USD', '45k USD',
            '45k và 1 tỷ', '45k và 5000 đồng', '45k cộng 5 đô la', '45k và5000đồng',
            '45k vàabc50k', 'abc45k',
            'Thu: tiền Chi: 45k']
        for text in invalid:
            with self.subTest(text=text):
                with self.assertRaises(QuickEntryError) as caught:
                    self.parse(text)
                self.assertTrue(caught.exception.errors)
                self.assertEqual(str(caught.exception), 'Quick entry rejected')

    def test_preserves_unknown_numbers_and_html_as_description(self):
        text = 'Chi: hóa đơn 123456, ĐT 0901234567 <b>ghi chú</b> 45k hôm nay'
        result = self.parse(text)
        self.assertEqual(result['fields']['description'], 'hóa đơn 123456, ĐT 0901234567 <b>ghi chú</b>')
        self.assertTrue(any('giữ nguyên' in warning for warning in result['warnings']))
        self.assertEqual(self.parse('x'*496 + ' 1k')['fields']['description'], 'x'*496)
        self.assertEqual(self.parse('Ăn cùng đồng nghiệp 45k')['fields']['description'], 'Ăn cùng đồng nghiệp')


class QuickEndpointTests(FinanceCase):
    def setUp(self):
        super().setUp()
        self.url = reverse('finance:quick_entry')

    def test_post_login_csrf_and_no_cache(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)
        self.client.logout()
        self.assertEqual(self.client.post(self.url, {'text': 'Ăn 45k'}).status_code, 302)
        secure = Client(enforce_csrf_checks=True)
        secure.force_login(self.alice)
        self.assertEqual(secure.post(self.url, {'text': 'Ăn 45k'}).status_code, 403)
        secure.get(reverse('finance:transaction_create'))
        result = secure.post(self.url, {'text': 'Ăn 45k'}, HTTP_X_CSRFTOKEN=secure.cookies['csrftoken'].value)
        self.assertEqual(result.status_code, 200)
        self.assertIn('no-store', result['Cache-Control'])

    def test_analysis_has_no_queries_inference_or_financial_writes(self):
        before = {m.__name__: list(m.objects.values()) for m in apps.get_app_config('finance').get_models()}
        request = RequestFactory().post(self.url, {'text': 'Ăn 45k hôm nay', 'user_id': self.bob.pk})
        request.user = self.alice
        with patch('finance.views.suggest_label') as model, self.assertNumQueries(0):
            self.assertEqual(analyze(request).status_code, 200)
            model.assert_not_called()
        after = {m.__name__: list(m.objects.values()) for m in apps.get_app_config('finance').get_models()}
        self.assertEqual(before, after)
        response = self.client.post(self.url, {'text': 'Ăn 45k'})
        self.assertEqual(set(response.json()['fields']), {'amount', 'date', 'kind', 'description'})
        self.assertNotIn(self.bob_category.name, response.content.decode())

    def test_invalid_empty_long_and_duplicate_fields(self):
        for payload in [{}, {'text': ''}, {'text': 'x'*501}, {'text': '2k 3k'}, {'text': ['45k','50k']}]:
            result = self.client.post(self.url, payload)
            self.assertEqual(result.status_code, 400)
            self.assertNotIn('fields', result.json())

    def test_prefill_untrusted_and_stale_receipt_rechecked_on_save(self):
        self.food.canonical_label = 'Restaurants'
        self.food.save()
        initial = {'description': 'Mua cơm', 'kind': 'expense', 'mode': 'vi'}
        with patch('finance.views.suggest_label', return_value='Restaurants'):
            token = self.client.post(reverse('finance:category_suggestion'), initial).json()['suggestion_id']
        parsed = self.client.post(self.url, {'text': 'Chi: Ăn trưa 45k hôm nay'}).json()['fields']
        target = reverse('finance:transaction_create')
        data = {**parsed, 'category': self.food.pk, 'suggestion_mode': 'vi', 'suggestion_id': token}
        before = Transaction.objects.count()
        self.assertContains(self.client.post(target, data), 'Gợi ý không còn hợp lệ')
        self.assertEqual(Transaction.objects.count(), before)
        self.assertEqual(ClassificationFeedback.objects.count(), 0)
        with patch('finance.views.suggest_label', return_value='Restaurants'):
            token = self.client.post(reverse('finance:category_suggestion'), {**parsed, 'mode':'vi'}).json()['suggestion_id']
        self.assertEqual(self.client.post(reverse('finance:suggestion_action'), {**parsed, 'mode':'vi',
            'action':'apply', 'category':self.food.pk, 'suggestion_id':token}).status_code, 200)
        data['suggestion_id'] = token
        self.assertEqual(self.client.post(target, data).status_code, 302)
        feedback = ClassificationFeedback.objects.get()
        self.assertTrue(feedback.applied and feedback.same_label)
        self.assertEqual(feedback.transaction.amount, 45000)
        for changes in [{'amount':'0'}, {'category':self.bob_category.pk}, {'kind':'income'}]:
            self.assertEqual(self.client.post(target, {**parsed,'category':self.food.pk,**changes}).status_code, 200)
        self.assertEqual(Transaction.objects.count(), before + 1)
