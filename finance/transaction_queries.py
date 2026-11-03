from django.db import models, transaction
from django.core.exceptions import ValidationError

from .coverage_state import lock_coverage_writes, reset_months


def validate_wallet_rows(objs, using, previous=None):
    from .models import Wallet, Transaction
    wallets = {w.pk: w for w in Wallet.objects.using(using).select_for_update().filter(
        pk__in={obj.wallet_id for obj in objs if obj.wallet_id}).order_by('pk')}
    previous = previous or {}
    for obj in objs:
        if obj.wallet_id:
            wallet = wallets.get(obj.wallet_id)
            if (wallet is None or wallet.user_id != obj.user_id
                    or (wallet.archived and previous.get(obj.pk) != obj.wallet_id)
                    or Transaction._meta.get_field('date').to_python(obj.date) < wallet.start_date):
                raise ValidationError('Ví không hợp lệ hoặc ngày giao dịch trước mốc theo dõi.')


class TransactionQuerySet(models.QuerySet):
    def update(self, **kwargs):
        using = self.db
        with transaction.atomic(using=using):
            lock_coverage_writes(self.values('user_id'), using)
            previous = list(self.values_list('pk', 'user_id', 'date'))
            previous_wallets = dict(self.values_list('pk', 'wallet_id'))
            result = super().update(**kwargs)
            ids = [pk for pk, _, _ in previous]
            current = self.model.objects.using(using).filter(pk__in=ids).values_list('user_id', 'date')
            validate_wallet_rows(list(self.model.objects.using(using).filter(pk__in=ids)), using, previous_wallets)
            from .models import Wallet
            wallet_ids = list(self.model.objects.using(using).filter(pk__in=ids).exclude(wallet=None).values_list('wallet_id',flat=True))
            Wallet.objects.using(using).filter(pk__in=wallet_ids).update(opening_locked=True)
            reset_months([(user_id, day) for _, user_id, day in previous] + list(current), using)
            return result

    def bulk_create(self, objs, *args, **kwargs):
        # Không cho thêm đường upsert có thể đổi tháng cũ mà không đọc trước.
        if args or kwargs.get('ignore_conflicts') or kwargs.get('update_conflicts'):
            raise ValueError('bulk_create giao dịch chỉ hỗ trợ insert thông thường với tùy chọn đặt tên.')
        objs = list(objs)
        if not objs:
            return []
        using = self.db
        with transaction.atomic(using=using):
            lock_coverage_writes({obj.user_id for obj in objs}, using)
            validate_wallet_rows(objs, using)
            result = super().bulk_create(objs, **kwargs)
            from .models import Wallet
            Wallet.objects.using(using).filter(pk__in={obj.wallet_id for obj in objs if obj.wallet_id}).update(opening_locked=True)
            date_field = self.model._meta.get_field('date')
            reset_months([(obj.user_id, date_field.to_python(obj.date)) for obj in objs], using)
            return result

    # Django bulk_update gọi QuerySet.update ở trên. QuerySet.delete và Model.delete
    # đi qua post_delete trong transaction của Collector (xem signals.py).
