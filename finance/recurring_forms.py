from django import forms

from .forms import TransactionForm
from .models import Category, RecurringRule


class RecurringRuleForm(forms.ModelForm):
    due_day = forms.IntegerField(label='Ngày đến hạn', min_value=1, max_value=31,
        help_text='Nếu tháng không có ngày này, dùng ngày cuối tháng.')
    start_month = forms.DateField(label='Tháng bắt đầu', input_formats=['%Y-%m'],
        widget=forms.DateInput(format='%Y-%m', attrs={'type': 'month'}))
    end_month = forms.DateField(label='Tháng kết thúc', required=False, input_formats=['%Y-%m'],
        widget=forms.DateInput(format='%Y-%m', attrs={'type': 'month'}))

    class Meta:
        model = RecurringRule
        fields = ['name', 'kind', 'amount', 'category', 'due_day', 'start_month', 'end_month']
        widgets = {'amount': forms.NumberInput(attrs={'min': 1, 'step': 1, 'inputmode': 'numeric'})}

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


class RecurringActionForm(forms.Form):
    confirm = forms.BooleanField(label='Tôi xác nhận thao tác này cho đúng kỳ đang hiển thị.')
