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
        fields = ['name', 'kind', 'amount', 'category', 'wallet', 'due_day', 'start_month', 'end_month']

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance._state.adding:
            self.instance.user = user
        self.fields['category'].queryset = Category.objects.filter(user=user)
        from .models import Wallet
        from django.db.models import Q
        self.fields['wallet'].queryset = Wallet.objects.filter(user=user).filter(
            Q(archived=False) | Q(pk=self.instance.wallet_id if self.instance.pk else None))
        self.fields['wallet'].empty_label = 'Chưa xác định ví'


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
        wallet_id = self.initial.get('wallet')
        if wallet_id and not self.fields['wallet'].queryset.filter(pk=wallet_id,archived=False).exists():
            self.initial['wallet'] = None
            self.fields['wallet_review'] = forms.BooleanField(required=False,
                label='Tôi đã xem lại ví mặc định không còn hợp lệ; nếu để trống ví, ghi nhận là Chưa xác định ví.')

    def clean(self):
        data = super().clean()
        if 'wallet_review' in self.fields and not data.get('wallet') and not data.get('wallet_review'):
            self.add_error('wallet','Chọn lại ví hoạt động hoặc xác nhận rõ Chưa xác định ví.')
        return data

    def clean_date(self):
        value = self.cleaned_data['date']
        if value > recurring.today():
            raise forms.ValidationError('Ngày giao dịch thực tế không được ở tương lai theo giờ Việt Nam.')
        return value


class RecurringActionForm(forms.Form):
    confirm = forms.BooleanField(label='Tôi xác nhận thao tác này cho đúng kỳ đang hiển thị.')
