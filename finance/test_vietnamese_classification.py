"""Chỉ suy luận từ artifact đã khóa; không fit, sửa dữ liệu hoặc dùng DB thật."""
import hashlib
import json
import tempfile
import unicodedata
from pathlib import Path
from unittest.mock import Mock, patch

from django.conf import settings
from django.test import Client, SimpleTestCase, override_settings
from django.urls import reverse

from . import classification, classification_modes as modes
from .classification import ModelUnavailable
from .models import Category, Transaction
from .tests import FinanceCase


class VietnameseInferenceTests(SimpleTestCase):
    def test_real_artifacts_hashes_predictions_and_no_cli_adapter(self):
        # Cả hai artifact thật được đọc từ cấu hình máy chủ, không cần adapter CLI.
        import sys
        with patch('sklearn.pipeline.Pipeline.fit', side_effect=AssertionError('No fit')):
            en = classification.load_model()
            vi = modes.load_vietnamese_model()
            self.assertIsNot(en, vi)
            for path, expected in [(settings.CLASSIFICATION_MODEL_PATH, classification.EXPECTED_SHA256),
                                   (settings.VI_CLASSIFICATION_MODEL_PATH, modes.VI_SHA256)]:
                self.assertEqual(hashlib.sha256(Path(path).read_bytes()).hexdigest(), expected)
            self.assertEqual(modes.suggest_label('Đóng học phí học kỳ đại học', mode='vi'), 'Education')
            self.assertEqual(modes.suggest_label('Grocery shopping at Whole Foods', mode='en'), 'Groceries')
        self.assertNotIn('scripts.run_classification_windows', sys.modules)

    def test_routing_is_explicit_and_no_fallback(self):
        with patch.object(classification, 'suggest_label', return_value='Fees') as en, \
                patch.object(modes, 'load_vietnamese_model', side_effect=OSError) as vi:
            self.assertEqual(modes.suggest_label('text', mode='en'), 'Fees')
            en.assert_called_once_with('text')
            vi.assert_not_called()
            en.reset_mock()
            with self.assertRaises(ModelUnavailable):
                modes.suggest_label('text', mode='vi')
            en.assert_not_called()
            with self.assertRaises(ModelUnavailable):
                modes.suggest_label('text', mode='auto')

    def test_normalization_keeps_accents_and_removes_one_prefix(self):
        text = unicodedata.normalize('NFD', '  [CREDIT]  ĐÓNG\tHỌC PHÍ  ')
        model = Mock()
        model.named_steps = {'tfidf': Mock()}
        model.named_steps['tfidf'].transform.return_value.nnz = 2
        model.predict.return_value = ['Education']
        with patch.object(modes, 'load_vietnamese_model', return_value=model):
            self.assertEqual(modes.suggest_label(text, mode='vi'), 'Education')
        model.predict.assert_called_once_with(['đóng học phí'])
        model.fit.assert_not_called()
        self.assertEqual(modes.normalize_description('[debit] [credit] Học'), '[credit] học')

    def test_empty_and_zero_vector(self):
        with patch.object(modes, 'load_vietnamese_model') as load:
            for text in ['', '  ', '[debit] ']:
                self.assertIsNone(modes.suggest_label(text, mode='vi'))
            load.assert_not_called()
            load.return_value.named_steps = {'tfidf': Mock()}
            load.return_value.named_steps['tfidf'].transform.return_value.nnz = 0
            self.assertIsNone(modes.suggest_label('🧬', mode='vi'))
            load.return_value.predict.assert_not_called()

    def test_hash_metadata_manifest_checked_before_deserialization_even_cached(self):
        modes.load_vietnamese_model()  # Cache hiện có vẫn không bỏ qua xác minh.
        with tempfile.TemporaryDirectory() as folder, patch('joblib.load') as deserialize:
            base = Path(folder)
            bad = base / 'bad.joblib'
            bad.write_bytes(b'not a trusted artifact')
            with override_settings(VI_CLASSIFICATION_MODEL_PATH=bad):
                with self.assertRaises(ModelUnavailable):
                    modes.load_vietnamese_model()
            for setting, original, mutate in [
                ('VI_CLASSIFICATION_METADATA_PATH', settings.VI_CLASSIFICATION_METADATA_PATH,
                 lambda d: d.update(selected_id='word_logreg_C_10')),
                ('VI_CLASSIFICATION_METADATA_PATH', settings.VI_CLASSIFICATION_METADATA_PATH,
                 lambda d: d['models'][modes.VI_CANDIDATE].update(model_sha256='0'*64)),
                ('VI_CLASSIFICATION_ARTIFACT_MANIFEST_PATH', settings.VI_CLASSIFICATION_ARTIFACT_MANIFEST_PATH,
                 lambda d: d['files'][f'models/{modes.VI_CANDIDATE}.joblib'].update(sha256='0'*64)),
            ]:
                data = json.loads(Path(original).read_text(encoding='utf-8'))
                mutate(data)
                bad.write_text(json.dumps(data), encoding='utf-8')
                with override_settings(**{setting: bad}):
                    with self.assertRaises(ModelUnavailable):
                        modes.load_vietnamese_model()
            deserialize.assert_not_called()


