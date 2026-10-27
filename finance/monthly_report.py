"""Read-only monthly report, using the dashboard's recorded-data aggregation."""
import re
from calendar import monthrange
from decimal import Decimal, ROUND_HALF_UP
from zoneinfo import ZoneInfo

from django import forms
from django.utils import timezone

from .forms import MonthForm
from .models import MonthlyCoverage, Transaction
from .statistics import financial_statistics

VIETNAM = ZoneInfo('Asia/Ho_Chi_Minh')


class MonthlyReportForm(MonthForm):
    include_details = forms.BooleanField(required=False, label='Bao gồm toàn bộ giao dịch trong tháng')

    def clean_month(self):
        if not re.fullmatch(r'[0-9]{4}-(0[1-9]|1[0-2])', self.data.get('month', '')):
            raise forms.ValidationError('Chọn tháng hợp lệ theo dạng YYYY-MM.')
        return self.cleaned_data['month']


def report_data(user, selected, include_details=False):
    stats = financial_statistics(user, selected, 6)
    current = stats['monthly_statistics'][-1]
    previous = stats['monthly_statistics'][-2] if len(stats['monthly_statistics']) > 1 else None
    comparisons = []
    for key, label in [('income', 'Tổng thu'), ('expense', 'Tổng chi'), ('balance', 'Chênh lệch thu–chi')]:
        before = previous[key] if previous else None
        # A signed net difference is not a meaningful percentage-growth base.
        percentage = None
        if key != 'balance' and before:
            percentage = ((current[key] - before) * Decimal('100') / before).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP)
        comparisons.append({'label': label, 'current': current[key], 'previous': before,
                            'difference': current[key] - before if before is not None else None,
                            'percentage': percentage, 'show_percentage': key != 'balance'})
    details = []
    if include_details:
        # No paginator, row limit, model inference, or writes in this path.
        details = list(Transaction.objects.filter(user=user, category__user=user,
            date__gte=selected,
            date__lte=selected.replace(day=monthrange(selected.year, selected.month)[1]))
            .select_related('category').order_by('-date', '-pk'))
    both_complete = bool(previous and all(item['status'] == MonthlyCoverage.Status.COMPLETE
                                         and not item['period_note'] for item in (current, previous)))
    return {'report_month': selected, 'generated_at': timezone.localtime(timezone.now(), VIETNAM),
            'current': current, 'previous': previous, 'comparisons': comparisons,
            'categories': stats['category_statistics'], 'both_complete': both_complete,
            'include_details': include_details, 'report_transactions': details}
