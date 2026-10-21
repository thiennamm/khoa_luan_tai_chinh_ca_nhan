from datetime import date
from zoneinfo import ZoneInfo

from django.utils import timezone


def month_start(day):
    return day.replace(day=1)


def next_month(month):
    return date(month.year + (month.month == 12), month.month % 12 + 1, 1)


def current_month():
    # Không phụ thuộc múi giờ trình duyệt hoặc timezone đang activate ở request.
    return month_start(timezone.localdate(timezone=ZoneInfo('Asia/Ho_Chi_Minh')))