class ModeEndpointTests(FinanceCase):
    def setUp(self):
        super().setUp()
        self.url = reverse('finance:category_suggestion')

    def post(self, mode='vi', **extra):
        return self.client.post(self.url, {'description': 'Mua rau nấu cơm', 'kind': 'expense', 'mode': mode, **extra})

    def test_invalid_or_missing_mode_does_not_infer(self):
        with patch('finance.views.suggest_label') as predict:
            for mode in ['', 'auto', 'fr', '../../model']:
                self.assertEqual(self.post(mode).status_code, 400)
            self.assertEqual(self.client.post(self.url, {'description':'x', 'kind':'expense'}).status_code, 400)
            predict.assert_not_called()

    def test_modes_owner_kind_multiple_unmapped_and_transfer(self):
        self.food.canonical_label = 'Groceries'
        self.food.save()
        self.bob_category.canonical_label = 'Groceries'
        self.bob_category.save()
        other = Category.objects.create(user=self.alice, name='Thực phẩm khác', kind='expense', canonical_label='Groceries')
        Category.objects.filter(pk=self.salary.pk).update(canonical_label='Groceries')
        before = (Transaction.objects.count(), Category.objects.count())
        for mode in ['vi', 'en']:
            with patch('finance.views.suggest_label', return_value='Groceries') as predict:
                data = self.post(mode, model_path='not-accepted', user_id=self.bob.pk).json()
                predict.assert_called_once_with('Mua rau nấu cơm', mode=mode)
                self.assertEqual({c['id'] for c in data['categories']}, {self.food.pk, other.pk})
                self.assertNotIn('score', data)
                self.assertEqual(self.post(mode, kind='income').json()['status'], 'review')
            with patch('finance.views.suggest_label', return_value='Transfer'):
                for kind in ['income', 'expense']:
                    data = self.post(mode, kind=kind).json()
                    self.assertEqual(data['status'], 'review')
                    self.assertEqual(data['categories'], [])
            with patch('finance.views.suggest_label', return_value='Travel'):
                self.assertEqual(self.post(mode).json()['categories'], [])
        self.assertEqual(before, (Transaction.objects.count(), Category.objects.count()))

    @override_settings(VI_CLASSIFICATION_MODEL_PATH='missing-vi-artifact.joblib')
    def test_missing_vi_no_fallback_and_manual_save(self):
        with patch.object(classification, 'suggest_label') as english:
            response = self.post()
            self.assertEqual(response.status_code, 503)
            self.assertEqual(response.json()['status'], 'unavailable')
            english.assert_not_called()
        self.assertEqual(self.client.post(reverse('finance:transaction_create'), self.payload()).status_code, 302)

    def test_empty_zero_and_security_both_modes(self):
        for mode in ['vi', 'en']:
            self.assertEqual(self.post(mode, description='').json()['status'], 'no_suggestion')
            self.assertEqual(self.post(mode, description='🧬').json()['status'], 'no_suggestion')
            self.assertEqual(self.post(mode, description='x'*501).status_code, 400)
            secure = Client(enforce_csrf_checks=True)
            secure.force_login(self.alice)
            payload = {'description':'', 'kind':'expense', 'mode':mode}
            self.assertEqual(secure.post(self.url, payload).status_code, 403)
            page = secure.get(reverse('finance:transaction_create'))
            self.assertEqual(secure.post(self.url, payload, HTTP_X_CSRFTOKEN=page.cookies['csrftoken'].value).status_code, 200)
        self.client.logout()
        self.assertEqual(self.post().status_code, 302)

    def test_template_explicit_modes_and_limitations(self):
        page = self.client.get(reverse('finance:transaction_create'))
        for text in ['Tiếng Việt — thử nghiệm', 'Tiếng Anh — thử nghiệm',
                     'Gợi ý có thể sai.', 'do AI biên soạn']:
            self.assertContains(page, text)
        self.assertNotContains(page, '72,73%')
