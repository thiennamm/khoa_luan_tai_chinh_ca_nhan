"""Bộ lọc chỉ đọc; tổng Decimal trên toàn bộ queryset đã lọc."""
from datetime import date
from decimal import Decimal
import re
from django import forms
from django.db import connection
from django.db.models import CharField, F, Func, Value
from django.db.models.functions import Collate
from django.utils import timezone
from .models import Category, Kind


class TransactionFilterForm(forms.Form):
    q = forms.CharField(label='Tìm trong mô tả', max_length=500, required=False)
    kind = forms.ChoiceField(label='Loại', required=False, choices=[('', 'Tất cả'), *Kind.choices])
    category = forms.ModelChoiceField(label='Danh mục', queryset=Category.objects.none(),
        required=False, empty_label='Tất cả danh mục',
        error_messages={'invalid_choice': 'Danh mục không hợp lệ. Vui lòng chọn lại.'})
    period = forms.ChoiceField(label='Thời gian', choices=[('month', 'Theo tháng'), ('range', 'Khoảng ngày')])
    month = forms.CharField(label='Tháng', required=False, widget=forms.TextInput(attrs={'type': 'month'}))
    start = forms.DateField(label='Từ ngày', required=False, input_formats=['%Y-%m-%d'],
        widget=forms.DateInput(attrs={'type': 'date'}), error_messages={'invalid': 'Ngày bắt đầu không hợp lệ.'})
    end = forms.DateField(label='Đến ngày', required=False, input_formats=['%Y-%m-%d'],
        widget=forms.DateInput(attrs={'type': 'date'}), error_messages={'invalid': 'Ngày kết thúc không hợp lệ.'})

    def __init__(self, data, *, user):
        data = data.copy()
        if 'period' not in data:
            data['period'] = 'month'
        if 'month' not in data:
            data['month'] = timezone.localdate().strftime('%Y-%m')
        for name in (['start', 'end'] if data.get('period') == 'month' else ['month']):
            data[name] = ''
        super().__init__(data)
        self.fields['category'].queryset = Category.objects.filter(user=user)

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('period') == 'month':
            value = cleaned.get('month', '')
            try:
                if not re.fullmatch(r'[0-9]{4}-(0[1-9]|1[0-2])', value):
                    raise ValueError
                cleaned['month_start'] = date(int(value[:4]), int(value[5:]), 1)
            except ValueError:
                self.add_error('month', 'Chọn tháng hợp lệ theo dạng YYYY-MM.')
        elif cleaned.get('period') == 'range':
            for name in ['start', 'end']:
                if not cleaned.get(name) and name not in self.errors:
                    self.add_error(name, 'Vui lòng chọn đủ ngày bắt đầu và kết thúc.')
            if cleaned.get('start') and cleaned.get('end') and cleaned['start'] > cleaned['end']:
                self.add_error('end', 'Ngày kết thúc phải bằng hoặc sau ngày bắt đầu.')
        return cleaned


def apply_filters(rows, data):
    if data['period'] == 'month':
        month = data['month_start']
        rows = rows.filter(date__year=month.year, date__month=month.month)
    else:
        rows = rows.filter(date__gte=data['start'], date__lte=data['end'])
    if data.get('kind'):
        rows = rows.filter(kind=data['kind'])
    if data.get('category'):
        rows = rows.filter(category=data['category'])
    if data.get('q'):
        if connection.vendor == 'sqlite':
            # SQLite LIKE/LOWER mặc định không casefold chữ Việt có dấu.
            # UDF thuần trên kết nối, không sửa schema; contains escape %/_.
            connection.ensure_connection()
            connection.connection.create_function('finance_casefold', 1,
                lambda value: (value or '').casefold(), deterministic=True)
            rows = rows.alias(description_fold=Func(F('description'),
                function='finance_casefold', output_field=CharField()))
            rows = rows.filter(description_fold__contains=data['q'].casefold())
        elif connection.vendor == 'postgresql' and connection.pg_version >= 180000:
            # Render/QA PostgreSQL 18: default C collation only folds ASCII.
            # Built-in deterministic Unicode folding, on both operands; contains
            # still escapes literal SQL wildcards. No schema/extension changes.
            def fold(expression):
                return Func(Collate(expression, 'pg_unicode_fast'), function='CASEFOLD', output_field=CharField())
            rows = rows.alias(description_fold=fold(F('description')))
            rows = rows.filter(description_fold__contains=fold(Value(data['q'])))
        else:
            rows = rows.filter(description__icontains=data['q'])
    return rows.order_by('-date', '-id')


def filtered_totals(rows):
    totals = {'income': Decimal('0'), 'expense': Decimal('0')}
    for kind, amount in rows.values_list('kind', 'amount').iterator():
        totals[kind] += amount
    return {**totals, 'balance': totals['income'] - totals['expense'], 'result_count': rows.count()}
