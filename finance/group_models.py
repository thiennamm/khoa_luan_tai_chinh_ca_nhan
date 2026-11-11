"""Shared ledger. Writes go through groups.py; personal wallets remain private."""
from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.functions import Round

MAX = 999999999999999


def money_check(field, name, zero=False):
    return models.CheckConstraint(condition=models.Q(**{field + '__gte': 0 if zero else 1,
        field + '__lte': MAX}) & models.Q(**{field: Round(field, precision=0)}), name=name)


class LedgerQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise ValidationError('Sổ nhóm chỉ thay đổi qua thao tác xác nhận được kiểm quyền.')

    def delete(self):
        raise ValidationError('Không xóa lịch sử tài chính nhóm.')

    def bulk_create(self, *args, **kwargs):
        raise ValidationError('Không nhập hàng loạt vào sổ nhóm ngoài dịch vụ kiểm quyền.')


class LedgerModel(models.Model):
    objects = LedgerQuerySet.as_manager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError('Khoản đã chốt không được sửa trực tiếp. Dùng thao tác được hỗ trợ trong sổ nhóm.')
        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError('Không xóa lịch sử tài chính nhóm.')


class ExpenseGroup(LedgerModel):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='owned_expense_groups')
    name = models.CharField(max_length=80)
    archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class GroupMember(LedgerModel):
    group = models.ForeignKey(ExpenseGroup, on_delete=models.PROTECT, related_name='members')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='group_memberships')
    status = models.CharField(max_length=12, default='invited', choices=[('invited','Được mời'),('active','Đang tham gia'),
        ('left','Đã rời'),('rejected','Đã từ chối'),('revoked','Đã thu hồi')])
    created_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    invitation_version = models.PositiveIntegerField(default=1)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['group','user'], name='group_member_once'),
            models.CheckConstraint(condition=models.Q(status__in=['invited','active','left','rejected','revoked']), name='group_member_status')]

    def __str__(self):
        return self.user.get_username()


class GroupExpense(LedgerModel):
    group = models.ForeignKey(ExpenseGroup, on_delete=models.PROTECT, related_name='expenses')
    payer = models.ForeignKey(GroupMember, on_delete=models.PROTECT, related_name='paid_expenses')
    amount = models.DecimalField(max_digits=15, decimal_places=0)
    date = models.DateField()
    description = models.CharField(max_length=300)
    method = models.CharField(max_length=8, choices=[('equal','Chia đều'),('exact','Nhập phần tiền')])
    voided = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date','-pk']
        constraints = [money_check('amount','group_expense_money'),
            models.CheckConstraint(condition=models.Q(method__in=['equal','exact']), name='group_expense_method')]
        indexes = [models.Index(fields=['group','date'], name='group_expense_date')]

    def clean(self):
        if self.payer_id and self.payer.group_id != self.group_id:
            raise ValidationError('Người trả không thuộc nhóm.')


class GroupShare(LedgerModel):
    expense = models.ForeignKey(GroupExpense, on_delete=models.PROTECT, related_name='shares')
    member = models.ForeignKey(GroupMember, on_delete=models.PROTECT, related_name='shares')
    amount = models.DecimalField(max_digits=15, decimal_places=0)
    status = models.CharField(max_length=10, default='pending', choices=[('pending','Chờ xác nhận'),
        ('accepted','Đã chấp nhận'),('rejected','Đã từ chối')])
    confirmed_at = models.DateTimeField(null=True, blank=True)
    transaction = models.OneToOneField('finance.Transaction', null=True, blank=True,
        on_delete=models.PROTECT, related_name='group_share')

    class Meta:
        constraints = [models.UniqueConstraint(fields=['expense','member'], name='group_share_once'),
            money_check('amount','group_share_money',zero=True),
            models.CheckConstraint(condition=models.Q(status__in=['pending','accepted','rejected']), name='group_share_status'),
            models.CheckConstraint(condition=(models.Q(status='accepted',confirmed_at__isnull=False)
                & (models.Q(amount=0,transaction__isnull=True)|models.Q(amount__gt=0,transaction__isnull=False)))
                | models.Q(status__in=['pending','rejected'],confirmed_at__isnull=True,transaction__isnull=True), name='group_share_confirmation')]

    def clean(self):
        if self.expense_id and self.member_id and self.expense.group_id != self.member.group_id:
            raise ValidationError('Phần chia không thuộc cùng nhóm.')


