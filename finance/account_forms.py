"""Biểu mẫu thông tin đăng nhập của đúng tài khoản đang xác thực."""
from django import forms
from django.contrib.auth.forms import UsernameField, PasswordChangeForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import transaction


class UsernameChangeForm(forms.Form):
    new_username = User._meta.get_field('username').formfield(
        form_class=UsernameField, label='Tên đăng nhập mới',
        validators=list(User._meta.get_field('username').validators),
        error_messages={'required': 'Vui lòng nhập tên đăng nhập mới.',
                        'invalid': 'Tên đăng nhập không hợp lệ.'})
    current_password = forms.CharField(label='Mật khẩu hiện tại', strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'current-password'}))

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        self.fields['new_username'].widget.attrs['autocomplete'] = 'username'

    def clean_new_username(self):
        username = self.cleaned_data['new_username']
        if User.objects.exclude(pk=self.user.pk).filter(username=username).exists():
            raise ValidationError('Tên đăng nhập này đã được sử dụng.')
        return username

    def clean_current_password(self):
        password = self.cleaned_data['current_password']
        if not self.user.check_password(password):
            raise ValidationError('Mật khẩu hiện tại không đúng.')
        return password

    def save(self):
        username = self.cleaned_data['new_username']
        with transaction.atomic():
            # Chỉ UPDATE username của ID hiện tại; không lưu lại các trường quyền.
            # Kiểm hash còn khớp để không dùng xác nhận mật khẩu đã bị đổi đồng thời.
            changed = User.objects.filter(pk=self.user.pk, password=self.user.password).update(username=username)
            if not changed:
                raise ValidationError('Thông tin xác thực đã thay đổi. Vui lòng tải lại trang và thử lại.')
        self.user.username = username
        return self.user


class VietnamesePasswordChangeForm(PasswordChangeForm):
    def __init__(self, user, *args, **kwargs):
        super().__init__(user, *args, **kwargs)
        for name, label in [('old_password', 'Mật khẩu hiện tại'),
                            ('new_password1', 'Mật khẩu mới'),
                            ('new_password2', 'Xác nhận mật khẩu mới')]:
            self.fields[name].label = label
            self.fields[name].widget.attrs.pop('autofocus', None)
        self.error_messages = {**self.error_messages, 'password_incorrect': 'Mật khẩu hiện tại không đúng.'}
