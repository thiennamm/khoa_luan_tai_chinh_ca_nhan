from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from .models import Category, Transaction, Kind
from .classification_modes import MODES
from .money_fields import amount_field


class VietnameseAuthenticationForm(AuthenticationForm):
    username = forms.CharField(label="Tên đăng nhập", widget=forms.TextInput(attrs={"autofocus": True, "autocomplete": "username"}))
    password = forms.CharField(label="Mật khẩu", strip=False, widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}))


class SignUpForm(UserCreationForm):
    class Meta:
        model = User
        fields = ["username", "password1", "password2"]
        labels = {"username": "Tên đăng nhập"}


class MonthForm(forms.Form):
    month = forms.DateField(
        label="Tháng", input_formats=["%Y-%m"],
        widget=forms.DateInput(format="%Y-%m", attrs={"type": "month", "required": True}),
        error_messages={"invalid": "Tháng không hợp lệ. Vui lòng chọn lại."},
    )


class CoverageYearForm(forms.Form):
    year = forms.IntegerField(label='Năm', min_value=1, max_value=9999,
        widget=forms.NumberInput(attrs={'min': 1, 'max': 9999}))


class CoverageConfirmationForm(forms.Form):
    review_token = forms.CharField(widget=forms.HiddenInput, max_length=1000)
    confirm_no_expense = forms.BooleanField(required=False,
        label='Tôi xác nhận tháng này không có khoản chi.')


class CoverageStatusForm(forms.Form):
    status = forms.ChoiceField(choices=[('unknown', 'Chưa xác nhận'), ('incomplete', 'Chưa đầy đủ')])


class SuggestionForm(forms.Form):
    mode = forms.ChoiceField(choices=MODES)
    description = forms.CharField(max_length=500, required=False, strip=False)
    kind = forms.ChoiceField(choices=Kind.choices)


class CsvUploadForm(forms.Form):
    file = forms.FileField(label='Tệp CSV UTF-8', allow_empty_file=False,
        error_messages={'required': 'Vui lòng chọn một tệp CSV.', 'empty': 'Tệp trống, chưa có header hoặc giao dịch.'})

    def clean_file(self):
        upload = self.cleaned_data['file']
        if upload.size > 2 * 1024 * 1024:
            raise forms.ValidationError('Tệp vượt giới hạn 2 MiB (2.097.152 byte).')
        return upload


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "kind", "canonical_label"]
        widgets = {"name": forms.TextInput(attrs={"placeholder": "Ví dụ: Ăn uống, Lương…"})}

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance._state.adding:
            self.instance.user = user


class TransactionForm(forms.ModelForm):
    amount = amount_field(Transaction)
    class Meta:
        model = Transaction
        fields = ["kind", "amount", "date", "category", "description"]
        widgets = {
            "date": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 3, "placeholder": "Ghi chú thêm về giao dịch (không bắt buộc)"}),
        }

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance._state.adding:
            self.instance.user = user
        self.fields["category"].queryset = Category.objects.filter(user=user)
        self.fields["category"].empty_label = "Chọn danh mục phù hợp"
