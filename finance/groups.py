"""Account-bound shared ledger operations; no implicit writes to another user's book."""
import json
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from uuid import UUID, uuid4
from django.contrib.auth import get_user_model
from django.core import signing
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone
from django.utils.crypto import constant_time_compare, salted_hmac
from .category_locks import lock_catalog
from .group_models import (MAX, ExpenseGroup, GroupMember, GroupExpense, GroupShare,
    GroupSettlement, GroupAllocation, GroupWalletPosting, GroupOperation)
from .models import Category, Transaction, Wallet
from .wallets import today

SALT = 'finance.group-ledger.v1'


def issue(user, action, group_id=0, target=0):
    version = GroupMember.objects.filter(pk=target,group_id=group_id).values_list('invitation_version',flat=True).first() if action in ['join','decline','revoke'] else None
    return signing.dumps({'user': user.pk, 'action': action, 'group': group_id,
        'target': target, 'key': str(uuid4()),'version':version}, salt=SALT)


def _update(model, pk, **values):
    # Deliberate internal transition; public managers reject arbitrary ledger edits.
    return model._base_manager.filter(pk=pk).update(**values)


def _member(user, group_id, *, write=True, invited=False, history=False):
    row = GroupMember.objects.select_related('group','user').filter(group_id=group_id, user=user).first()
    allowed = ['active','invited','left','rejected','revoked'] if history else ['active','invited'] if invited else ['active']
    if not row or row.status not in allowed:
        raise ValidationError('Bạn không có quyền thực hiện thao tác trong nhóm này.')
    if write and row.group.archived:
        raise ValidationError('Nhóm đã lưu trữ, chỉ được xem lịch sử.')
    return row


def _run(user, token, action, group_id, target, data, callback, *, invited=False):
    try:
        claim = signing.loads(token, salt=SALT, max_age=7200)
        if any(claim.get(k) != v for k,v in {'user':user.pk,'action':action,'group':group_id,'target':target}.items()):
            raise ValueError
        key = UUID(claim['key'])
    except (signing.BadSignature, ValueError, KeyError, TypeError, AttributeError):
        raise ValidationError('Phiên thao tác không hợp lệ hoặc hết hạn. Hãy mở lại biểu mẫu.') from None
    digest = salted_hmac(SALT, json.dumps(data, sort_keys=True, ensure_ascii=False, default=str), algorithm='sha256').hexdigest()
    with transaction.atomic():
        lock_catalog(user.pk)
        if group_id:
            if not ExpenseGroup.objects.select_for_update().filter(pk=group_id).exists():
                raise ValidationError('Nhóm không còn khả dụng.')
            _member(user, group_id, write=False, invited=invited,history=action.startswith('post_'))
        previous = GroupOperation.objects.filter(user=user, action=action, key=key).first()
        if previous:
            if previous.group_id != (group_id or None) or not constant_time_compare(previous.digest, digest):
                raise ValidationError('Mã thao tác đã dùng với dữ liệu khác. Kiểm tra lịch sử trước khi gửi lại.')
            return previous.result_id
        if action in ['join','decline','revoke'] and not GroupMember.objects.filter(pk=target,group_id=group_id,
                invitation_version=claim.get('version')).exists():
            raise ValidationError('Đây là lời mời cũ đã bị thu hồi/thay thế. Hãy mở lời mời hiện tại.')
        result = callback()
        GroupOperation.objects.create(user=user,group_id=group_id or None,key=key,action=action,
            digest=digest,result_id=result)
        return result


def amount(value, *, zero=False):
    try:
        if isinstance(value, (float, bool)):
            raise ValueError
        result = Decimal(value)
        if not result.is_finite() or result != result.to_integral_value() or not (0 if zero else 1) <= result <= MAX:
            raise ValueError
        return result
    except (InvalidOperation, ValueError, TypeError):
        raise ValidationError('Nhập số nguyên VND trong giới hạn cho phép.') from None


def check_date(day):
    from datetime import date
    if type(day) is not date or day > today():
        raise ValidationError('Ngày thực tế không hợp lệ hoặc ở tương lai theo giờ Việt Nam.')


def create_group(user, token, name):
    name = ' '.join(name.split())
    def create():
        if not name or len(name) > 80:
            raise ValidationError('Tên nhóm từ 1 đến 80 ký tự.')
        group = ExpenseGroup.objects.create(owner=user,name=name)
        GroupMember.objects.create(group=group,user=user,status='active',accepted_at=timezone.now())
        return group.pk
    return _run(user,token,'create',0,0,{'name':name},create)


