from django.db import models, transaction

from .coverage_state import lock_coverage_writes, reset_months


class TransactionQuerySet(models.QuerySet):
    def update(self, **kwargs):
        using = self.db
        with transaction.atomic(using=using):
            lock_coverage_writes(self.values('user_id'), using)
            previous = list(self.values_list('pk', 'user_id', 'date'))
            result = super().update(**kwargs)
            ids = [pk for pk, _, _ in previous]
            current = self.model.objects.using(using).filter(pk__in=ids).values_list('user_id', 'date')
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
            result = super().bulk_create(objs, **kwargs)
            date_field = self.model._meta.get_field('date')
            reset_months([(obj.user_id, date_field.to_python(obj.date)) for obj in objs], using)
            return result

    # Django bulk_update gọi QuerySet.update ở trên. QuerySet.delete và Model.delete
    # đi qua post_delete trong transaction của Collector (xem signals.py).
