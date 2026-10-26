"""Allocation ledger, deliberately independent of Transaction/coverage/forecast/ML."""
import hashlib
import json
import uuid
from decimal import Decimal
from django.core import signing
from django.core.exceptions import ValidationError
from django.db import transaction, IntegrityError
from django.db.models import F
from django.utils import timezone
from .models import SavingsGoal, SavingsEntry, SavingsOperation
from .savings_calendar import today

TOKEN_AGE = 7200
SALT = 'finance.savings.operation.v1'
ACTIONS = {'goal_create', 'goal_edit', 'archive', 'reopen', 'entry_create', 'entry_edit', 'entry_delete'}


class SavingsConflict(Exception):
    pass


def issue(user, action, goal=None, entry=None):
    # GET only signs data; it does not create pending records in the database.
    return signing.dumps({'key': str(uuid.uuid4()), 'user': user.pk, 'action': action,
        'goal': goal.pk if goal else None, 'entry': entry.pk if entry else None,
        'version': entry.version if entry else (goal.version if goal and action != 'entry_create' else None)}, salt=SALT)


def verify(user, token, action, goal_id, entry_id):
    try:
        claim = signing.loads(token, salt=SALT, max_age=TOKEN_AGE)
        if action not in ACTIONS or any(claim.get(k) != value for k, value in
                [('user', user.pk), ('action', action), ('goal', goal_id), ('entry', entry_id)]):
            raise ValueError
        claim['key'] = uuid.UUID(claim['key'])
        return claim
    except (signing.BadSignature, ValueError, TypeError, KeyError, AttributeError):
        raise SavingsConflict('Biểu mẫu không hợp lệ hoặc đã hết hạn. Hãy mở lại biểu mẫu.') from None


def validate_history(goal, rows):
    """Same-day order is immutable PK order; a new entry is appended that day."""
    balance = Decimal(0)
    for row in sorted(rows, key=lambda r: (r.date, r.pk)):
        if row.date < goal.start_date or row.date > today():
            raise ValidationError('Lịch sử có ngày trước ngày bắt đầu hoặc sau hôm nay. Hãy kiểm tra ngày.')
        balance += row.amount if row.kind == SavingsEntry.Kind.CONTRIBUTION else -row.amount
        if balance < 0:
            raise ValidationError('Thao tác làm số tích lũy âm trong lịch sử. Cùng ngày được xét theo thứ tự ghi nhận (ID).')
    return balance


def progress(goal, accumulated):
    percent = accumulated * Decimal(100) / goal.amount
    archived = goal.archived_at is not None
    reached = accumulated >= goal.amount
    return {'goal': goal, 'accumulated': accumulated, 'remaining': max(goal.amount-accumulated, Decimal(0)),
        'percent': percent.quantize(Decimal('.01')),
        'width': format(min(percent, Decimal(100)).quantize(Decimal('.01')), 'f'),
        'state': 'archived' if archived else 'reached' if reached else 'active',
        'state_label': 'Đã lưu trữ' if archived else 'Đã đạt' if reached else 'Đang thực hiện',
        'overdue': not archived and not reached and goal.due_date is not None and goal.due_date < today()}


def summaries(user):
    goals = list(SavingsGoal.objects.filter(user=user))
    amounts = {g.pk: Decimal(0) for g in goals}
    # Do not SUM NUMERIC in SQLite: iterate Decimal values to preserve integer precision.
    for goal_id, kind, amount in SavingsEntry.objects.filter(goal__user=user).order_by().values_list('goal_id','kind','amount').iterator():
        amounts[goal_id] += amount if kind == SavingsEntry.Kind.CONTRIBUTION else -amount
    return [progress(g, amounts[g.pk]) for g in goals]


def summary(goal):
    incoming = outgoing = Decimal(0)
    for kind, amount in goal.entries.order_by().values_list('kind','amount').iterator():
        if kind == SavingsEntry.Kind.CONTRIBUTION:
            incoming += amount
        else:
            outgoing += amount
    return {**progress(goal, incoming-outgoing), 'contributed': incoming, 'withdrawn': outgoing}


@transaction.atomic
def execute(user, token, action, goal_id=None, entry_id=None, data=None):
    claim = verify(user, token, action, goal_id, entry_id)
    data = data or {}
    digest = hashlib.sha256(json.dumps(data, default=str, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    # First statement is an INSERT, taking SQLite's write lock without a read->write
    # upgrade. PostgreSQL's unique PK also serializes replay of the same nonce.
    try:
        with transaction.atomic():
            operation = SavingsOperation.objects.create(id=claim['key'], user=user, action=action, digest=digest)
    except IntegrityError:
        previous = SavingsOperation.objects.filter(pk=claim['key'], user=user, action=action, digest=digest).first()
        if not previous or previous.goal_id is None or previous.goal.user_id != user.pk:
            raise SavingsConflict('Mã thao tác đã được dùng cho dữ liệu khác. Hãy mở lại biểu mẫu.') from None
        return previous.goal, True
    if action == 'goal_create':
        goal = SavingsGoal(user=user, **data)
        goal.full_clean()
        goal.save()
    else:
        # UPDATE obtains a row lock on PostgreSQL, a write lock on SQLite.
        if not SavingsGoal.objects.filter(user=user, pk=goal_id).update(version=F('version')):
            raise SavingsConflict('Mục tiêu không còn khả dụng.')
        goal = SavingsGoal.objects.get(user=user, pk=goal_id)
        if action.startswith('entry_'):
            if goal.archived_at:
                raise SavingsConflict('Mục tiêu đã lưu trữ. Hãy mở lại trước khi thay đổi khoản phân bổ.')
            entry = None
            if entry_id is not None:
                entry = SavingsEntry.objects.filter(goal=goal, pk=entry_id).first()
                if entry is None or entry.version != claim['version']:
                    raise SavingsConflict('Bản ghi vừa thay đổi hoặc bị xóa. Hãy mở lại biểu mẫu.')
            if action == 'entry_delete':
                entry.delete()
            else:
                entry = entry or SavingsEntry(goal=goal)
                for key in ('kind','amount','date','note'):
                    setattr(entry, key, data[key])
                entry.full_clean()
                entry.version += 1
                entry.save()
        else:
            if goal.version != claim['version']:
                raise SavingsConflict('Mục tiêu vừa thay đổi. Hãy mở lại biểu mẫu để kiểm tra.')
            if action == 'goal_edit':
                if goal.archived_at:
                    raise SavingsConflict('Hãy mở lại mục tiêu trước khi sửa.')
                for key in ('name','amount','start_date','due_date','note'):
                    setattr(goal, key, data[key])
                goal.full_clean()
            else:
                goal.archived_at = timezone.now() if action == 'archive' else None
        # Full history rechecked inside the same lock/transaction, including edits/deletes.
        validate_history(goal, list(goal.entries.all()))
        goal.version += 1
        goal.save()
    operation.goal = goal
    operation.save(update_fields=['goal'])
    return goal, False
