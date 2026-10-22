"""Monthly plans only become actual transactions on an explicit valid POST."""
from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from .models import Category, RecurringRule, RecurringRevision, RecurringOccurrence, RecurringEvent


class RecurringConflict(Exception):
    pass


def today():
    return timezone.localdate(timezone=timezone.get_fixed_timezone(420))


def shift(month, offset):
    index = month.year * 12 + month.month - 1 + offset
    year, zero_month = divmod(index, 12)
    if not 1 <= year <= 9999:
        raise ValueError('Tháng ngoài phạm vi.')
    return date(year, zero_month + 1, 1)


def window():
    current = today().replace(day=1)
    return shift(current, -11), shift(current, 1)


def snapshot(rule):
    return {'name': rule.name, 'kind': rule.kind, 'amount': str(rule.amount),
        'category_id': rule.category_id, 'category_name': rule.category.name,
        'due_day': rule.due_day, 'start_month': rule.start_month.isoformat(),
        'end_month': rule.end_month.isoformat() if rule.end_month else None}


def lock_rule(user, pk):
    # Take the write lock before reading, including SQLite's deferred transactions.
    if not RecurringRule.objects.filter(pk=pk, user=user).update(updated_at=F('updated_at')):
        raise RecurringConflict('Quy tắc không hợp lệ.')
    return RecurringRule.objects.get(pk=pk, user=user)


@transaction.atomic
def save_rule(form, user):
    if form.instance.pk:
        current = lock_rule(user, form.instance.pk)
        # Do not let a stale form overwrite a concurrently paused rule.
        form.instance.is_active = current.is_active
        effective = shift(today().replace(day=1), 1)
    else:
        effective = today().replace(day=1)
    rule = form.save()
    RecurringRevision.objects.update_or_create(rule=rule, effective_month=effective,
        defaults={'active': rule.is_active, 'snapshot': snapshot(rule)})
    return rule


@transaction.atomic
def set_active(user, pk, active):
    rule = lock_rule(user, pk)
    if rule.is_active == active:
        return rule
    current = today().replace(day=1)
    revisions = list(rule.revisions.all())
    if active:
        effective = shift(current, 1)
        data = snapshot(rule)
    else:
        effective = current
        past = [rev for rev in revisions if rev.effective_month <= current]
        data = past[-1].snapshot if past else snapshot(rule)
        rule.revisions.filter(effective_month__gte=current).update(active=False)
    rule.is_active = active
    rule.save(update_fields=['is_active', 'updated_at'])
    RecurringRevision.objects.update_or_create(rule=rule, effective_month=effective,
        defaults={'active': active, 'snapshot': data})
    return rule


def planned(rule, month):
    revisions = [rev for rev in rule.revisions.all() if rev.effective_month <= month]
    if not revisions:
        return None
    rev = revisions[-1]
    data = rev.snapshot
    if (not rev.active or month < date.fromisoformat(data['start_month'])
            or (data['end_month'] and month > date.fromisoformat(data['end_month']))):
        return None
    due = date(month.year, month.month, min(int(data['due_day']), monthrange(month.year, month.month)[1]))
    return data, due


def rule_status(rule):
    """Today's effective revision, independent of selected period or processed history."""
    month = today().replace(day=1)
    revisions = list(rule.revisions.all())
    effective = [rev for rev in revisions if rev.effective_month <= month]
    rev = effective[-1] if effective else None
    data = rev.snapshot if rev else snapshot(rule)
    # End is inclusive: only the following month is ended, even if paused.
    if data['end_month'] and month > date.fromisoformat(data['end_month']):
        label = 'Đã kết thúc'
    elif rev is not None and not rev.active:
        label = 'Đã tạm dừng'
    elif month < date.fromisoformat(data['start_month']) or rev is None:
        label = 'Chưa đến tháng bắt đầu'
    else:
        label = 'Đang hoạt động'
    future = [rev for rev in revisions if rev.effective_month > month]
    note = ''
    if future:
        next_rev = future[0]
        when = next_rev.effective_month.strftime('%m/%Y')
        if rev is not None and not rev.active and next_rev.active:
            note = f'Đã lên lịch kích hoạt lại từ {when}.'
        else:
            note = f'Thay đổi đã lên lịch có hiệu lực từ {when}.'
    return {'label': label, 'note': note}


