"""Read-only reconciliation against current recorded expenses and coverage."""
from datetime import date
from decimal import Decimal, InvalidOperation, localcontext
from zoneinfo import ZoneInfo

from django.db import transaction
from django.utils import timezone

from .coverage import monthly_history
from .coverage_calendar import current_month, next_month
from .forecast_config import METHOD_LABELS
from .models import ForecastDataVersion, ForecastHistory


class ReviewChanged(Exception):
    pass


def eligible(entry):
    """Evidence of a forecast made IN the target month, not before its start."""
    try:
        made = timezone.localtime(entry.calculated_at, ZoneInfo('Asia/Ho_Chi_Minh')).date()
        months = [date.fromisoformat(row['month']) for row in entry.inputs]
        return (entry.origin == 'live-post-v1' and entry.configuration_version
            and entry.method in METHOD_LABELS and entry.estimate_decimal.is_finite()
            and entry.estimate_decimal >= 0 and entry.target_month.day == 1
            and entry.target_month <= made < next_month(entry.target_month)
            and entry.history_count >= 3 and len(months) == entry.history_count
            and months[0] == entry.history_start and months[-1] == entry.history_end
            and entry.history_end < entry.target_month
            and next_month(entry.history_end) == entry.target_month
            and all(next_month(a) == b for a, b in zip(months, months[1:]))
            and all(row['status'] == 'complete' and row['confirmed_at']
                and Decimal(row['expense']).is_finite() and Decimal(row['expense']) >= 0
                for row in entry.inputs))
    except (ValueError, TypeError, KeyError, IndexError, InvalidOperation, OverflowError):
        return False


@transaction.atomic
def review(user):
    updated_at = timezone.now()
    current = current_month()
    version = ForecastDataVersion.objects.filter(user=user).values_list('version', flat=True).first() or 0
    entries = list(ForecastHistory.objects.filter(user=user).order_by('target_month', 'calculated_at', 'pk'))
    past = [entry.target_month for entry in entries if entry.target_month < current]
    actuals = {row['month']: row for row in monthly_history(user, min(past), max(past))} if past else {}
    selected = set()
    errors = []
    rows = []
    for entry in entries:
        has_evidence = bool(eligible(entry))
        first = has_evidence and entry.target_month not in selected
        if first:
            selected.add(entry.target_month)
        actual = actuals.get(entry.target_month)
        row = {'entry': entry, 'method_label': METHOD_LABELS.get(entry.method, entry.method),
            'selected': first, 'used_for_mae': False, 'actual': None, 'bias': None, 'absolute_error': None}
        if not has_evidence:
            row['status'] = 'Không đủ thông tin đánh giá'
        elif entry.target_month >= current:
            row['status'] = 'Tháng chưa kết thúc'
        elif actual is None or actual['forecast_expense'] is None:
            row['status'] = 'Chưa đủ dữ liệu đối chiếu'
        else:
            row['status'] = 'Đã đối chiếu'
            row['actual'] = actual['forecast_expense']
            with localcontext() as money_context:
                money_context.prec = 64
                row['bias'] = entry.estimate_decimal - row['actual']
            row['absolute_error'] = row['bias'].copy_abs()
            row['used_for_mae'] = first
            if first:
                errors.append(row['absolute_error'])
        rows.append(row)
    latest = ForecastDataVersion.objects.filter(user=user).values_list('version', flat=True).first() or 0
    if version != latest or current != current_month():
        raise ReviewChanged('Dữ liệu hoặc tháng hiện tại vừa thay đổi. Vui lòng tải lại lịch sử để đối chiếu.')
    # Newest month first, earliest version first within each month.
    rows.sort(key=lambda row: (-row['entry'].target_month.toordinal(), row['entry'].calculated_at, row['entry'].pk))
    with localcontext() as money_context:
        money_context.prec = 64
        mae = sum(errors, Decimal('0')) / Decimal(len(errors)) if errors else None
    return {'rows': rows, 'evaluated_months': len(errors), 'mae': mae,
        'updated_at': updated_at}
