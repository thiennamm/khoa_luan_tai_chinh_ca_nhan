"""Receipt validation and atomic save; inference stays in the existing service."""
import json
from datetime import timedelta
from uuid import UUID

from django.db import transaction
from django.utils import timezone
from django.utils.crypto import constant_time_compare, salted_hmac

from .classification import CANDIDATE, EXPECTED_SHA256
from .classification_modes import VI_CANDIDATE, VI_SHA256
from .classification_labels import LABELS, compatible_kind
from .models import Category, ClassificationFeedback, ClassificationSuggestion, Transaction

TTL = timedelta(minutes=15)


class InvalidSuggestion(Exception):
    pass


def identity(mode):
    return ('task10b-vi-v1/' + VI_CANDIDATE, VI_SHA256) if mode == 'vi' else (
        'task06b-v1-final/' + CANDIDATE, EXPECTED_SHA256)


def input_digest(description, kind, mode):
    # Exact form input, not the broader normalization used by the model.
    payload = json.dumps([description.strip(), kind, mode], ensure_ascii=False)
    return salted_hmac('classification-feedback-input-v1', payload, algorithm='sha256').hexdigest()


def seal(receipt):
    payload = json.dumps([str(receipt.pk), receipt.user_id, receipt.input_digest,
        receipt.kind, receipt.mode, receipt.predicted_label, receipt.model_name,
        receipt.model_sha256, receipt.source_transaction_id, receipt.expires_at.isoformat()])
    return salted_hmac('classification-feedback-receipt-v1', payload, algorithm='sha256').hexdigest()


def issue(user, data, label, source=None):
    name, sha = identity(data['mode'])
    receipt = ClassificationSuggestion(user=user, input_digest=input_digest(
        data['description'], data['kind'], data['mode']), kind=data['kind'], mode=data['mode'],
        predicted_label=label, model_name=name, model_sha256=sha,
        source_transaction=source, expires_at=timezone.now() + TTL)
    receipt.seal = seal(receipt)
    receipt.save()
    return receipt


def owned_receipt(user, token, *, lock=False):
    try:
        key = UUID(str(token))
    except (ValueError, TypeError, AttributeError):
        raise InvalidSuggestion from None
    rows = ClassificationSuggestion.objects.filter(pk=key, user=user)
    receipt = (rows.select_for_update() if lock else rows).first()
    if receipt is None or not constant_time_compare(receipt.seal, seal(receipt)):
        raise InvalidSuggestion
    return receipt


def verify(receipt, data, source_id, *, allow_consumed=False):
    if (receipt.source_transaction_id != source_id
            or receipt.mode not in ('vi', 'en')
            or (receipt.model_name, receipt.model_sha256) != identity(receipt.mode)
            or receipt.predicted_label not in LABELS
            or receipt.input_digest != input_digest(data.get('description', ''), data.get('kind', ''), data.get('mode', ''))):
        raise InvalidSuggestion
    if allow_consumed and receipt.consumed_at and receipt.saved_transaction_id:
        return
    if receipt.revoked_at or receipt.expires_at <= timezone.now() or receipt.consumed_at:
        raise InvalidSuggestion


@transaction.atomic
def apply_receipt(user, token, data, source_id, category_id):
    # Same lock order as save: receipt, then category (avoid PostgreSQL deadlock).
    receipt = owned_receipt(user, token, lock=True)
    verify(receipt, data, source_id)
    if receipt.predicted_label == 'Transfer' or compatible_kind(receipt.predicted_label) != receipt.kind:
        raise InvalidSuggestion
    try:
        category_id = int(category_id)
        if not 0 < category_id <= 9223372036854775807:
            raise ValueError
        category = Category.objects.select_for_update().get(pk=category_id, user=user,
            kind=receipt.kind, canonical_label=receipt.predicted_label)
    except (Category.DoesNotExist, ValueError, TypeError, OverflowError):
        raise InvalidSuggestion from None
    updated = ClassificationSuggestion.objects.filter(pk=receipt.pk, consumed_at__isnull=True,
        revoked_at__isnull=True, expires_at__gt=timezone.now()).update(
            applied_at=timezone.now(), applied_category=category)
    if not updated:
        raise InvalidSuggestion
    return category


@transaction.atomic
def save_with_feedback(form, user, token='', mode=''):
    if not token:
        return form.save()
    source_id = form.instance.pk
    data = {**form.cleaned_data, 'mode': mode}
    receipt = owned_receipt(user, token)
    verify(receipt, data, source_id, allow_consumed=True)
    if receipt.consumed_at:
        return Transaction.objects.get(pk=receipt.saved_transaction_id, user=user)
    now = timezone.now()
    # Compare-and-set also serializes competing claims on SQLite and PostgreSQL.
    claimed = ClassificationSuggestion.objects.filter(pk=receipt.pk, consumed_at__isnull=True,
        revoked_at__isnull=True, expires_at__gt=now).update(consumed_at=now)
    if not claimed:
        receipt.refresh_from_db()
        if receipt.consumed_at and receipt.saved_transaction_id:
            return Transaction.objects.get(pk=receipt.saved_transaction_id, user=user)
        raise InvalidSuggestion
    # Reload after claiming so an Apply request racing with save cannot be lost.
    receipt.refresh_from_db()
    category = Category.objects.select_for_update().get(pk=form.cleaned_data['category'].pk, user=user)
    form.instance.category = category
    saved = form.save()  # Model validation rechecks kind and ownership.
    ClassificationSuggestion.objects.filter(pk=receipt.pk).update(saved_transaction=saved)
    final_label = category.canonical_label
    if final_label in LABELS and compatible_kind(final_label) == saved.kind:
        ClassificationFeedback.objects.create(user=user, transaction=saved, suggestion=receipt,
            mode=receipt.mode, model_name=receipt.model_name, model_sha256=receipt.model_sha256,
            predicted_label=receipt.predicted_label, final_category=category,
            final_category_name=category.name, final_label=final_label,
            applied=receipt.applied_at is not None,
            same_label=receipt.predicted_label == final_label)
    return saved
