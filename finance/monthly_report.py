"""Read-only monthly report, using the dashboard's recorded-data aggregation."""
import re
from calendar import monthrange
from datetime import date
from decimal import Decimal, ROUND_HALF_UP, localcontext
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from django import forms
from django.utils import timezone
from django.urls import reverse

from .forms import MonthForm
from .models import MonthlyCoverage, Transaction
from .statistics import chart_axis, percent, recorded_month_statistics

VIETNAM = ZoneInfo('Asia/Ho_Chi_Minh')


class MonthlyReportForm(MonthForm):
    base_month = forms.DateField(required=False, label='Tháng gốc A', input_formats=['%Y-%m'],
        widget=forms.DateInput(format='%Y-%m', attrs={'type': 'month'}),
        error_messages={'invalid': 'Chọn tháng gốc hợp lệ theo dạng YYYY-MM.'})
    include_details = forms.BooleanField(required=False, label='Bao gồm toàn bộ giao dịch trong tháng')

    def __init__(self, data):
        data = data.copy()
        if 'base_month' not in data and re.fullmatch(r'[0-9]{4}-(0[1-9]|1[0-2])', data.get('month', '')):
            try:
                month = date(int(data['month'][:4]), int(data['month'][5:]), 1)
                if month > date.min:
                    previous = month.replace(month=month.month-1) if month.month > 1 else date(month.year-1, 12, 1)
                    data['base_month'] = f'{previous.year:04d}-{previous.month:02d}'
            except ValueError:
                pass  # Month validation below reports the error, without a fallback report.
        super().__init__(data)
        self.fields['month'].label = 'Tháng đối chiếu B'

    def clean_base_month(self):
        if 'base_month' in self.data and not re.fullmatch(r'[0-9]{4}-(0[1-9]|1[0-2])', self.data.get('base_month', '')):
            raise forms.ValidationError('Chọn tháng gốc hợp lệ theo dạng YYYY-MM.')
        return self.cleaned_data['base_month']

    def clean_month(self):
        if not re.fullmatch(r'[0-9]{4}-(0[1-9]|1[0-2])', self.data.get('month', '')):
            raise forms.ValidationError('Chọn tháng hợp lệ theo dạng YYYY-MM.')
        return self.cleaned_data['month']


def change(before, after):
    with localcontext() as context:
        context.prec = 64
        difference = after - before
        percentage = ((difference * Decimal('100') / before).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP) if before > 0 else None)
    return {'difference': difference, 'percentage': percentage,
        'direction': 'Tăng' if difference > 0 else 'Giảm' if difference < 0 else 'Không đổi',
        'ratio_note': ('Không tính tỷ lệ: tháng gốc bằng 0' if before == 0 else
                       'Không tính tỷ lệ: tháng gốc âm' if before < 0 else '')}


def report_data(user, selected, include_details=False, base_month=None):
    generated_at = timezone.localtime(timezone.now(), VIETNAM)
    if base_month is None and selected > date.min:
        base_month = selected.replace(month=selected.month-1) if selected.month > 1 else date(selected.year-1, 12, 1)
    series, categories = recorded_month_statistics(user, [selected] + ([base_month] if base_month else []),
                                                   today=generated_at.date())
    current = series[selected]
    previous = series[base_month] if base_month else None
    comparisons = []
    for key, label in [('income', 'Tổng thu'), ('expense', 'Tổng chi'), ('balance', 'Chênh lệch thu–chi')]:
        before = previous[key] if previous else None
        comparisons.append({'label': label, 'current': current[key], 'previous': before,
            **(change(before, current[key]) if before is not None else
               {'difference': None, 'percentage': None, 'direction': '', 'ratio_note': ''})})
    a_categories = {item['id']: item for item in categories.get(base_month, [])}
    b_categories = {item['id']: item for item in categories[selected]}
    category_comparisons = []
    choices = {'comparison_a': f'{base_month.year:04d}-{base_month.month:02d}',
               'comparison_b': f'{selected.year:04d}-{selected.month:02d}'} if base_month else {}

    def transaction_url(month, category_id):
        return reverse('finance:transaction_list') + '?' + urlencode({'period': 'month',
            'month': f'{month.year:04d}-{month.month:02d}', 'kind': 'expense', 'category': category_id, **choices})

    if previous:
        for key in a_categories.keys() | b_categories.keys():
            a = a_categories.get(key, {}).get('amount', Decimal('0'))
            b = b_categories.get(key, {}).get('amount', Decimal('0'))
            category_comparisons.append({'id': key, 'name': (b_categories.get(key) or a_categories[key])['name'],
                'a': a, 'b': b, **change(a, b),
                'a_url': transaction_url(base_month, key), 'b_url': transaction_url(selected, key)})
        category_comparisons.sort(key=lambda row: (-row['difference'], row['id']))
    maximum = max(current['income'], current['expense'], previous['income'] if previous else Decimal('0'),
                  previous['expense'] if previous else Decimal('0'))
    chart = []
    if previous:
        for code, item in [('A', previous), ('B', current)]:
            chart.append({**item, 'code': code, 'income_height': format(percent(item['income'], maximum), 'f'),
                          'expense_height': format(percent(item['expense'], maximum), 'f')})
    details = []
    if include_details:
        # No paginator, row limit, model inference, or writes in this path.
        details = list(Transaction.objects.filter(user=user, category__user=user,
            date__gte=selected,
            date__lte=selected.replace(day=monthrange(selected.year, selected.month)[1]))
            .select_related('category').order_by('-date', '-pk'))
    both_complete = bool(previous and all(item['status'] == MonthlyCoverage.Status.COMPLETE
                                         and not item['period_note'] for item in (current, previous)))
    return {'report_month': selected, 'base_month': base_month, 'generated_at': generated_at,
            'current': current, 'previous': previous, 'comparisons': comparisons,
            'categories': categories[selected], 'both_complete': both_complete,
            'category_comparisons': category_comparisons, 'comparison_chart': chart, **chart_axis(maximum),
            'include_details': include_details, 'report_transactions': details}
