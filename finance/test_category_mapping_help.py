from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import Client, TestCase, SimpleTestCase
from django.urls import reverse

from .category_mapping_help import SCOPES, MAPPING_LABEL, MAPPING_HELP, RENAME_HELP
from .classification_labels import LABELS
from .forms import CategoryForm
from .models import Category, Transaction
from . import classification_feedback as feedback


class LabelScopeTests(SimpleTestCase):
    def test_all_original_codes_have_scope_and_transfer_is_review_only(self):
        self.assertEqual(set(SCOPES), set(LABELS))
        self.assertEqual(len(SCOPES), 17)
        for name, scope in SCOPES.values():
            self.assertTrue(name)
            self.assertTrue(scope)
        self.assertIn('không phải giải trí nói chung', SCOPES['Travel'][1])


class CategoryMappingHelpTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user('mapping-help-qa')
        cls.other = User.objects.create_user('mapping-help-other')
        cls.a = Category.objects.create(user=cls.user, name='Vé <phim>', kind='expense', canonical_label='Entertainment')
        cls.b = Category.objects.create(user=cls.user, name='Trò chơi', kind='expense', canonical_label='Entertainment')
        cls.foreign = Category.objects.create(user=cls.other, name='Riêng tư KHÔNG HIỂN THỊ', kind='expense', canonical_label='Entertainment')

    def setUp(self):
        self.client.force_login(self.user)
        self.create = reverse('finance:category_create')
        self.edit = reverse('finance:category_edit', args=[self.a.pk])

    def test_blank_is_explicit_default_and_is_usable_for_transactions(self):
        form = CategoryForm(user=self.user)
        self.assertEqual(form.fields['canonical_label'].label, MAPPING_LABEL)
        self.assertEqual(list(form.fields['canonical_label'].choices)[0], ('', 'Chưa ánh xạ'))
        self.assertIn(form['canonical_label'].value(), ('', None))
        self.assertContains(self.client.get(self.create), MAPPING_HELP)
        response = self.client.post(self.create, {'name': 'Tùy tôi', 'kind': 'expense', 'canonical_label': ''})
        self.assertEqual(response.status_code, 302)
        item = Category.objects.get(name='Tùy tôi')
        self.assertEqual(item.canonical_label, '')
        response = self.client.post(reverse('finance:transaction_create'), {
            'kind': 'expense', 'amount': '50.000', 'date': '2026-09-01',
            'category': item.pk, 'description': 'Chỉ dữ liệu QA'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Transaction.objects.get().amount, Decimal('50000'))

    def test_duplicate_label_allowed_without_keyword_policing(self):
        # Deliberately odd names must not trigger automatic remapping/rejection.
        response = self.client.post(self.create, {'name': 'Giải trí tùy chọn', 'kind': 'expense',
            'canonical_label': 'Restaurants'}, follow=True)
        self.assertEqual(Category.objects.get(name='Giải trí tùy chọn').canonical_label, 'Restaurants')
        response = self.client.post(self.create, {'name': 'Khác', 'kind': 'expense',
            'canonical_label': 'Entertainment'}, follow=True)
        self.assertContains(response, 'Nhãn này đang liên kết với các danh mục:')
        self.assertContains(response, 'Vé &lt;phim&gt;')
        self.assertNotContains(response, self.foreign.name)

    def test_get_and_post_preview_are_read_only_scoped_and_work_without_js(self):
        before = list(Category.objects.order_by('pk').values())
        response = self.client.get(self.edit)
        self.assertEqual(response.context['linked_names'], [self.b.name])
        self.assertNotContains(response, self.foreign.name)
        response = self.client.post(self.create, {'name': 'Chưa lưu', 'kind': 'expense',
            'canonical_label': 'Entertainment', 'action': 'preview_mapping'})
        self.assertContains(response, 'Đã kiểm tra, chưa lưu danh mục.')
        self.assertEqual(set(response.context['linked_names']), {self.a.name, self.b.name})
        self.assertNotContains(response, self.foreign.name)
        self.assertEqual(before, list(Category.objects.order_by('pk').values()))

    def test_wrong_kind_has_no_peer_notice_and_stays_invalid(self):
        response = self.client.post(self.create, {'name': 'Sai loại', 'kind': 'income',
            'canonical_label': 'Entertainment', 'action': 'preview_mapping'})
        self.assertEqual(response.context['linked_names'], [])
        self.assertTrue(response.context['form'].errors)
        self.assertFalse(Category.objects.filter(name='Sai loại').exists())

    def test_invalid_codes_transfer_and_forged_owner(self):
        for code in ('not-a-label', 'Transfer'):
            response = self.client.post(self.create, {'name': 'Không tạo', 'kind': 'expense', 'canonical_label': code})
            self.assertIn('canonical_label', response.context['form'].errors)
        response = self.client.post(self.create, {'name': 'Thu riêng', 'kind': 'income',
            'canonical_label': 'Income', 'user_id': self.other.pk})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Category.objects.get(name='Thu riêng').user_id, self.user.pk)

    def test_rename_keeps_ids_transactions_and_feedback_snapshots(self):
        tx = Transaction.objects.create(user=self.user, kind='expense', category=self.a,
            date=date(2026, 9, 1), amount=Decimal('50000'), description='QA')
        receipt = feedback.issue(self.user, {'description': 'QA', 'kind': 'expense', 'mode': 'vi'}, 'Entertainment', tx)
        from .forms import TransactionForm
        form = TransactionForm({'kind': 'expense', 'category': self.a.pk, 'date': '2026-09-01',
            'amount': '50000', 'description': 'QA'}, instance=tx, user=self.user)
        self.assertTrue(form.is_valid(), form.errors)
        feedback.save_with_feedback(form, self.user, str(receipt.pk), 'vi')
        before = list(self.user.classificationfeedback_set.values())
        # A second unconsumed receipt must still validate after rename.
        live = feedback.issue(self.user, {'description': 'Live QA', 'kind': 'expense', 'mode': 'vi'}, 'Entertainment')
        self.assertContains(self.client.get(self.edit), RENAME_HELP)
        response = self.client.post(self.edit, {'name': 'Tên mới', 'kind': 'expense', 'canonical_label': 'Entertainment'})
        self.assertEqual(response.status_code, 302)
        tx.refresh_from_db(); self.a.refresh_from_db()
        self.assertEqual(tx.category_id, self.a.pk)
        self.assertEqual(tx.category.name, 'Tên mới')
        self.assertEqual(before, list(self.user.classificationfeedback_set.values()))
        feedback.verify(live, {'description': 'Live QA', 'kind': 'expense', 'mode': 'vi'}, None)
        self.assertEqual(feedback.apply_receipt(self.user, str(live.pk),
            {'description': 'Live QA', 'kind': 'expense', 'mode': 'vi'}, None, self.a.pk).pk, self.a.pk)

    def test_owner_login_and_csrf(self):
        foreign_url = reverse('finance:category_edit', args=[self.foreign.pk])
        for method in (self.client.get, self.client.post):
            self.assertEqual(method(foreign_url).status_code, 404)
        csrf = Client(enforce_csrf_checks=True); csrf.force_login(self.user)
        self.assertEqual(csrf.post(self.create, {'action': 'preview_mapping'}).status_code, 403)
        self.client.logout()
        self.assertEqual(self.client.get(self.create).status_code, 302)
