"""Only isolated test DB; models are mocked at the existing inference boundary."""
from datetime import timedelta
from datetime import date
from io import StringIO
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.management import call_command
from django.db import IntegrityError
from django.db.models.deletion import ProtectedError
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from . import classification_feedback as service
from .classification import ModelUnavailable, EXPECTED_SHA256
from .classification_modes import VI_SHA256
from .models import Category, Transaction, ClassificationSuggestion as Suggestion, ClassificationFeedback as Feedback
from .models import MonthlyCoverage


class FeedbackTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('feedback-qa', password='OnlyForTests!8391')
        self.other = User.objects.create_user('other-qa')
        self.food = Category.objects.create(user=self.user, name='Chợ <rau>', kind='expense', canonical_label='Groceries')
        self.cafe = Category.objects.create(user=self.user, name='Quán', kind='expense', canonical_label='Restaurants')
        self.unmapped = Category.objects.create(user=self.user, name='Chưa ánh xạ', kind='expense')
        self.foreign = Category.objects.create(user=self.other, name='Riêng tư', kind='expense', canonical_label='Groceries')
        self.client.force_login(self.user)
        self.input = {'description': 'Mua rau chợ', 'kind': 'expense', 'mode': 'vi'}
        self.create_url = reverse('finance:transaction_create')
        self.action_url = reverse('finance:suggestion_action')

    def offer(self, label='Groceries', **data):
        with patch('finance.views.suggest_label', return_value=label):
            response = self.client.post(reverse('finance:category_suggestion'), {**self.input, **data})
        self.assertEqual(response.status_code, 200)
        return response.json()['suggestion_id']

    def apply(self, token, category=None, **data):
        return self.client.post(self.action_url, {**self.input, 'action': 'apply',
            'suggestion_id': token, 'category': category or self.food.pk, **data})

    def save(self, token='', category=None, url=None, **data):
        return self.client.post(url or self.create_url, {
            'description': self.input['description'], 'kind': 'expense', 'date': '2026-09-15',
            'amount': '12000', 'category': category or self.food.pk, 'suggestion_id': token,
            'suggestion_mode': self.input['mode'], **data})

    def test_same_label_without_apply_is_not_acceptance(self):
        token = self.offer()
        self.assertEqual(self.save(token, applied='true', predicted_label='Income', model_sha256='fake').status_code, 302)
        item = Feedback.objects.get()
        self.assertTrue(item.same_label)
        self.assertFalse(item.applied)
        self.assertEqual(item.predicted_label, 'Groceries')
        self.assertEqual(item.model_sha256, VI_SHA256)
        self.assertFalse(hasattr(item, 'description'))

    def test_apply_same_then_final_different(self):
        for changed in (False, True):
            with self.subTest(changed=changed):
                token = self.offer()
                self.assertEqual(self.apply(token).status_code, 200)
                self.assertEqual(Transaction.objects.count(), int(changed))
                self.assertEqual(self.save(token, self.cafe.pk if changed else self.food.pk).status_code, 302)
                item = Feedback.objects.latest('pk')
                self.assertTrue(item.applied)
                self.assertEqual(item.same_label, not changed)
                self.assertEqual(item.final_label, 'Restaurants' if changed else 'Groceries')

    def test_different_without_apply(self):
        self.save(self.offer(), self.cafe.pk)
        item = Feedback.objects.get()
        self.assertFalse(item.same_label)
        self.assertFalse(item.applied)

    def test_unmapped_final_category_consumes_without_feedback(self):
        token = self.offer()
        self.save(token, self.unmapped.pk)
        self.assertFalse(Feedback.objects.exists())
        self.assertIsNotNone(Suggestion.objects.get(pk=token).consumed_at)
        self.save(token, self.unmapped.pk)
        self.assertEqual(Transaction.objects.count(), 1)

    def test_no_model_or_no_suggestion_can_save_manually(self):
        for value in (None, ModelUnavailable()):
            with patch('finance.views.suggest_label', **({'side_effect': value} if isinstance(value, Exception) else {'return_value': value})):
                self.client.post(reverse('finance:category_suggestion'), self.input)
            self.assertEqual(self.save().status_code, 302)
        self.assertEqual(Transaction.objects.count(), 2)
        self.assertFalse(Feedback.objects.exists())

    def test_transfer_needs_review_cannot_apply_but_can_compare_final_choice(self):
        token = self.offer('Transfer')
        self.assertEqual(self.apply(token).status_code, 400)
        self.save(token)
        item = Feedback.objects.get()
        self.assertEqual(item.predicted_label, 'Transfer')
        self.assertFalse(item.same_label)
        self.assertFalse(item.applied)
        self.assertContains(self.client.get(reverse('finance:classification_feedback')), 'Cần xem lại')

    def test_apply_checks_ownership_kind_and_mapping(self):
        income = Category.objects.create(user=self.user, name='Lương', kind='income', canonical_label='Income')
        for category in (self.foreign, self.cafe, self.unmapped, income):
            self.assertEqual(self.apply(self.offer(), category.pk).status_code, 400)
        self.assertIsNone(Suggestion.objects.latest('created_at').applied_at)

    def test_stale_expired_foreign_and_tampered_tokens_block_then_allow_manual_save(self):
        tokens = ['not-a-uuid', self.offer(), self.offer(), self.offer(), self.offer()]
        Suggestion.objects.filter(pk=tokens[1]).update(expires_at=timezone.now() - timedelta(seconds=1))
        # Correctly sealed but expired (not only seal rejection).
        expired = Suggestion.objects.get(pk=tokens[1]); expired.seal = service.seal(expired); expired.save()
        Suggestion.objects.filter(pk=tokens[2]).update(user=self.other)
        Suggestion.objects.filter(pk=tokens[3]).update(predicted_label='Income')
        self.client.post(self.action_url, {'action': 'revoke', 'suggestion_id': tokens[4]})
        for token in tokens:
            with self.subTest(token=token):
                self.assertEqual(self.apply(token).status_code, 400)
                response = self.save(token)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'Gợi ý không còn hợp lệ')
                self.assertContains(response, 'id="suggestion-id" name="suggestion_id" value=""')
        self.assertFalse(Transaction.objects.exists())
        self.assertFalse(Feedback.objects.exists())
        self.assertEqual(self.save().status_code, 302)

    def test_backend_rechecks_description_kind_mode_and_target(self):
        for changes in ({'description': 'mua cá'}, {'description': 'Mua  rau chợ'},
                        {'kind': 'income'}, {'suggestion_mode': 'en'}, {'suggestion_mode': ''}):
            token = self.offer()
            if changes.get('kind') == 'income':
                cat = Category.objects.create(user=self.user, name='Lương', kind='income', canonical_label='Income')
                changes = {**changes, 'category': cat.pk}
            self.assertEqual(self.save(token, **changes).status_code, 200)
        self.assertFalse(Feedback.objects.exists())
        row = Transaction.objects.create(user=self.user, category=self.food, kind='expense', date='2026-09-15', amount=12, description=self.input['description'])
        token = self.offer(transaction_id=row.pk)
        self.assertEqual(self.save(token).status_code, 200)  # edit receipt cannot create
        foreign = Transaction.objects.create(user=self.other, category=self.foreign, kind='expense', amount=1)
        with patch('finance.views.suggest_label') as predict:
            self.assertEqual(self.client.post(reverse('finance:category_suggestion'), {**self.input, 'transaction_id': foreign.pk}).status_code, 400)
            predict.assert_not_called()

    def test_invalid_transaction_keeps_receipt_unused(self):
        token = self.offer()
        self.assertEqual(self.save(token, amount='0').status_code, 200)
        self.assertFalse(Transaction.objects.exists())
        self.assertFalse(Feedback.objects.exists())
        self.assertIsNone(Suggestion.objects.get(pk=token).consumed_at)
        self.assertEqual(self.save(token).status_code, 302)

    def test_rollback_removes_transaction_feedback_and_consumption(self):
        coverage = MonthlyCoverage.objects.create(user=self.user, month=date(2026, 9, 1),
            status='complete', confirmed_at=timezone.now())
        token = self.offer()
        real_create = Feedback.objects.create
        def fail_after_create(**kwargs):
            real_create(**kwargs)
            raise IntegrityError('Synthetic failure after feedback insert')
        with patch.object(Feedback.objects, 'create', side_effect=fail_after_create):
            self.assertEqual(self.save(token).status_code, 200)
        self.assertFalse(Transaction.objects.exists())
        self.assertFalse(Feedback.objects.exists())
        self.assertIsNone(Suggestion.objects.get(pk=token).consumed_at)
        coverage.refresh_from_db()
        self.assertEqual(coverage.status, 'complete')
        self.assertEqual(self.save(token).status_code, 302)

    def test_resubmission_creates_no_duplicate_and_cannot_apply_used_receipt(self):
        token = self.offer()
        first = self.save(token)
        second = self.save(token)
        self.assertEqual(first.url, second.url)
        self.assertEqual(Transaction.objects.count(), 1)
        self.assertEqual(Feedback.objects.count(), 1)
        self.assertEqual(self.apply(token).status_code, 400)
        self.save(token, amount='25000')
        self.assertEqual(Transaction.objects.get().amount, 12000)

    def test_final_mapping_is_read_at_save_not_at_inference_or_apply(self):
        token = self.offer()
        self.apply(token)
        self.food.canonical_label = 'Shopping'
        self.food.save()
        self.save(token)
        item = Feedback.objects.get()
        self.assertEqual(item.final_label, 'Shopping')
        self.assertTrue(item.applied)
        self.assertFalse(item.same_label)

    def test_same_label_other_category_does_not_imply_apply(self):
        other_food = Category.objects.create(user=self.user, name='Siêu thị', kind='expense', canonical_label='Groceries')
        self.save(self.offer(), other_food.pk)
        item = Feedback.objects.get()
        self.assertEqual(item.final_category_id, other_food.pk)
        self.assertTrue(item.same_label)
        self.assertFalse(item.applied)

    def test_revoked_receipt_stays_invalid_when_input_is_restored(self):
        token = self.offer()
        self.assertEqual(self.client.post(self.action_url, {'action': 'revoke', 'suggestion_id': token}).status_code, 200)
        self.assertEqual(self.save(token).status_code, 200)
        self.assertFalse(Feedback.objects.exists())
        self.assertFalse(Transaction.objects.exists())

    def test_wrong_kind_prediction_can_only_be_reviewed(self):
        token = self.offer('Income')
        self.assertEqual(self.apply(token).status_code, 400)
        self.save(token)
        item = Feedback.objects.get()
        self.assertEqual(item.predicted_label, 'Income')
        self.assertFalse(item.applied)

    def test_model_identity_changes_invalidates_old_receipt(self):
        token = self.offer()
        with patch('finance.classification_feedback.VI_SHA256', '0' * 64):
            self.assertEqual(self.save(token).status_code, 200)
        self.assertFalse(Feedback.objects.exists())

    def test_edit_does_not_rewrite_history_new_receipt_can_add_new_feedback(self):
        self.save(self.offer())
        original = Feedback.objects.get()
        url = reverse('finance:transaction_edit', args=[original.transaction_id])
        self.save(category=self.cafe.pk, url=url)
        original.refresh_from_db()
        self.assertEqual(original.final_label, 'Groceries')
        self.assertEqual(Feedback.objects.count(), 1)
        token = self.offer(transaction_id=original.transaction_id)
        self.save(token, self.cafe.pk, url=url)
        self.assertEqual(Feedback.objects.count(), 2)
        self.assertEqual(self.save(token, self.cafe.pk, url=url).status_code, 302)
        self.assertEqual(Feedback.objects.count(), 2)

    def test_category_snapshot_and_deletion_policy(self):
        self.save(self.offer())
        item = Feedback.objects.get()
        self.food.name = 'Đổi tên'; self.food.canonical_label = 'Shopping'; self.food.save()
        item.refresh_from_db()
        self.assertEqual(item.final_category_name, 'Chợ <rau>')
        self.assertEqual(item.final_label, 'Groceries')
        # Keep feedback while the original category becomes deletable after transaction edit.
        self.save(category=self.cafe.pk, url=reverse('finance:transaction_edit', args=[item.transaction_id]))
        self.food.delete()
        item.refresh_from_db()
        self.assertIsNone(item.final_category_id)
        self.assertEqual(item.final_category_name, 'Chợ <rau>')
        item.transaction.delete()
        self.assertFalse(Feedback.objects.exists())
        self.assertFalse(Suggestion.objects.exists())

    def test_delete_account_cascades_no_orphans(self):
        self.save(self.offer())
        pending = self.offer()
        # Existing Category <- Transaction PROTECT remains unchanged.
        with self.assertRaises(ProtectedError):
            self.user.delete()
        self.assertEqual(Feedback.objects.count(), 1)
        Transaction.objects.filter(user=self.user).delete()
        self.user.delete()
        self.assertFalse(Feedback.objects.exists())
        self.assertFalse(Suggestion.objects.exists())

    def test_list_is_private_counts_overlap_and_escape_paginates(self):
        for _ in range(21):
            token = self.offer()
            self.apply(token)
            self.save(token)
        url = reverse('finance:classification_feedback')
        page = self.client.get(url)
        self.assertEqual((page.context['total'], page.context['same'], page.context['different'], page.context['applied']), (21, 21, 0, 21))
        self.assertEqual(len(page.context['page_obj']), 20)
        self.assertEqual(len(self.client.get(url, {'page': 2}).context['page_obj']), 1)
        self.assertContains(page, 'Chợ &lt;rau&gt;')
        self.client.force_login(self.other)
        other_page = self.client.get(url)
        self.assertEqual(other_page.context['total'], 0)
        self.assertNotContains(other_page, 'Chợ &lt;rau&gt;')
        self.assertEqual(self.apply(token).status_code, 400)
        self.client.logout()
        self.assertEqual(self.client.get(url).status_code, 302)
        self.assertEqual(self.client.post(self.action_url, {}).status_code, 302)

    def test_post_only_and_csrf(self):
        self.assertEqual(self.client.get(self.action_url).status_code, 405)
        secure = Client(enforce_csrf_checks=True); secure.force_login(self.user)
        self.assertEqual(secure.post(self.action_url, {}).status_code, 403)
        self.assertEqual(secure.post(self.create_url, {}).status_code, 403)

    def test_en_identity_and_cleanup(self):
        token = self.offer(mode='en')
        self.save(token, suggestion_mode='en')
        self.assertEqual(Feedback.objects.get().model_sha256, EXPECTED_SHA256)
        used = Suggestion.objects.get(pk=token)
        pending = self.offer()
        Suggestion.objects.all().update(expires_at=timezone.now() - timedelta(days=1))
        call_command('cleanup_classification_suggestions', stdout=StringIO())
        self.assertFalse(Suggestion.objects.filter(pk=pending).exists())
        self.assertTrue(Suggestion.objects.filter(pk=used.pk).exists())
        self.assertEqual(Feedback.objects.count(), 1)
