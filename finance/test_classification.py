"""Dữ liệu thử chỉ ở test DB; không thay artifact hay huấn luyện."""
import hashlib
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from django.conf import settings
from django.core.exceptions import ValidationError
from django.test import Client, SimpleTestCase, override_settings
from django.urls import reverse

from . import classification
from .classification import ModelUnavailable, normalize_description
from .forms import CategoryForm
from .models import Category, Kind, Transaction
from .tests import FinanceCase


class SuggestionEndpointTests(FinanceCase):
    def setUp(self):
        super().setUp()
        self.url = reverse('finance:category_suggestion')
        self.food.canonical_label = 'Groceries'
        self.food.save()
        self.bob_category.canonical_label = 'Groceries'
        self.bob_category.save()

    def post(self, **changes):
        return self.client.post(self.url, {'description': 'purchase', 'kind': 'expense', **changes})

    @patch('finance.views.suggest_label', return_value='Groceries')
    def test_only_explicit_own_mapping_and_no_write(self, predict):
        Category.objects.create(user=self.alice, kind='expense', name='Groceries')  # cùng tên, không ánh xạ
        # Giả lập bản ghi sai loại từ bên ngoài Model.save; endpoint vẫn phải lọc.
        Category.objects.filter(pk=self.salary.pk).update(canonical_label='Groceries')
        before = (Transaction.objects.count(), Category.objects.count())
        data = self.post(user=self.bob.pk, model_path='untrusted.joblib').json()
        self.assertEqual(data['categories'], [{'id': self.food.pk, 'name': self.food.name}])
        self.assertEqual(data['label'], 'Groceries')
        self.assertNotIn('score', data)
        self.assertNotIn('probability', data)
        self.assertEqual(before, (Transaction.objects.count(), Category.objects.count()))
        self.alice_row.refresh_from_db()
        self.assertEqual(self.alice_row.category_id, self.food.pk)

    @patch('finance.views.suggest_label', return_value='Groceries')
    def test_multiple_mappings_return_all_without_selecting(self, predict):
        other = Category.objects.create(user=self.alice, kind='expense', name='Thực phẩm khác', canonical_label='Groceries')
        data = self.post().json()
        self.assertEqual({c['id'] for c in data['categories']}, {self.food.pk, other.pk})
        self.assertNotIn('selected_category', data)

    @patch('finance.views.suggest_label', return_value='Travel')
    def test_unmapped_label_does_not_create_category(self, predict):
        count = Category.objects.count()
        data = self.post().json()
        self.assertEqual(data['label'], 'Travel')
        self.assertEqual(data['categories'], [])
        self.assertEqual(Category.objects.count(), count)

    @patch('finance.views.suggest_label', return_value='Transfer')
    def test_transfer_always_review_even_if_corrupt_mapping_exists(self, predict):
        Category.objects.filter(pk=self.food.pk).update(canonical_label='Transfer')
        for kind in Kind.values:
            data = self.post(kind=kind).json()
            self.assertEqual(data['status'], 'review')
            self.assertEqual(data['categories'], [])

    @patch('finance.views.suggest_label', return_value='Income')
    def test_income_does_not_change_expense_kind(self, predict):
        self.salary.canonical_label = 'Income'
        self.salary.save()
        data = self.post().json()
        self.assertEqual(data['status'], 'review')
        self.assertEqual(data['categories'], [])
        data = self.post(kind='income').json()
        self.assertEqual([c['id'] for c in data['categories']], [self.salary.pk])

    def test_empty_and_prefix_only_without_loading(self):
        with patch('finance.classification.load_model') as load:
            for text in ['', '  \n ', '[DEBIT] ', ' [credit]  ']:
                self.assertEqual(self.post(description=text).json()['status'], 'no_suggestion')
            load.assert_not_called()

    @override_settings(CLASSIFICATION_MODEL_PATH='missing-local-model.joblib')
    def test_missing_model_still_allows_manual_transaction(self):
        response = self.post()
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()['status'], 'unavailable')
        self.assertEqual(self.client.get(reverse('finance:transaction_create')).status_code, 200)
        response = self.client.post(reverse('finance:transaction_create'), self.payload())
        self.assertEqual(response.status_code, 302)

    def test_auth_post_only_csrf_and_length(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)
        for payload in [{'description': 'x' * 501}, {'description': ' ' * 501}, {'kind': 'transfer'}]:
            with patch('finance.views.suggest_label') as predict:
                self.assertEqual(self.post(**payload).status_code, 400)
                predict.assert_not_called()
        secure = Client(enforce_csrf_checks=True)
        secure.force_login(self.alice)
        self.assertEqual(secure.post(self.url, {'description': 'test', 'kind': 'expense'}).status_code, 403)
        page = secure.get(reverse('finance:transaction_create'))
        csrf = page.cookies['csrftoken'].value
        with patch('finance.views.suggest_label', return_value=None):
            response = secure.post(self.url, {'description': '', 'kind': 'expense'}, HTTP_X_CSRFTOKEN=csrf)
        self.assertEqual(response.status_code, 200)
        self.assertIn('no-store', response.headers['Cache-Control'])
        self.client.logout()
        self.assertEqual(self.post().status_code, 302)

    def test_wrong_kind_and_transfer_mapping_rejected(self):
        for kind, label in [('expense', 'Income'), ('income', 'Groceries'), ('expense', 'Transfer')]:
            form = CategoryForm({'name': 'New', 'kind': kind, 'canonical_label': label}, user=self.alice)
            self.assertFalse(form.is_valid())
            self.assertIn('canonical_label', form.errors)
            with self.assertRaises(ValidationError):
                Category.objects.create(user=self.alice, name='Invalid', kind=kind, canonical_label=label)

    def test_mapping_used_category_changes_no_transaction(self):
        response = self.client.post(reverse('finance:category_edit', args=[self.food.pk]),
            {'name': self.food.name, 'kind': self.food.kind, 'canonical_label': 'Restaurants'})
        self.assertEqual(response.status_code, 302)
        self.alice_row.refresh_from_db()
        self.food.refresh_from_db()
        self.assertEqual(self.alice_row.category_id, self.food.pk)
        self.assertEqual(self.food.canonical_label, 'Restaurants')

    def test_form_controls_do_not_submit_suggestion(self):
        response = self.client.get(reverse('finance:transaction_edit', args=[self.alice_row.pk]))
        self.assertContains(response, 'type="button" id="suggest-category"')
        self.assertContains(response, 'type="button" id="apply-suggestion" disabled')
        self.assertContains(response, 'Gợi ý thử nghiệm')
        self.assertContains(response, 'dữ liệu tổng hợp tiếng Anh')
        self.assertContains(response, 'chưa được kiểm chứng cho tiếng Việt')


