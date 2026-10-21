"""Các hook ghi dữ liệu dùng chung; cùng database/transaction với giao dịch."""
from django.db.models import F, Q

from .coverage_calendar import month_start
from .forecast_state import bump_forecast_version


def lock_coverage_writes(user_ids, using):
    from .models import MonthlyCoverage
    # UPDATE đầu transaction lấy khóa ghi SQLite, kể cả khi chưa có dòng trạng thái.
    MonthlyCoverage.objects.using(using).filter(user_id__in=user_ids).update(status=F('status'))


def reset_months(pairs, using):
    from .models import MonthlyCoverage
    keys = sorted({(user_id, month_start(day)) for user_id, day in pairs})
    # Giới hạn độ sâu biểu thức SQL khi CSV trải qua nhiều tháng.
    for offset in range(0, len(keys), 100):
        query = Q()
        for user_id, month in keys[offset:offset + 100]:
            query |= Q(user_id=user_id, month=month)
        MonthlyCoverage.objects.using(using).filter(query).update(
            status=MonthlyCoverage.Status.UNKNOWN, confirmed_at=None)
    # Không có dòng trạng thái tương đương mặc định Chưa xác nhận; không tạo bù.
    if keys:
        bump_forecast_version([user_id for user_id, _ in keys], using)
