"""Thống kê đã ghi, chỉ đọc; không dùng zero này làm đầu vào dự báo."""
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from django import forms
from django.utils import timezone
from zoneinfo import ZoneInfo
from .coverage_calendar import current_month
from .models import MonthlyCoverage
from .services import recorded_month_groups


class StatisticsSpanForm(forms.Form):
    span = forms.TypedChoiceField(label='So sánh', coerce=int,
        choices=[(6, '6 tháng'), (12, '12 tháng')],
        error_messages={'invalid_choice': 'Chỉ chọn 6 hoặc 12 tháng.', 'required': 'Chỉ chọn 6 hoặc 12 tháng.'})


def percent(amount, total):
    return (amount * Decimal('100') / total).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP) if total else Decimal('0')


def chart_axis(maximum):
    """Nhãn trình bày rút gọn; giữ nguyên thang cột và số tiền trong bảng."""
    units = [('triệu tỷ VND', '1000000000000000'), ('nghìn tỷ VND', '1000000000000'),
             ('tỷ VND', '1000000000'), ('triệu VND', '1000000'), ('nghìn VND', '1000')]
    unit, divisor = next(((name, Decimal(value)) for name, value in units
                          if maximum >= Decimal(value)), ('VND', Decimal('1')))
    ticks = []
    for position in ([100, 75, 50, 25, 0] if maximum else [0]):
        value = (maximum * Decimal(position) / Decimal('100') / divisor).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP)
        label = format(value, 'f').rstrip('0').rstrip('.').replace('.', ',')
        ticks.append({'position': position, 'value': maximum * Decimal(position) / Decimal('100'),
                      'label': label})
    return {'chart_axis_unit': unit, 'chart_axis_ticks': ticks}


def recorded_month_statistics(user, months, *, today=None):
    """Same recorded-money/coverage definitions for dashboard and month report."""
    months = sorted(set(months))
    reference_month = current_month() if today is None else today.replace(day=1)
    today = today or timezone.localdate(timezone=ZoneInfo('Asia/Ho_Chi_Minh'))
    series = {m: {'month': m, 'income': Decimal('0'), 'expense': Decimal('0'), 'count': 0,
                  'future_count': 0, 'status': MonthlyCoverage.Status.UNKNOWN} for m in months}
    categories = {m: [] for m in months}
    for group in recorded_month_groups(user, months, today):
        item = series[group['month']]
        item[group['kind']] += group['total']
        item['count'] += group['count']
        item['future_count'] += group['future_count']
        if group['kind'] == 'expense':
            categories[group['month']].append({'id': group['category_id'],
                'name': group['category__name'], 'amount': group['total']})
    for coverage in MonthlyCoverage.objects.filter(user=user, month__in=months):
        series[coverage.month]['status'] = coverage.status
    for item in series.values():
        item['balance'] = item['income'] - item['expense']
        item['status_display'] = MonthlyCoverage.Status(item['status']).label
        item['period_note'] = ('Tháng chưa kết thúc' if item['month'] == reference_month else
                               'Tháng tương lai' if item['month'] > reference_month else '')
        item['is_current'] = item['month'] == reference_month
        for category in categories[item['month']]:
            category['share'] = percent(category['amount'], item['expense'])
            category['width'] = format(category['share'], 'f')
        categories[item['month']].sort(key=lambda row: (-row['amount'], row['id']))
        assert sum((c['amount'] for c in categories[item['month']]), Decimal('0')) == item['expense']
    return series, categories


def financial_statistics(user, selected, span):
    if span not in (6, 12) or selected.day != 1:
        raise ValueError('Khoảng thống kê không hợp lệ')
    last = (selected.year - 1) * 12 + selected.month - 1
    months = [date(i // 12 + 1, i % 12 + 1, 1) for i in range(max(0, last - span + 1), last + 1)]
    series, categories = recorded_month_statistics(user, months)
    maximum = max((max(m['income'], m['expense']) for m in series.values()), default=Decimal('0'))
    for item in series.values():
        item['income_height'] = format(percent(item['income'], maximum), 'f')
        item['expense_height'] = format(percent(item['expense'], maximum), 'f')
    expense = series[selected]['expense']
    return {**chart_axis(maximum), 'category_statistics': categories[selected], 'monthly_statistics': list(series.values()),
            'statistics_expense': expense, 'statistics_span': span, 'statistics_actual_months': len(months)}