def invite(user, token, group_id, username):
    def send():
        actor = _member(user, group_id)
        if actor.group.owner_id != user.pk:
            raise ValidationError('Chỉ chủ nhóm được mời thành viên.')
        target = get_user_model().objects.filter(username=username,is_active=True).first()
        if target is None or target.pk == user.pk:
            raise ValidationError('Không thể gửi lời mời tới tài khoản này.')
        if GroupMember.objects.filter(group_id=group_id,status__in=['active','invited']).count() >= 20:
            raise ValidationError('Nhóm có tối đa 20 thành viên/lời mời đang hiệu lực.')
        old = GroupMember.objects.filter(group_id=group_id,user=target).first()
        if old:
            if old.status in ['active','invited']:
                raise ValidationError('Tài khoản đã tham gia hoặc đang có lời mời.')
            _update(GroupMember,old.pk,status='invited',invitation_version=F('invitation_version')+1)
            return old.pk
        return GroupMember.objects.create(group_id=group_id,user=target).pk
    return _run(user,token,'invite',group_id,0,{'username':username},send)


def membership_action(user, token, group_id, member_id, action):
    if action not in ['join','decline','revoke','leave']:
        raise ValidationError('Thao tác thành viên không được hỗ trợ.')
    def change():
        actor = _member(user,group_id,write=False,invited=action in ['join','decline'])
        row = GroupMember.objects.filter(pk=member_id,group_id=group_id).first()
        if not row:
            raise ValidationError('Thành viên không khả dụng.')
        if action in ['join','decline']:
            if row.user_id != user.pk or row.status != 'invited' or actor.group.archived:
                raise ValidationError('Lời mời đã bị thu hồi, hết hiệu lực hoặc không thuộc bạn.')
            if action == 'join' and GroupMember.objects.filter(group_id=group_id,status='active').count() >= 20:
                raise ValidationError('Nhóm đã đủ thành viên.')
            _update(GroupMember,row.pk,status='active' if action=='join' else 'rejected',
                accepted_at=timezone.now() if action=='join' else None)
        elif action == 'revoke':
            if actor.group.owner_id != user.pk or row.status != 'invited' or actor.group.archived:
                raise ValidationError('Chỉ chủ nhóm được thu hồi lời mời chưa chấp nhận.')
            _update(GroupMember,row.pk,status='revoked')
        else:
            if row.user_id != user.pk or row.status != 'active' or actor.group.owner_id == user.pk:
                raise ValidationError('Chỉ thành viên được tự rời nhóm; chủ nhóm chưa thể rời trong bản này.')
            balances = obligations(group_id)
            has_debt = any(x['remaining'] > 0 and (x['share'].member_id == row.pk or x['share'].expense.payer_id == row.pk) for x in balances)
            unresolved = GroupShare.objects.filter(expense__group_id=group_id,expense__voided=False,
                status='pending').filter(Q(member=row)|Q(expense__payer=row)).exists()
            if has_debt or unresolved or GroupSettlement.objects.filter(group_id=group_id,status='pending',
                    expires_at__gt=timezone.now()).filter(Q(debtor=row)|Q(creditor=row)).exists():
                raise ValidationError('Chưa thể rời: còn phải thu/trả, phần chia chờ hoặc hoàn trả chờ xác nhận.')
            _update(GroupMember,row.pk,status='left')
        return row.pk
    return _run(user,token,action,group_id,member_id,{},change,invited=action in ['join','decline'])


def archive_group(user, token, group_id):
    def archive():
        actor = _member(user,group_id)
        if actor.group.owner_id != user.pk:
            raise ValidationError('Chỉ chủ nhóm được lưu trữ.')
        if any(row['remaining'] > 0 for row in obligations(group_id)) or GroupShare.objects.filter(
                expense__group_id=group_id,expense__voided=False,status='pending').exists():
            raise ValidationError('Nhóm còn công nợ hoặc phần chia chờ, chưa được lưu trữ.')
        if GroupMember.objects.filter(group_id=group_id,status='invited').exists():
            raise ValidationError('Nhóm còn lời mời chờ. Hãy thu hồi hoặc chờ người nhận xử lý trước khi lưu trữ.')
        _update(ExpenseGroup,group_id,archived=True)
        return group_id
    return _run(user,token,'archive',group_id,0,{},archive)