class GroupSettlement(LedgerModel):
    group = models.ForeignKey(ExpenseGroup, on_delete=models.PROTECT, related_name='settlements')
    debtor = models.ForeignKey(GroupMember, on_delete=models.PROTECT, related_name='repayments')
    creditor = models.ForeignKey(GroupMember, on_delete=models.PROTECT, related_name='receipts')
    amount = models.DecimalField(max_digits=15, decimal_places=0)
    date = models.DateField()
    status = models.CharField(max_length=10, default='pending', choices=[('pending','Chờ xác nhận'),
        ('confirmed','Đã xác nhận'),('rejected','Đã từ chối'),('cancelled','Đã hủy')])
    expires_at = models.DateTimeField()
    confirmed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at','-pk']
        constraints = [money_check('amount','group_settlement_money'),
            models.CheckConstraint(condition=~models.Q(debtor=models.F('creditor')), name='group_settlement_parties'),
            models.CheckConstraint(condition=models.Q(status__in=['pending','confirmed','rejected','cancelled']), name='group_settlement_status'),
            models.CheckConstraint(condition=models.Q(status='confirmed',confirmed_at__isnull=False)
                | (models.Q(status__in=['pending','rejected','cancelled'],confirmed_at__isnull=True)), name='group_settlement_confirmation')]

    def clean(self):
        for field in ('debtor','creditor'):
            if getattr(self, field + '_id') and getattr(self, field).group_id != self.group_id:
                raise ValidationError('Hai bên hoàn trả phải thuộc đúng nhóm.')


class GroupAllocation(LedgerModel):
    settlement = models.ForeignKey(GroupSettlement, on_delete=models.PROTECT, related_name='allocations')
    share = models.ForeignKey(GroupShare, on_delete=models.PROTECT, related_name='allocations')
    amount = models.DecimalField(max_digits=15, decimal_places=0)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['settlement','share'], name='group_allocation_once'),
            money_check('amount','group_allocation_money')]

    def clean(self):
        if self.share_id and self.settlement_id:
            if (self.share.status != 'accepted' or self.share.member_id != self.settlement.debtor_id
                    or self.share.expense.payer_id != self.settlement.creditor_id
                    or self.share.expense.group_id != self.settlement.group_id
                    or self.settlement.date < self.share.expense.date or self.amount > self.share.amount):
                raise ValidationError('Phân bổ hoàn trả không khớp nghĩa vụ đã xác nhận.')


class GroupWalletPosting(LedgerModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='group_wallet_postings')
    wallet = models.ForeignKey('finance.Wallet', on_delete=models.RESTRICT, related_name='group_postings')
    expense = models.OneToOneField(GroupExpense, null=True, blank=True, on_delete=models.PROTECT, related_name='wallet_posting')
    settlement = models.ForeignKey(GroupSettlement, null=True, blank=True, on_delete=models.PROTECT, related_name='wallet_postings')
    side = models.CharField(max_length=8, choices=[('bill','Trả hóa đơn nhóm'),('pay','Hoàn trả nhóm'),('receive','Nhận hoàn trả nhóm')])
    amount = models.DecimalField(max_digits=15, decimal_places=0)
    date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [money_check('amount','group_posting_money'),
            models.UniqueConstraint(fields=['user','settlement','side'], condition=models.Q(settlement__isnull=False), name='group_posting_once'),
            models.CheckConstraint(condition=models.Q(side='bill',expense__isnull=False,settlement__isnull=True)
                | models.Q(side__in=['pay','receive'],expense__isnull=True,settlement__isnull=False), name='group_posting_source')]
        indexes = [models.Index(fields=['user','date'], name='group_posting_user_date')]

    def clean(self):
        from .wallets import today
        if self.wallet_id and (self.wallet.user_id != self.user_id or self.wallet.archived or self.date < self.wallet.start_date):
            raise ValidationError('Chọn ví hoạt động của chính bạn; ngày không trước mốc theo dõi.')
        if self.date > today():
            raise ValidationError('Không ghi dòng tiền nhóm ngày tương lai.')
        if self.expense_id:
            source = self.expense
            valid = not source.voided and source.payer.user_id == self.user_id and self.side == 'bill'
        elif self.settlement_id:
            source = self.settlement
            valid = source.status == 'confirmed' and ((self.side == 'pay' and source.debtor.user_id == self.user_id)
                or (self.side == 'receive' and source.creditor.user_id == self.user_id))
        else:
            raise ValidationError('Thiếu nguồn dòng tiền.')
        if not valid or source.amount != self.amount or source.date != self.date:
            raise ValidationError('Dòng tiền không khớp nguồn đã chốt và chủ tài khoản.')


class GroupOperation(LedgerModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    group = models.ForeignKey(ExpenseGroup, null=True, blank=True, on_delete=models.PROTECT)
    key = models.UUIDField()
    action = models.CharField(max_length=40)
    digest = models.CharField(max_length=64)
    result_id = models.PositiveBigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['user','action','key'], name='group_operation_once')]
