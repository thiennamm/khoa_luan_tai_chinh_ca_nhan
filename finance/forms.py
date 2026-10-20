from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from .models import Category, Transaction


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


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "kind"]
        widgets = {"name": forms.TextInput(attrs={"placeholder": "Ví dụ: Ăn uống, Lương…"})}

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance._state.adding:
            self.instance.user = user


class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ["kind", "amount", "date", "category", "description"]
        widgets = {
            "amount": forms.NumberInput(attrs={"min": "1", "step": "1", "inputmode": "numeric", "placeholder": "150000"}),
            "date": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 3, "placeholder": "Ghi chú thêm về giao dịch (không bắt buộc)"}),
        }

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance._state.adding:
            self.instance.user = user
        self.fields["category"].queryset = Category.objects.filter(user=user)
        self.fields["category"].empty_label = "Chọn danh mục phù hợp"
