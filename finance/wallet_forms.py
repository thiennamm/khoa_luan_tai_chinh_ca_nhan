from decimal import Decimal
from django import forms
from .models import Wallet, WalletTransfer
from .money import input_digits
from .money_fields import VNDInput, amount_field
from .wallets import today


class SignedVNDField(forms.DecimalField):
    def to_python(self, value):
        if value in self.empty_values: return None
        if isinstance(value, Decimal): return super().to_python(value)
        value = str(value).strip()
        negative = value.startswith('-')
        digits = input_digits(value[1:] if negative else value)
        return super().to_python(('-' if negative else '') + digits)


class WalletForm(forms.ModelForm):
    opening_balance = SignedVNDField(label='Số dư ban đầu (VND)', max_digits=15, decimal_places=0,
        min_value=Decimal('-999999999999999'), max_value=Decimal('999999999999999'),
        widget=VNDInput(attrs={'inputmode':'text'}),
        help_text='Cho phép 0 hoặc âm, ví dụ -50.000. Đây là mốc tài sản tự khai báo, không phải thu nhập.')
    class Meta:
        model = Wallet
        fields = ['name','kind','opening_balance','start_date']
        widgets = {'start_date':forms.DateInput(format='%Y-%m-%d',attrs={'type':'date'})}

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.user = user
        if not self.instance.pk:
            self.initial.setdefault('opening_balance', Decimal(0))
            self.initial.setdefault('start_date', today())
        elif self.instance.opening_locked or self.instance.transactions.exists() or self.instance.sent_transfers.exists() or self.instance.received_transfers.exists():
            self.fields['opening_balance'].disabled = True
            self.fields['start_date'].disabled = True


class TransferForm(forms.ModelForm):
    operation_token = forms.CharField(widget=forms.HiddenInput, max_length=2000)
    amount = amount_field(WalletTransfer)
    class Meta:
        model = WalletTransfer
        fields = ['source','destination','amount','date','note']
        widgets = {'date':forms.DateInput(format='%Y-%m-%d',attrs={'type':'date'}), 'note':forms.Textarea(attrs={'rows':2})}

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.user = user
        for field in ('source','destination'):
            self.fields[field].queryset = Wallet.objects.filter(user=user, archived=False)
        self.initial.setdefault('date', today())
        self.fields['date'].widget.attrs['max'] = today().isoformat()

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('source') and cleaned.get('source') == cleaned.get('destination'):
            self.add_error('destination','Ví đích phải khác ví nguồn.')
        return cleaned


class WalletHistoryForm(forms.Form):
    start = forms.DateField(label='Từ ngày', required=False, widget=forms.DateInput(attrs={'type':'date'}))
    end = forms.DateField(label='Đến ngày', required=False, widget=forms.DateInput(attrs={'type':'date'}))

    def clean(self):
        data = super().clean()
        if bool(data.get('start')) != bool(data.get('end')):
            raise forms.ValidationError('Chọn đủ ngày bắt đầu và kết thúc.')
        if data.get('start') and data.get('end') and data['start'] > data['end']:
            raise forms.ValidationError('Ngày bắt đầu không được sau ngày kết thúc.')
        return data
