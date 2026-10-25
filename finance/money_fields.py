from decimal import Decimal
from django import forms
from django.core.exceptions import ValidationError
from .money import input_digits


class VNDInput(forms.TextInput):
    template_name = 'finance/widgets/vnd_input.html'

    def format_value(self, value):
        if value is None or value == '':
            return None
        try:
            if isinstance(value, Decimal):
                if not value.is_finite() or value != value.to_integral_value():
                    return str(value)
                return f'{value:,.0f}'.replace(',', '.')
            return f'{Decimal(input_digits(value)):,.0f}'.replace(',', '.')
        except ValidationError:
            return value  # Preserve invalid input on a bound form, never silently repair it.


class VNDAmountField(forms.DecimalField):
    widget = VNDInput

    def to_python(self, value):
        if value in self.empty_values:
            return None
        if isinstance(value, Decimal):
            return super().to_python(value)
        return super().to_python(input_digits(value, self.max_digits or 15))


def amount_field(model):
    return model._meta.get_field('amount').formfield(
        form_class=VNDAmountField, min_value=Decimal('1'),
        widget=VNDInput(attrs={'inputmode':'numeric', 'data-vnd-input':'true', 'autocomplete':'off', 'placeholder':'50.000'}),
        help_text='Nhập số nguyên VND dương, tối đa 15 chữ số. Có thể nhập 50000 hoặc 50.000; không dùng dấu phẩy.')
