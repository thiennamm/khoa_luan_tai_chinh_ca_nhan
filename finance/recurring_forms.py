from django import forms

from .forms import TransactionForm
from .models import Category, RecurringRule
from . import recurring
from .money_fields import amount_field


class RecurringRuleForm(forms.ModelForm):
    amount = amount_field(RecurringRule)
    due_day = forms.IntegerField(label='Ngày đến hạn', min_value=1, max_value=31,
        help_text='Nếu tháng không có ngày này, dùng ngày cuối tháng.')
    start_month = forms.DateField(label='Tháng bắt đầu', input_formats=['%Y-%m'],
        widget=forms.DateInput(format='%Y-%m', attrs={'type': 'month'}))
    end_month = forms.DateField(label='Tháng kết thúc', required=False, input_formats=['%Y-%m'],
        widget=forms.DateInput(format='%Y-%m', attrs={'type': 'month'}))

    class Meta:
        model = RecurringRule
        fields = ['name', 'kind', 'amount', 'category', 'due_day', 'start_month', 'end_month']

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance._state.adding:
            self.instance.user = user
        self.fields['category'].queryset = Category.objects.filter(user=user)


class RecurringConfirmationForm(TransactionForm):
    def __init__(self, *args, expected_kind, user, **kwargs):
        super().__init__(*args, user=user, **kwargs)
        self.initial['kind'] = expected_kind
        self.fields['kind'].disabled = True
        self.fields['kind'].widget = forms.HiddenInput()
        self.fields['category'].queryset = Category.objects.filter(user=user, kind=expected_kind)
        self.initial['date'] = recurring.today()
        self.fields['date'].label = 'Ngày giao dịch thực tế'
        self.fields['date'].help_text = 'Chỉ ghi nhận khoản đã thực sự phát sinh; có thể chọn ngày quá khứ.'
        self.fields['date'].widget.attrs['max'] = recurring.today().isoformat()

    def clean_date(self):
        value = self.cleaned_data['date']
        if value > recurring.today():
            raise forms.ValidationError('Ngày giao dịch thực tế không được ở tương lai theo giờ Việt Nam.')
        return value


class RecurringActionForm(forms.Form):
    confirm = forms.BooleanField(label='Tôi xác nhận thao tác này cho đúng kỳ đang hiển thị.')
