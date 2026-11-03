"""Recorded VND balances. Internal transfers never use Transaction or coverage."""
import json
from decimal import Decimal
from uuid import UUID, uuid4
from django.core import signing
from django.core.exceptions import ValidationError
from django.db import connections, transaction
from django.db.models import Count, F, Value, CharField
from django.utils import timezone
from django.utils.crypto import salted_hmac, constant_time_compare
from .category_locks import lock_catalog
from .models import Wallet, WalletTransfer, Transaction
from .services import _RecordedSum, _SQLiteDecimalSum

SALT = 'finance.wallet-transfer.v1'


def today():
    return timezone.localdate(timezone=timezone.get_fixed_timezone(420))


def issue_transfer(user):
    return signing.dumps({'user':user.pk, 'action':'transfer', 'key':str(uuid4())}, salt=SALT)


@transaction.atomic
def transfer(user, token, data):
    try:
        claim = signing.loads(token, salt=SALT, max_age=7200)
        if claim['user'] != user.pk or claim['action'] != 'transfer':
            raise ValueError
        key = UUID(claim['key'])
    except (signing.BadSignature, ValueError, TypeError, KeyError):
        raise ValidationError('Phiên chuyển tiền không hợp lệ hoặc đã hết hạn. Hãy mở biểu mẫu mới.') from None
    payload = [data['source'].pk, data['destination'].pk, str(data['amount']), data['date'].isoformat(), data['note']]
    digest = salted_hmac(SALT, json.dumps(payload, ensure_ascii=False), algorithm='sha256').hexdigest()
    # Same account write lock as wallet saves, including SQLite's real write lock.
    lock_catalog(user.pk)
    existing = WalletTransfer.objects.filter(operation_id=key).first()
    if existing:
        if existing.user_id != user.pk or not constant_time_compare(existing.digest, digest):
            raise ValidationError('Mã thao tác đã được dùng với dữ liệu khác. Kiểm tra lịch sử trước khi gửi lại.')
        return existing, True
    wallets = {w.pk:w for w in Wallet.objects.select_for_update().filter(
        user=user, pk__in=payload[:2]).order_by('pk')}
    if len(wallets) != 2:
        raise ValidationError('Chọn hai ví khác nhau của chính bạn.')
    record = WalletTransfer(user=user, operation_id=key, digest=digest,
        source=wallets[payload[0]], destination=wallets[payload[1]],
        amount=data['amount'], date=data['date'], note=data['note'])
    record.save()  # Revalidates live owner/status/dates, not browser input.
    return record, False


def sums(rows, *fields):
    connection = connections[rows.db]
    if connection.vendor == 'sqlite':
        connection.ensure_connection()
        connection.connection.create_aggregate('finance_vnd_sum', 1, _SQLiteDecimalSum)
    return rows.order_by().values(*fields).annotate(total=_RecordedSum('amount'), count=Count('pk'))


def balances(user, as_of=None):
    day = as_of or today()
    wallets = list(Wallet.objects.filter(user=user))
    result = {w.pk:{'wallet':w, 'balance':w.opening_balance if w.start_date <= day else None,
                    'future_income':Decimal(0),'future_expense':Decimal(0)} for w in wallets}
    unknown = {'income':Decimal(0),'expense':Decimal(0)}
    # At most two groups (past/future) per wallet/kind, never descriptions/history.
    for future in (False, True):
        rows = Transaction.objects.filter(user=user)
        rows = rows.filter(date__gt=day) if future else rows.filter(date__lte=day)
        for group in sums(rows, 'wallet_id', 'kind'):
            amount = Decimal(group['total']); item = result.get(group['wallet_id'])
            if item is not None:
                if future:
                    item['future_' + group['kind']] += amount
                elif item['balance'] is not None:
                    item['balance'] += amount if group['kind']=='income' else -amount
            elif group['wallet_id'] is None and not future:
                unknown[group['kind']] += amount
    # Read both effects from the same grouped row, not two independently timed
    # SELECTs that could show only one side of a concurrently committed transfer.
    rows = WalletTransfer.objects.filter(user=user, source__user=user, destination__user=user, date__lte=day)
    for group in sums(rows, 'source_id', 'destination_id'):
        for field, sign in [('source_id', -1), ('destination_id', 1)]:
            item = result.get(group[field])
            if item and item['balance'] is not None:
                item['balance'] += Decimal(sign) * Decimal(group['total'])
    items = list(result.values())
    total = sum((r['balance'] for r in items if not r['wallet'].archived and r['balance'] is not None), Decimal(0))
    return {'wallet_rows':items, 'wallet_total':total, 'unknown':unknown, 'as_of':day}


def history(user, wallet, start=None, end=None):
    rows = Transaction.objects.filter(user=user, wallet=wallet)
    if start: rows = rows.filter(date__gte=start)
    if end: rows = rows.filter(date__lte=end)
    fields = ('id','date','amount','entry_type','note','link_id')
    rows = rows.order_by().annotate(entry_type=F('kind'), note=F('description'), link_id=F('pk')).values(*fields)
    if wallet is not None:
        for field, label in [('source','transfer_out'),('destination','transfer_in')]:
            transfers = WalletTransfer.objects.filter(user=user, source__user=user, destination__user=user, **{field:wallet})
            if start: transfers = transfers.filter(date__gte=start)
            if end: transfers = transfers.filter(date__lte=end)
            transfers = transfers.order_by().annotate(entry_type=Value(label, output_field=CharField()), link_id=F('pk')).values(*fields)
            rows = rows.union(transfers, all=True)
    return rows.order_by('-date','entry_type','-id')