def rename_group(user,token,group_id,name):
    name=' '.join(name.split())
    def rename():
        actor=_member(user,group_id)
        if actor.group.owner_id!=user.pk or not name or len(name)>80:
            raise ValidationError('Chỉ chủ nhóm được đổi tên hợp lệ (1–80 ký tự).')
        _update(ExpenseGroup,group_id,name=name)
        return group_id
    return _run(user,token,'rename',group_id,0,{'name':name},rename)


def split(total, members, method, exact=None):
    total = amount(total)
    ids = sorted(members)
    if not ids or len(ids)>20 or len(set(ids)) != len(ids):
        raise ValidationError('Chọn từ 1 đến 20 người chịu chi, không trùng.')
    if method == 'equal':
        q,r = divmod(total, Decimal(len(ids)))
        return {pk:q + (Decimal(1) if index < r else Decimal(0)) for index,pk in enumerate(ids)}
    if method != 'exact' or set(exact or {}) != set(ids):
        raise ValidationError('Cách chia/phần tiền không hợp lệ.')
    parts = {pk:amount(exact[pk],zero=True) for pk in ids}
    if sum(parts.values(),Decimal(0)) != total:
        raise ValidationError('Tổng phần chia phải bằng tổng khoản chi; không tự bù chênh lệch.')
    return parts


def create_expense(user, token, group_id, data):
    def create():
        actor = _member(user,group_id)
        check_date(data['date'])
        parts = split(data['amount'],data['members'],data['method'],data.get('exact'))
        if GroupMember.objects.filter(group_id=group_id,status='active',pk__in=parts).count() != len(parts):
            raise ValidationError('Người chịu chi không còn tham gia đúng nhóm.')
        expense = GroupExpense.objects.create(group_id=group_id,payer=actor,amount=amount(data['amount']),
            date=data['date'],description=data['description'],method=data['method'])
        for pk,value in parts.items():
            GroupShare.objects.create(expense=expense,member_id=pk,amount=value)
        return expense.pk
    return _run(user,token,'expense',group_id,0,data,create)


def respond_share(user, token, group_id, share_id, accept, category_id=None):
    def respond():
        _member(user,group_id)
        share = GroupShare.objects.select_related('expense','member').filter(pk=share_id,
            expense__group_id=group_id,member__user=user,expense__voided=False).first()
        if not share or share.status != 'pending':
            raise ValidationError('Phần chia không thuộc bạn hoặc đã được xử lý; không sửa lịch sử đã chốt.')
        if not accept:
            _update(GroupShare,share.pk,status='rejected')
        else:
            saved = None
            if share.amount > 0:
                category = Category.objects.filter(pk=category_id,user=user,kind='expense').first()
                if not category:
                    raise ValidationError('Chọn danh mục chi của chính bạn.')
                saved = Transaction.objects.create(user=user,kind='expense',amount=share.amount,date=share.expense.date,
                    category=category,description='Phần chi nhóm: ' + share.expense.description,wallet=None)
            _update(GroupShare,share.pk,status='accepted',confirmed_at=timezone.now(),transaction_id=saved.pk if saved else None)
        return share.pk
    action = 'share_accept' if accept else 'share_reject'
    return _run(user,token,action,group_id,share_id,{'category':category_id},respond)


def void_expense(user,token,group_id,expense_id):
    def cancel():
        _member(user,group_id)
        expense = GroupExpense.objects.filter(pk=expense_id,group_id=group_id,payer__user=user,voided=False).first()
        if not expense or expense.shares.filter(status='accepted').exists() or GroupWalletPosting.objects.filter(expense=expense).exists():
            raise ValidationError('Không thể hủy: khoản không thuộc bạn, đã hủy hoặc đã có xác nhận/ghi ví. Bản này chưa hỗ trợ sửa sai sau chốt.')
        _update(GroupExpense,expense.pk,voided=True)
        return expense.pk
    return _run(user,token,'void',group_id,expense_id,{},cancel)


