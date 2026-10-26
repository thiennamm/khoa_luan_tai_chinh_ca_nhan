from zoneinfo import ZoneInfo
from django.utils import timezone


def today():
    return timezone.localdate(timezone=ZoneInfo('Asia/Ho_Chi_Minh'))