def item(rule, month, occurrence=None):
    if occurrence:
        data, due = occurrence.snapshot, occurrence.due_date
        state = occurrence.status
    else:
        plan = planned(rule, month)
        if not plan:
            return None
        data, due = plan
        state = 'open'
    display = ('due' if due <= today() else 'upcoming') if state == 'open' else state
    first, last = window()
    actionable = first <= month <= today().replace(day=1)
    labels = {'due': 'Đến hạn / quá hạn', 'upcoming': 'Sắp đến hạn', 'recorded': 'Đã ghi nhận',
        'skipped': 'Đã bỏ qua', 'deleted': 'Giao dịch đã xóa — cần mở lại'}
    return {'rule': rule, 'month': month, 'snapshot': data, 'due_date': due, 'amount': Decimal(data['amount']),
        'state': display, 'state_label': labels[display], 'occurrence': occurrence,
        'can_process': state == 'open' and actionable,
        'can_reopen': state in ('skipped', 'deleted') and actionable}


def monthly_items(user, month):
    rules = RecurringRule.objects.filter(user=user).prefetch_related('revisions')
    occurrences = {o.rule_id: o for o in RecurringOccurrence.objects.filter(user=user, month=month).select_related('transaction')}
    items = [item(rule, month, occurrences.get(rule.pk)) for rule in rules]
    return sorted((row for row in items if row), key=lambda row: (row['due_date'], row['rule'].pk))


def dashboard_items(user):
    first, _ = window()
    current = today().replace(day=1)
    until = today() + timedelta(days=7)
    rules = list(RecurringRule.objects.filter(user=user).prefetch_related('revisions'))
    occurrences = {(o.rule_id, o.month): o for o in RecurringOccurrence.objects.filter(user=user,
        month__gte=first, month__lte=until.replace(day=1))}
    rows = []
    month = first
    while month <= until.replace(day=1):
        for rule in rules:
            row = item(rule, month, occurrences.get((rule.pk, month)))
            if row and row['state'] in ('due', 'upcoming') and row['due_date'] <= until:
                rows.append(row)
        month = shift(month, 1)
    rows.sort(key=lambda row: (row['due_date'], row['rule'].pk))
    return {'recurring_due': rows[:5], 'recurring_due_count': len(rows)}


def validate_month(month):
    first, last = window()
    if month.day != 1 or not first <= month <= last or month > today().replace(day=1):
        raise RecurringConflict('Chỉ xử lý kỳ trong 12 tháng đến tháng hiện tại. Kỳ tháng sau chỉ để xem trước.')


@transaction.atomic
def process(user, rule_id, month, action, form=None):
    validate_month(month)
    rule = lock_rule(user, rule_id)
    occurrence = RecurringOccurrence.objects.select_for_update().filter(rule=rule, month=month, user=user).first()
    if occurrence and occurrence.status == 'recorded':
        if action == 'record':
            return occurrence  # Idempotent: return original without changing submitted values.
        raise RecurringConflict('Kỳ đã ghi nhận. Hãy xem giao dịch liên kết.')
    if action == 'reopen':
        if not occurrence or occurrence.status not in ('skipped', 'deleted'):
            raise RecurringConflict('Chỉ mở lại kỳ đã bỏ qua hoặc giao dịch đã xóa.')
        occurrence.status = 'open'
        occurrence.save(update_fields=['status', 'updated_at'])
        RecurringEvent.objects.create(occurrence=occurrence, action='reopen')
        return occurrence
    if occurrence and occurrence.status != 'open':
        if action == 'skip' and occurrence.status == 'skipped':
            return occurrence
        raise RecurringConflict('Kỳ đã được xử lý. Cần xác nhận mở lại trước.')
    if not occurrence:
        plan = planned(rule, month)
        if not plan:
            raise RecurringConflict('Kỳ không còn hợp lệ; quy tắc có thể đã tạm dừng hoặc ngoài thời gian áp dụng.')
        data, due = plan
        occurrence = RecurringOccurrence(user=user, rule=rule, month=month, due_date=due, snapshot=data)
    if action == 'skip':
        occurrence.status = 'skipped'
    elif action == 'record' and form is not None:
        if not form.is_valid() or form.cleaned_data['kind'] != occurrence.snapshot['kind']:
            raise RecurringConflict('Dữ liệu xác nhận không hợp lệ hoặc khác loại của kỳ. Hãy tải lại biểu mẫu.')
        category = Category.objects.select_for_update().get(pk=form.cleaned_data['category'].pk, user=user)
        form.instance.category = category
        form.instance.user = user
        occurrence.transaction = form.save()  # Existing coverage/forecast hooks, no ML feedback.
        occurrence.status = 'recorded'
    else:
        raise RecurringConflict('Thao tác không hợp lệ.')
    occurrence.save()
    RecurringEvent.objects.create(occurrence=occurrence, action=action)
    return occurrence
