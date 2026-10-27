"""Prefill only on GET; signed, account-bound idempotency on explicit save."""
import json
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from django.core import signing
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.crypto import constant_time_compare, salted_hmac

from . import classification_feedback
from .models import Category, SimilarTransactionOperation

SALT = 'finance.similar-transaction.v1'
TOKEN_AGE = 7200


class SimilarConflict(Exception):
    pass


def issue(user):
    # No pending row, session snapshot or source ID; safe to open more than one tab.
    return signing.dumps({'key': str(uuid4()), 'user': user.pk, 'action': 'similar_create'}, salt=SALT)


def verify(user, token):
    try:
        claim = signing.loads(token, salt=SALT, max_age=TOKEN_AGE)
        if claim['user'] != user.pk or claim['action'] != 'similar_create':
            raise ValueError
        return UUID(claim['key'])
    except (signing.BadSignature, ValueError, TypeError, KeyError, AttributeError):
        raise SimilarConflict('Phiên tạo giao dịch tương tự không hợp lệ hoặc đã hết hạn. Hãy mở biểu mẫu mới.') from None


def initial_data(source, user):
    valid = Category.objects.filter(pk=source.category_id, user=user, kind=source.kind).exists()
    return {'description': source.description, 'kind': source.kind, 'amount': source.amount,
        'category': source.category_id if valid else None,
        'date': timezone.localdate(timezone=ZoneInfo('Asia/Ho_Chi_Minh')),
        'similar_operation': issue(user)}, not valid


@transaction.atomic
def save(form, user, token, suggestion_id='', mode='vi'):
    key = verify(user, token)
    if not form.instance._state.adding or form.instance.user_id != user.pk:
        raise SimilarConflict('Biểu mẫu tạo mới không hợp lệ.')
    data = form.cleaned_data
    payload = [data['kind'], format(data['amount'], 'f'), data['date'].isoformat(),
        data['category'].pk, data['description'], suggestion_id, mode if suggestion_id else '']
    digest = salted_hmac(SALT + '.payload', json.dumps(payload, ensure_ascii=False), algorithm='sha256').hexdigest()
    # First statement in this transaction is INSERT. A unique PK serializes two
    # claims on PostgreSQL; SQLite takes its write lock without read->write upgrade.
    try:
        with transaction.atomic():
            operation = SimilarTransactionOperation.objects.create(id=key, user=user, digest=digest)
    except IntegrityError:
        previous = SimilarTransactionOperation.objects.filter(pk=key, user=user).select_related('saved_transaction').first()
        if not previous or not constant_time_compare(previous.digest, digest):
            raise SimilarConflict('Mã thao tác đã được dùng với dữ liệu khác. Hãy kiểm tra giao dịch đã lưu hoặc mở biểu mẫu mới.') from None
        if not previous.saved_transaction_id or previous.saved_transaction.user_id != user.pk:
            raise SimilarConflict('Giao dịch của thao tác này đã bị xóa hoặc không còn khả dụng. Hãy mở biểu mẫu mới.')
        return previous.saved_transaction, True
    if not suggestion_id:
        # Refresh and lock current ownership/type, rather than trust prefill or
        # the ModelChoice instance read before entering this transaction.
        form.instance.category = Category.objects.select_for_update().get(
            pk=data['category'].pk, user=user, kind=data['kind'])
    saved = classification_feedback.save_with_feedback(form, user, suggestion_id, mode)
    # A consumed ML receipt from another form must not attach an old transaction
    # to this new operation. Genuine retries are resolved above by the operation.
    if form.instance.pk != saved.pk:
        raise classification_feedback.InvalidSuggestion
    operation.saved_transaction = saved
    operation.save(update_fields=['saved_transaction'])
    return saved, False
