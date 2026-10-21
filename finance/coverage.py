"""Tổng hợp lịch tháng và xác nhận do người dùng, chưa dự báo/huấn luyện."""
import hashlib
import json
from datetime import date
from decimal import Decimal

from django.core import signing
from django.core.exceptions import ValidationError
from django.db import router, transaction
from django.utils import timezone

from .coverage_calendar import current_month, month_start, next_month
from .coverage_state import lock_coverage_writes
from .models import Kind, MonthlyCoverage, Transaction

TOKEN_SALT = 'finance.monthly-coverage.review.v1'


def check_month(month):
    if type(month) is not date or month.day != 1:
        raise ValidationError('Vui lòng chọn tháng hợp lệ.')


@transaction.atomic
def monthly_history(user, first, last):
    """Khoảng đóng first..last, chỉ tháng đã kết thúc; không nén khoảng trống.

    recorded_expense là tổng đã ghi; forecast_expense=None nếu chưa xác nhận đủ.
    """
    check_month(first)
    check_month(last)
    if first > last:
        raise ValidationError('Tháng bắt đầu phải trước hoặc bằng tháng kết thúc.')
    limit = current_month()
    months = []
    cursor = first
    while cursor <= last and cursor < limit:
        months.append(cursor)
        cursor = next_month(cursor)
    if not months:
        return []
    items = {month: {'month': month, 'recorded_expense': Decimal('0'), 'transaction_count': 0,
                     'status': MonthlyCoverage.Status.UNKNOWN, 'confirmed_at': None} for month in months}
    rows = Transaction.objects.filter(user=user, date__gte=first, date__lt=cursor).order_by()
    for day, kind, amount in rows.values_list('date', 'kind', 'amount').iterator():
        item = items[month_start(day)]
        item['transaction_count'] += 1  # tất cả giao dịch thu và chi
        if kind == Kind.EXPENSE:
            item['recorded_expense'] += amount
    for coverage in MonthlyCoverage.objects.filter(user=user, month__gte=first, month__lt=cursor):
        items[coverage.month].update(status=coverage.status, confirmed_at=coverage.confirmed_at)
    for item in items.values():
        item['status_display'] = MonthlyCoverage.Status(item['status']).label
        item['forecast_expense'] = item['recorded_expense'] if item['status'] == MonthlyCoverage.Status.COMPLETE else None
    return list(items.values())


def _month_snapshot(user, month, using):
    expense = Decimal('0')
    count = 0
    digest = hashlib.sha256()
    fields = ['pk', 'user_id', 'date', 'kind', 'amount', 'category_id', 'description']
    rows = Transaction.objects.using(using).filter(user=user, date__gte=month, date__lt=next_month(month)).order_by('pk')
    for values in rows.values_list(*fields).iterator():
        count += 1
        if values[3] == Kind.EXPENSE:
            expense += values[4]
        # Chỉ hash trong bộ nhớ; không lưu/ghi log mô tả hoặc toàn bộ giao dịch.
        digest.update(json.dumps([str(value) for value in values], ensure_ascii=True).encode('utf-8') + b'\n')
    return {'recorded_expense': expense, 'transaction_count': count, 'digest': digest.hexdigest()}


def review_month(user, month):
    check_month(month)
    if month >= current_month():
        raise ValidationError('Chỉ xác nhận đầy đủ tháng đã kết thúc theo giờ Việt Nam.')
    using = router.db_for_read(Transaction)
    snapshot = _month_snapshot(user, month, using)
    snapshot['review_token'] = signing.dumps(
        {'user': user.pk, 'month': month.isoformat(), 'digest': snapshot['digest']}, salt=TOKEN_SALT)
    return snapshot


def change_month_status(user, month, status, *, review_token='', confirm_no_expense=False):
    check_month(month)
    if status not in MonthlyCoverage.Status.values:
        raise ValidationError('Trạng thái không hợp lệ.')
    using = router.db_for_write(MonthlyCoverage)
    with transaction.atomic(using=using):
        lock_coverage_writes([user.pk], using)
        confirmed_at = None
        if status == MonthlyCoverage.Status.COMPLETE:
            if month >= current_month():
                raise ValidationError('Chỉ xác nhận đầy đủ tháng đã kết thúc theo giờ Việt Nam.')
            snapshot = _month_snapshot(user, month, using)
            try:
                proof = signing.loads(review_token, salt=TOKEN_SALT, max_age=30 * 60)
            except signing.BadSignature:
                raise ValidationError('Trang xác nhận không còn hợp lệ. Hãy mở lại để kiểm tra tháng này.') from None
            if proof != {'user': user.pk, 'month': month.isoformat(), 'digest': snapshot['digest']}:
                raise ValidationError('Giao dịch đã thay đổi hoặc trang xác nhận không đúng tài khoản/tháng. Hãy kiểm tra lại.')
            if snapshot['recorded_expense'] == 0 and not confirm_no_expense:
                raise ValidationError('Bạn xác nhận tháng này không có khoản chi? Vui lòng đánh dấu xác nhận trước khi tiếp tục.')
            confirmed_at = timezone.now()
        coverage, _ = MonthlyCoverage.objects.using(using).update_or_create(
            user=user, month=month, defaults={'status': status, 'confirmed_at': confirmed_at})
        return coverage
