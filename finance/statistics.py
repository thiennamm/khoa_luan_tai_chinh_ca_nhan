"""Thống kê đã ghi, chỉ đọc; không dùng zero này làm đầu vào dự báo."""
from datetime import date
from calendar import monthrange
from decimal import Decimal, ROUND_HALF_UP
from django import forms
from .coverage_calendar import current_month
from .models import Transaction, MonthlyCoverage


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


def financial_statistics(user, selected, span):
    if span not in (6, 12) or selected.day != 1:
        raise ValueError('Khoảng thống kê không hợp lệ')
    last = (selected.year - 1) * 12 + selected.month - 1
    months = [date(i // 12 + 1, i % 12 + 1, 1) for i in range(max(0, last - span + 1), last + 1)]
    series = {m: {'month': m, 'income': Decimal('0'), 'expense': Decimal('0'), 'count': 0,
                  'status': MonthlyCoverage.Status.UNKNOWN} for m in months}
    categories = {}
    # Cả transaction và danh mục phải thuộc chủ tài khoản; nhóm theo ID, không tên.
    rows = Transaction.objects.filter(user=user, category__user=user, date__gte=months[0],
        date__lte=date(selected.year, selected.month, monthrange(selected.year, selected.month)[1])).order_by()
    for day, kind, amount, category_id, name in rows.values_list('date', 'kind', 'amount', 'category_id', 'category__name').iterator():
        month = day.replace(day=1)
        item = series[month]
        item[kind] += amount
        item['count'] += 1
        if month == selected and kind == 'expense':
            category = categories.setdefault(category_id, {'id': category_id, 'name': name, 'amount': Decimal('0')})
            category['amount'] += amount
    for coverage in MonthlyCoverage.objects.filter(user=user, month__gte=months[0], month__lte=selected):
        series[coverage.month]['status'] = coverage.status
    today = current_month()
    maximum = max((max(m['income'], m['expense']) for m in series.values()), default=Decimal('0'))
    for item in series.values():
        item['balance'] = item['income'] - item['expense']
        item['status_display'] = MonthlyCoverage.Status(item['status']).label
        item['period_note'] = ('Tháng chưa kết thúc' if item['month'] == today else
                               'Tháng tương lai' if item['month'] > today else '')
        item['income_height'] = format(percent(item['income'], maximum), 'f')
        item['expense_height'] = format(percent(item['expense'], maximum), 'f')
    expense = series[selected]['expense']
    category_rows = sorted(categories.values(), key=lambda r: (-r['amount'], r['id']))
    for item in category_rows:
        item['share'] = percent(item['amount'], expense)
        item['width'] = format(item['share'], 'f')
    assert sum((c['amount'] for c in category_rows), Decimal('0')) == expense
    return {**chart_axis(maximum), 'category_statistics': category_rows, 'monthly_statistics': list(series.values()),
            'statistics_expense': expense, 'statistics_span': span, 'statistics_actual_months': len(months)}
