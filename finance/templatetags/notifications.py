from django import template

from ..notification_models import GroupNotification

register = template.Library()


@register.simple_tag
def unread_notifications(user):
    return GroupNotification.objects.filter(recipient=user, read_at__isnull=True).count()