class InferenceTests(SimpleTestCase):
    def test_normalization_matches_audit(self):
        from scripts.audit_classification_data import body
        samples = [' [DeBiT]  CAFE\u0301 \nPAYMENT ', '[credit] AMAZON  123',
                   'word [debit] XYZ', '[debit] [credit] TWO', '', '\u00a0  ABC\t DEF']
        for sample in samples:
            self.assertEqual(normalize_description(sample), body(sample))
        self.assertEqual(normalize_description('[debit] [credit] TWO'), '[credit] two')

    def test_zero_vector_never_predicts(self):
        model = Mock()
        model.named_steps = {'tfidf': Mock()}
        model.named_steps['tfidf'].transform.return_value.nnz = 0
        with patch('finance.classification.load_model', return_value=model):
            self.assertIsNone(classification.suggest_label('🦖'))
        model.predict.assert_not_called()

    def test_pipeline_gets_only_normalized_text(self):
        model = Mock()
        model.named_steps = {'tfidf': Mock()}
        model.named_steps['tfidf'].transform.return_value.nnz = 3
        model.predict.return_value = ['Groceries']
        with patch('finance.classification.load_model', return_value=model):
            self.assertEqual(classification.suggest_label(' [DEBIT]  STORE \n Purchase'), 'Groceries')
        model.predict.assert_called_once_with(['store purchase'])
        model.fit.assert_not_called()

    def test_bad_hash_rejected_before_joblib_load_even_if_cache_exists(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'model.joblib'
            path.write_bytes(b'not a model')
            with override_settings(CLASSIFICATION_MODEL_PATH=path), patch('joblib.load') as load:
                with self.assertRaises(ModelUnavailable):
                    classification.suggest_label('purchase')
                load.assert_not_called()

    def test_modified_metadata_refuses_loading(self):
        data = json.loads(Path(settings.CLASSIFICATION_METADATA_PATH).read_text(encoding='utf-8'))
        data['selection']['selected_model_sha256'] = '0' * 64
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'metadata.json'
            path.write_text(json.dumps(data), encoding='utf-8')
            with override_settings(CLASSIFICATION_METADATA_PATH=path), patch('joblib.load') as load:
                with self.assertRaises(ModelUnavailable):
                    classification.suggest_label('purchase')
                load.assert_not_called()

    def test_runtime_error_becomes_unavailable(self):
        with patch('finance.classification.load_model', side_effect=OSError('DLL runtime')):
            with self.assertRaises(ModelUnavailable):
                classification.suggest_label('purchase')
