"""VND presentation and strict form input; not used by CSV or quick parser."""
import re
from decimal import Decimal
from django.core.exceptions import ValidationError


def format_vnd(value):
    if value is None:
        return '—'  # Unknown is not a zero transaction/forecast.
    # Same whole-VND display rounding as the previous template filter.
    return f'{value:,.0f}'.replace(',', '.') + ' VND'


def input_digits(value, max_digits=15):
    text = str(value).strip()
    plain = re.fullmatch(r'[0-9]+', text)
    grouped = re.fullmatch(r'[1-9][0-9]{0,2}(?:\.[0-9]{3})+', text)
    if not plain and not grouped:
        raise ValidationError('Nhập số nguyên VND như 50000 hoặc 50.000; không dùng dấu phẩy, phần lẻ, ký hiệu tiền hoặc dấu âm/dương.')
    digits = text.replace('.', '') if grouped else text
    if len(digits) > max_digits:
        raise ValidationError(f'Số tiền tối đa {max_digits} chữ số.')
    return digits