def obligations(group_id):
    # Exact aggregate, bounded to one group; never N+1 per share or participant.
    from .wallets import sums
    shares = GroupShare.objects.filter(expense__group_id=group_id,expense__voided=False,status='accepted',amount__gt=0).exclude(
        member_id=F('expense__payer_id')).select_related('expense__payer__user','member__user')
    result = {s.pk:{'share':s,'remaining':s.amount,'reserved':Decimal(0)} for s in shares}
    allocations = GroupAllocation.objects.filter(settlement__group_id=group_id)
    for confirmed in (True,False):
        rows = allocations.filter(settlement__status='confirmed') if confirmed else allocations.filter(
            settlement__status='pending',settlement__expires_at__gt=timezone.now())
        for value in sums(rows,'share_id'):
            if value['share_id'] in result:
                row = result[value['share_id']]
                if confirmed: row['remaining'] -= Decimal(value['total'])
                else: row['reserved'] += Decimal(value['total'])
    for row in result.values(): row['available'] = row['remaining'] - row['reserved']
    return list(result.values())


def propose_settlement(user,token,group_id,data):
    def create():
        actor = _member(user,group_id)
        check_date(data['date'])
        value = amount(data['amount'])
        ids = data['shares']
        if not ids or len(ids) != len(set(ids)):
            raise ValidationError('Chọn các phần còn nợ, không trùng.')
        chosen = [row for row in obligations(group_id) if row['share'].pk in ids]
        if len(chosen) != len(ids) or any(row['share'].member_id != actor.pk for row in chosen):
            raise ValidationError('Chỉ được hoàn các phần nợ đã chấp nhận của chính bạn.')
        payers = {row['share'].expense.payer_id for row in chosen}
        if len(payers) != 1 or any(row['share'].expense.date > data['date'] for row in chosen):
            raise ValidationError('Chỉ chọn một người nhận và ngày không trước khoản đang hoàn.')
        creditor_id = payers.pop()
        if not GroupMember.objects.filter(pk=creditor_id,group_id=group_id,status='active').exists():
            raise ValidationError('Người nhận không còn hoạt động trong nhóm.')
        if value > sum((row['available'] for row in chosen),Decimal(0)):
            raise ValidationError('Tiền vượt phần còn có thể hoàn; yêu cầu chờ khác đang giữ chỗ số nợ.')
        record = GroupSettlement.objects.create(group_id=group_id,debtor=actor,creditor_id=creditor_id,
            amount=value,date=data['date'],expires_at=timezone.now()+timedelta(days=7))
        remaining=value
        for row in sorted(chosen,key=lambda r:(r['share'].expense.date,r['share'].pk)):
            allocated = min(remaining,row['available'])
            if allocated > 0:
                GroupAllocation.objects.create(settlement=record,share=row['share'],amount=allocated)
                remaining-=allocated
        return record.pk
    return _run(user,token,'settlement',group_id,0,data,create)


def settlement_action(user,token,group_id,settlement_id,action):
    if action not in ['confirm','reject','cancel']:
        raise ValidationError('Thao tác hoàn trả không được hỗ trợ.')
    def change():
        actor = _member(user,group_id)
        row = GroupSettlement.objects.filter(pk=settlement_id,group_id=group_id).first()
        expected = row.debtor_id if row and action=='cancel' else row.creditor_id if row else None
        if not row or expected != actor.pk or row.status != 'pending' or row.expires_at <= timezone.now():
            raise ValidationError('Đề nghị đã xử lý/hết hạn hoặc bạn không phải bên được xác nhận thao tác.')
        if action == 'confirm':
            states = {r['share'].pk:r for r in obligations(group_id)}
            allocations = list(row.allocations.all())
            if sum((a.amount for a in allocations),Decimal(0)) != row.amount or any(
                    a.share_id not in states or states[a.share_id]['remaining'] < states[a.share_id]['reserved'] for a in allocations):
                raise ValidationError('Số nợ đã thay đổi; chưa thể xác nhận hoàn trả.')
            _update(GroupSettlement,row.pk,status='confirmed',confirmed_at=timezone.now())
        else:
            _update(GroupSettlement,row.pk,status='rejected' if action=='reject' else 'cancelled')
        return row.pk
    return _run(user,token,'settlement_'+action,group_id,settlement_id,{},change)


