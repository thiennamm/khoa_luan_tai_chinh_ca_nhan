from django.db.models.signals import post_delete, pre_delete
from django.contrib.auth import get_user_model
from django.dispatch import receiver

from .coverage_state import reset_months
from .models import Transaction


@receiver(pre_delete, sender=Transaction, dispatch_uid='finance.recurring_transaction_deleted')
def recurring_transaction_deleted(sender, instance, using, **kwargs):
    from .models import RecurringOccurrence, RecurringEvent
    from django.utils import timezone
    # Collector's atomic includes both this update and the actual delete.
    rows = RecurringOccurrence.objects.using(using).filter(transaction_id=instance.pk)
    for occurrence in rows:
        changed = RecurringOccurrence.objects.using(using).filter(pk=occurrence.pk,
            transaction_id=instance.pk, status='recorded').update(
                status='deleted', transaction=None, updated_at=timezone.now())
        if changed:
            RecurringEvent.objects.using(using).create(occurrence_id=occurrence.pk, action='delete')


@receiver(post_delete, sender=Transaction, dispatch_uid='finance.reset_month_after_transaction_delete')
def transaction_deleted(sender, instance, using, **kwargs):
    # Django Collector phát tín hiệu này trong atomic, cả xóa instance/queryset/cascade.
    origin = kwargs.get('origin')
    user_model = get_user_model()
    if isinstance(origin, user_model) or getattr(origin, 'model', None) is user_model:
        # Trạng thái/kết quả của tài khoản cũng đang bị cascade xóa; không
        # tạo lại bản ghi phiên bản FK tới tài khoản sắp bị xóa.
        return
    reset_months([(instance.user_id, instance.date)], using)