def post_wallet(user,token,group_id,source_id,side,wallet_id):
    def post():
        # Private cash assignment does not edit the shared ledger. Historical
        # source ownership is rechecked even after leaving/archiving the group.
        _member(user,group_id,write=False,history=True)
        if side == 'bill':
            source = GroupExpense.objects.filter(pk=source_id,group_id=group_id,payer__user=user,voided=False).first()
            scope = {'expense_id':source_id}
        elif side in ['pay','receive']:
            scope = {'settlement_id':source_id,'side':side,'user':user}
            source = GroupSettlement.objects.filter(pk=source_id,group_id=group_id,status='confirmed',
                **{'debtor__user' if side=='pay' else 'creditor__user':user}).first()
        else:
            raise ValidationError('Nguồn dòng tiền không hợp lệ.')
        if not source:
            raise ValidationError('Nguồn không thuộc bạn hoặc chưa được chốt.')
        previous = GroupWalletPosting.objects.filter(**scope).first()
        if previous:
            if previous.user_id != user.pk or previous.wallet_id != wallet_id:
                raise ValidationError('Dòng tiền đã gắn ví; bản này chưa hỗ trợ đổi hoặc đảo posting.')
            return previous.pk
        wallet = Wallet.objects.select_for_update().filter(pk=wallet_id,user=user,archived=False).first()
        if not wallet:
            raise ValidationError('Chọn ví hoạt động của chính bạn.')
        posting = GroupWalletPosting.objects.create(user=user,wallet=wallet,side=side,amount=source.amount,date=source.date,**{
            'expense_id' if side=='bill' else 'settlement_id':source_id})
        Wallet.objects.filter(pk=wallet.pk).update(opening_locked=True)
        return posting.pk
    return _run(user,token,'post_'+side,group_id,source_id,{'wallet':wallet_id},post)


def unassigned_entries(user):
    from django.db.models import Value, CharField
    fields=('source_id','group_id','date','amount','side','label')
    rows=GroupExpense.objects.filter(payer__user=user,voided=False,wallet_posting__isnull=True).order_by().annotate(
        source_id=F('pk'),side=Value('bill',output_field=CharField()),label=Value('Trả hóa đơn nhóm',output_field=CharField())).values(*fields)
    for side,party in [('pay','debtor'),('receive','creditor')]:
        part=GroupSettlement.objects.filter(status='confirmed',**{party+'__user':user}).exclude(
            wallet_postings__user=user,wallet_postings__side=side).order_by().annotate(source_id=F('pk'),
                side=Value(side,output_field=CharField()),label=Value('Hoàn trả nhóm' if side=='pay' else 'Nhận hoàn trả nhóm',output_field=CharField())).values(*fields)
        rows=rows.union(part,all=True)
    return rows.order_by('-date','side','-source_id')


def pending_count(user, month=None):
    rows = GroupShare.objects.filter(member__user=user,status='pending',expense__voided=False,amount__gt=0)
    if month is not None:
        from calendar import monthrange
        end=month.replace(day=monthrange(month.year,month.month)[1])
        rows = rows.filter(expense__date__gte=month,expense__date__lte=end)
    return rows.count()


def guard_personal_transaction(row):
    if not row.pk:
        return
    guard_personal_rows([row])


def guard_personal_rows(rows):
    rows = {row.pk:row for row in rows}
    for share in GroupShare.objects.select_related('expense','member').filter(transaction_id__in=rows):
        row = rows[share.transaction_id]
        if (row.user_id != share.member.user_id or row.kind != 'expense' or row.amount != share.amount
                or row.date != share.expense.date or row.wallet_id is not None):
            raise ValidationError('Phần chi nhóm đã xác nhận: không đổi tiền, loại, ngày hoặc ví; dòng tiền ví được ghi riêng trong nhóm.')


def unassigned_cash(user, as_of):
    from django.db.models import Value, CharField
    from .wallets import sums
    bills = GroupExpense.objects.filter(payer__user=user,voided=False,date__lte=as_of,wallet_posting__isnull=True)
    combined = sums(bills.annotate(cashside=Value('out',output_field=CharField())),'cashside')
    for side,field in [('pay','debtor'),('receive','creditor')]:
        rows = GroupSettlement.objects.filter(status='confirmed',date__lte=as_of,**{field+'__user':user}).exclude(
            wallet_postings__user=user,wallet_postings__side=side)
        part = sums(rows.annotate(cashside=Value('out' if side=='pay' else 'in',output_field=CharField())),'cashside')
        combined = combined.union(part,all=True)
    result = {'out':Decimal(0),'in':Decimal(0),'count':0}
    for row in combined:
        if row['total'] is not None:
            result[row['cashside']] += Decimal(row['total'])
        result['count'] += row['count']
    return result
